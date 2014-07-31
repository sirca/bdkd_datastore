#!//usr/bin/env python
import sys
import os
import argparse
import re
import ckanapi
import tempfile
import yaml
import logging
from argparse import RawTextHelpFormatter
from bdkd import datastore as ds

MANIFEST_FILENAME = "manifest.txt"
S3_PREFIX = 's3://'

# Constants
__version__ = '0.1'


def build_ckan_data(bucket_name, api_key, org_name, ds_host, ckan_host):
    """ Builds a CKAN portal data using data taken from a datastore repository.
    :param bucket_name: the name of the bucket where the datastore repository can be found.
    :param api_key: the CKAN API key for the CKAN user login
    :param org_name: the organization name (can be ID too) for the organization that the data will be stored under.
    :param host: the object storage host.
    """
    logging.info('Priming portal data from bucket: %s' % (bucket_name))
    repo = ds.Repository(ds.Host(host=ds_host), bucket_name)
    r_names = repo.list() # get a list of resource names

    workdir = tempfile.mkdtemp()
    try:
        # Prepare a CKAN connection for use.
        site = ckanapi.RemoteCKAN(ckan_host, apikey=api_key)

        # For each resource found, build a manifest list from the raw data files under that resource.
        manifest_filename = workdir + MANIFEST_FILENAME

        # Get a list of existing CKAN groups so it doesn't get recreated.
        ckan_groups = site.action.group_list()

        for r_name in r_names:
            logging.debug("Priming repository " + r_name)
            # First Bulid the manifest file.
            manifest_file = open(manifest_filename, 'w')
            resource = repo.get(r_name)
            for f in resource.files:
                # If the file is in the bucket, give it a "s3://<bucket_name>/" style URL prefix.
                # Otherwise assume it is a remote file and just push that directly into the manifest.
                if f.location():
                    manifest_file.write('%s%s/%s\n' % (S3_PREFIX, bucket_name, f.location()))
                elif f.remote():
                    manifest_file.write(f.remote())
                else:
                    # Unknown resource error.
                    raise Exception('Unable to determine file location in resource %s.' % (r_name))
            manifest_file.close()

            # Turn pseudo path into a unique string that CKAN can use.
            # Note that it is possible that collusion can happen if the pseudo path contains
            # too many non alphanumeric characters.
            dataset_name = re.sub(r'[^0-9a-zA-Z_-]', '-', r_name).lower()
            pseudo_path = r_name.split('/')
            dataset_title = pseudo_path[-1]    # the last field of the pseudo path is the title
            dataset_groups = pseudo_path[0:-1] # the in middle fields will be the 'groups'
            author = resource.metadata.get('author', '')
            author_email = resource.metadata.get('author_email', '')
            maintainer = resource.metadata.get('maintainer', '')
            maintainer_email = resource.metadata.get('maintainer_email', '')
            version = resource.metadata.get("version", "")
            notes = resource.metadata.get("description", "")
            extras = []
            for k,v in resource.metadata.get("custom_fields", {}).items():
                extras.append({ 'key':k, 'value':v })
            """
            [
                {'key':'key1','value':'value1'},
                {'key':'key2','value':'value2'},
            ]
            """

            # Create the groups if there are not there yet.
            logging.debug("Existing groups:" + str(dataset_groups))
            dataset_group_names = []
            for group_name in dataset_groups:
                group_ckan_name = re.sub(r'[^0-9a-zA-Z_-]', '-', group_name).lower()
                if group_ckan_name not in ckan_groups:
                    logging.info("Group %s not found, creating group..." % (group_ckan_name))
                    site.action.group_create(name=group_ckan_name, title=group_name)
                    ckan_groups.append(group_ckan_name)
                dataset_group_names.append({'name':group_ckan_name})

            # Prepare a CKAN data set by creating a 'package'.
            logging.debug("Creating dataset " + dataset_name)
            logging.debug("name =" + dataset_name)
            logging.debug("owner_org =" + org_name)
            logging.debug("title =" + dataset_title)
            logging.debug("version =" + '1.0')
            logging.debug("author =" + author)
            logging.debug("notes =" + notes)
            logging.debug("extras =" + str(extras))
            logging.debug("groups =" + str(dataset_group_names))
            dataset = site.action.package_create(
                name = dataset_name,
                owner_org = org_name,
                title = dataset_title,
                version = '1.0',
                author = author,
                notes = notes,
                extras = extras,
                groups = dataset_group_names,
                # groups = [{'name':g} for g in dataset_groups],
            )


            # Now upload the manifest file into this dataset.
            site.action.resource_create(
                package_id = dataset_name,
                # revision_id = created_at,
                description = 'Manifest for resource ' + r_name,
                name = 'manifest',
                upload=open(manifest_filename)
            )

    finally:
        os.removedirs(workdir)


"""
Primer is a class that encapsulates operations required to prime a data portal with
information about research data and resources store in an object storage (such as S3).
"""
class Primer:
    def __init__(self):
        self._cfg = {}
        pass


    def load_config(self, cfg_filename):
        """ Loads the primer configuration file.
        :raises: IOError if the config can't be loaded.
        """
        # Put some default values
        if not os.path.exists(cfg_filename):
            raise Exception("Error: primer config file %s not found." % (cfg_filename))

        logging.info("Using config from " + cfg_filename)
        self._cfg = yaml.load(open(cfg_filename))


    def _check_cfg(self, cfg_dict, req_keys, name=None):
        """ Checks if the mandatory keys are present in the config dictionary object.
        :param cfg_dict:  the config data dictionary to check.
        :param req_keys: the list of keys to check for.
        :param name: the name of the token that should have those keys.
        """
        for item in req_keys:
            if item not in cfg_dict:
                sect = ""
                if name is not None:
                    sect = " from '%s'" % (name)
                raise Exception("Error: missing mandatory configuration token '%s'%s" % (item, sect))
            else:
               logging.info("config:%s = %s" % (item, cfg_dict[item]))


    def prime_portal(self, repo_name=None):
        """ Executes the priming process for the portal for all repos configured.
        :param repo_name: if specified, then only the repo with the matching bucket name will be primed.
        :raises: Exception if there is any failure.
        """
        # Validate primer config
        self._check_cfg(self._cfg, ['repos', "api_key"],)

        if repo_name is not None:
            logging.debug("Priming only repository %s" % (repo_name))
        for repo in self._cfg['repos']:
            self._check_cfg(repo, ['bucket','ckan_url',"ds_host",'org_name',], name='the repo config')
            if repo_name is not None and repo['bucket'] != repo_name:
                continue
            try:
                build_ckan_data(bucket_name=repo['bucket'],
                                api_key=self._cfg['api_key'],
                                org_name=repo['org_name'],
                                ckan_host=repo['ckan_url'],
                                ds_host=repo['ds_host'])
            except Exception as e:
                logging.error(e.message)


    def setup_organizations(self, repo_name=None):
        """ Check that the organizations in the configuration file exist
        and if not create them.
        :param repo_name: Only setup the organization for that repo config.
        """
        # Validate primer config
        self._check_cfg(self._cfg, ['repos', "api_key"],)
        api_key = self._cfg['api_key']

        action = False
        for repo in self._cfg['repos']:
            self._check_cfg(repo, ['bucket','ckan_url','org_name','org_title'], name='the repo config')
            if repo_name is not None and repo['bucket'] != repo_name:
                continue
            action = True
            # Prepare a CKAN connection for use.
            ckan_host = repo['ckan_url']
            org_name = repo['org_name']
            site = ckanapi.RemoteCKAN(ckan_host, apikey=api_key)
            orgs = site.action.organization_list()
            if org_name not in orgs:
                logging.debug("Organization %s does not exist yet, creating one..." % (org_name))
                site.action.organization_create(name=org_name,
                                                title=repo['org_title'],
                                                description=repo['org_title'])
            else:
                logging.debug("Organization %s already exists, skipping setup" % (org_name))
        if not action:
            logging.warn("No organization was setup")


def main():
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
        description='BDKD Portal Primer V%s\nTo prime a BDKD data portal so that it is synchronized '
                    'with the BDKD Data Repository in an object store.' % (__version__))

    parser.add_argument('command',
                        help='The command to execute, which can be:\n'
                             ' prime - prime the portal data from the data storage\n'
                             ' setup - setup the organizations in the config file\n'
    )
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('-b', '--bucket-name', help='Select the bucket to prime (must be in the config)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run in verbose mode')
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    cfg_filename = '/etc/bdkd/primer.conf'
    if args.config:
        cfg_filename = args.config

    primer = Primer()

    if args.command == 'prime':
        primer.load_config(cfg_filename)
        primer.prime_portal(repo_name=args.bucket_name)
        sys.exit(0)

    elif args.command == 'setup':
        primer.load_config(cfg_filename)
        primer.setup_organizations(repo_name=args.bucket_name)
        sys.exit(0)

    else:
        sys.exit('Unknown command %s' % (args.command))


if __name__=='__main__':
    logging.basicConfig(level=logging.WARN)
    main()
