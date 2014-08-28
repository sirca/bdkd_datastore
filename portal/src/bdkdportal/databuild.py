#!//usr/bin/env python
import sys
import os
import argparse
import re
import ckanapi
import tempfile
import yaml
import logging
import urllib
import dateutil.parser
import pytz
from lockfile import FileLock
from lockfile import LockTimeout
from argparse import RawTextHelpFormatter
from bdkd import datastore
import paste.script.command
import ckan.lib.cli


MANIFEST_FILENAME = "manifest.txt"
S3_PREFIX = 's3://'

# Constants
__version__ = '0.1'


class Dataset:
    """
    Dataset class holds information that can be used to build a CKAN dataset (or CKAN package)
    for a BDKD-datastore dataset.
    """

    def __init__(self, name, title, owner_org, description):
        self.name = name
        self.title = title
        self.owner_org = owner_org
        self.description = description


def purge_ckan_dataset(ds_to_purge, ckan_ini):
    """ Delete a dataset from the portal.
    Note: this method was created as CKAN 2.2 does not support purging of dataset from its API.
    Purging is done through the UI or through a paster command. So this function is created to
    wraps the nastiness up so that it can be replaced easily when CKAN implements purging through API.
    :param ds_to_purge: the unique name of the dataset to purge.
    :param ckan_ini: the CKAN ini file to use when purgin via python paste
    """
    logging.info("Purging dataset '%s' from portal" % (ds_to_purge))
    dataset_cmd = ckan.lib.cli.DatasetCmd("purger")
    dataset_cmd.run(["purge", ds_to_purge, "-c", ckan_ini])


class RepositoryBuilder:
    """
    The RepositoryBuilder class is used to build/update all the portal information for a single
    datastore repository.
    """

    def _reset(self):
        self._repo_name = None
        self._ckan_site = None
        self._tmp_dir = None


    def __init__(self, data_builder):
        """
        :param data_builder: The portal builder object that created this builder object.
        :type  data_builder: PortalBuilder
        """
        self._reset()
        self._data_builder = data_builder
        self._dataset_audit = None


    @staticmethod
    def to_ckan_usable_name(dataset_name):
        """ Takes a BDKD datastore dataset name and turn it into a dataset that
        is usable as a dataset name in CKAN. This basically involves turning anything
        that is not an alphanumeric, underscores, or dashes, into dashes.
        If the dataset name came from datastore, it is likely to be a pseudo path of the
        resource name. In the case, it is possible that collusion can happen if the pseudo path
        contains too many non alphanumeric characters.
        """
        return re.sub(r'[^0-9a-zA-Z_-]', '-', dataset_name).lower()


    def release(self):
        """ End the building process, cleaning up any temporary resources used.
        """
        if self._tmp_dir:
            os.removedirs(self._tmp_dir)
        self._reset()


    def _create_ckan_dataset(self, dataset):
        """ Create a CKAN dataset using this dataset object.
        :param dataset: the dataset object to create in CKAN
        :type  dataset: Dataset
        :return: the CKAN dataset object created.
        """
        logging.info("Creating CKAN dataset '%s'" % (dataset.name))
        ckan_ds = self._ckan_site.action.package_create(
            name = dataset.name,
            owner_org = dataset.owner_org,
            title = dataset.title,
            version = dataset.version,
            author = dataset.author,
            notes = dataset.description,
            groups = dataset.groups)
        return ckan_ds


    def _create_manifest_file(self, dataset_name, ds_resource):
        """ Creates a manifest file for all the files in a datastore resource.
        :param dataset_name: the name of the dataset
        :param ds_resource: the datastore resource to build the manifest file from
        :type  ds_resource: datastore.Resource
        """
        manifest_filename = self._tmp_dir + MANIFEST_FILENAME
        manifest_file = open(manifest_filename, 'w')
        for f in ds_resource.files:
            # If the file is in the bucket, give it a "s3://<bucket_name>/" style URL prefix.
            # Otherwise assume it is a remote file and just push that directly into the manifest.
            if f.location():
                manifest_file.write('%s%s/%s\n' % (S3_PREFIX, self._repo_name, f.location()))
            elif f.remote():
                manifest_file.write(f.remote() + '\n')
            else:
                # Unknown resource error.
                raise Exception('Unable to determine file location in resource %s.' % (ds_resource.name))
        manifest_file.close()
        logging.info("Creating manifest file for %s" % (ds_resource.name))
        self._ckan_site.action.resource_create(
            package_id = dataset_name,
            description = 'Manifest for resource ' + ds_resource.name,
            name = 'manifest',
            upload=open(manifest_filename))


    def _create_visualization_resource(self, dataset_name, ds_resource):
        """ To create a visualization ckan resource for the datastore resource.
        :param dataset_name: the name of the CKAN dataset to put the visual link under
        :param ds_resource: the resource in datastore to create visualization for
        :type  ds_resource: datastore.Resource
        """
        datatype = ds_resource.metadata.get('data_type', None)
        if datatype:
            visual_site = self._data_builder.find_visual_site_for_datatype(datatype)
            if visual_site:
                url = visual_site.format(urllib.quote_plus(self._repo_name), urllib.quote_plus(ds_resource.name))
                logging.debug("Explore link for '%s' is '%s'" % (ds_resource.name, url))
                self._ckan_site.action.resource_create(
                    package_id = dataset_name,
                    description = 'Explore the dataset',
                    url = url, format = 'html', name = 'explore')


    def _purge_dataset_from_portal(self, ds_to_purge):
        """ Delete a dataset from the portal.
        :param ds_to_purge: the unique name of the dataset to purge.
        """
        purge_ckan_dataset(ds_to_purge, self._ckan_cfg)


    def set_dataset_audit(self, dataset_audit):
        """ Indicate that dataset is to be tracked when building.
        """
        self._dataset_audit = dataset_audit


    def build_portal_from_repo(self, **kwargs):
        """ Prepare to build a single datastore repository into a CKAN portal.
        :param ds_host: the name of the datastore host
        :param repo_name: the name of the repository to build from the datastore host.
        :param ckan_host: the CKAN host to build the repository to.
        :param org_name: the CKAN organization name (can be ID too) where the datasets will be stored under.
        :param api_key: the CKAN API key to use when priming (i.e. login account)
        :param ckan_cfg: the CKAN configuration file (for purging only)
        """
        self.release() # in case someone forgot to cleanup
        for key in ['ds_host','repo_name','ckan_host','org_name', 'api_key', 'ckan_cfg']:
            if kwargs.get(key) is None:
                raise Exception("Cannot build a repository without param %s" % (key))
        self._repo_name = kwargs.get('repo_name')
        self._ckan_site = ckanapi.RemoteCKAN(kwargs.get('ckan_host'), apikey=kwargs.get('api_key'))
        self._ckan_cfg = kwargs.get('ckan_cfg')
        self._tmp_dir = tempfile.mkdtemp()

        org_name = kwargs.get('org_name')
        ds_host = kwargs.get('ds_host')

        logging.info('Priming portal data from bucket: %s' % (self._repo_name))
        repo = datastore.Repository(datastore.Host(host=ds_host), self._repo_name)
        repo_dataset_names = repo.list()

        # Get a list of existing CKAN groups so repeated groups don't get recreated.
        existing_groups = self._ckan_site.action.group_list()
        groups_to_cleanup = {}
        logging.debug("Existing groups:" + str(existing_groups))

        # Get a full list of all existing dataset in CKAN along side their meta data so that
        # 1. deleted dataset can be tracked and removed
        # 2. last mod time of the dataset can be compare to decide if that dataset needs to be rebuild.
        datasets_in_portal = self._ckan_site.action.current_package_list_with_resources()
    
        for ds_dataset_name in repo_dataset_names:
            logging.debug("Priming repository:%s dataset:%s" % (self._repo_name, ds_dataset_name))
            dataset_name = RepositoryBuilder.to_ckan_usable_name(self._repo_name + "-" + ds_dataset_name)
            build_dataset_portal_data = True
            # Look for the dataset in the portal.
            for dataset in datasets_in_portal:
                if dataset['name'] == dataset_name:
                    self._dataset_audit[dataset_name] = True # Mark dataset is touched and audited

                    # Dataset already exists in the portal, check if it was modified in datastore since
                    # last built.
                    last_built_in_portal = dateutil.parser.parse(dataset['revision_timestamp'])
                    last_mod_in_datastore = repo.get_resource_last_modified(ds_dataset_name)
                    if last_mod_in_datastore <= last_built_in_portal:
                        # Dataset has not changed, so mark to skip the update.
                        build_dataset_portal_data = False
                    else:
                        # Dataset has changed, need to remove the existing dataset from the portal,
                        # and build up a list of 'groups' to possibly remove at the end of all these.
                        self._purge_dataset_from_portal(dataset_name)
                    break
                # else continue to search for a matching dataset.
                # If not found in existing dataset, then it will be added in as a new dataset.

            if build_dataset_portal_data:
                resource = repo.get(ds_dataset_name)
                pseudo_path = ds_dataset_name.split('/')
                dataset = Dataset(
                    name = dataset_name,
                    title = pseudo_path[-1], # the last directory of the pseudo path is the title of the dataset
                    owner_org = org_name,
                    description = resource.metadata.get('description',''))
                # Bring over other optional fields from the metadata.
                for field in ['author','author_email','maintainer','maintainer_email','version']:
                    setattr(dataset, field, resource.metadata.get(field, ""))

                # Create the groups if there are not there yet. Needs to happen before the dataset is created in CKAN.
                group_names = pseudo_path[0:-1]
                dataset.groups = []
                for group_name in group_names:
                    group_ckan_name = RepositoryBuilder.to_ckan_usable_name(group_name)
                    if group_ckan_name not in existing_groups:
                        logging.info("Group %s not found, creating group..." % (group_ckan_name))
                        self._ckan_site.action.group_create(name=group_ckan_name, title=group_name)
                        existing_groups.append(group_ckan_name)
                    dataset.groups.append({'name':group_ckan_name})

                # Build and upload the manifest file into this dataset.
                self._create_ckan_dataset(dataset)
                self._create_manifest_file(dataset_name=dataset.name, ds_resource=resource)
                self._create_visualization_resource(dataset_name=dataset.name, ds_resource=resource)
            # else don't need to update the dataset as it hasn't changed.
        # end-for ds_dataset_name in repo_dataset_names

        # For datasets that were in the portal before the 


"""
PortalBuilder is a class that encapsulates operations required to build a data portal with
information about research data and resources store in an object storage (such as S3).
"""
class PortalBuilder:
    def __init__(self):
        self._cfg = {}
        self._ckan_site = None
        pass


    def load_config(self, from_file=None, from_string=None):
        """ Loads the data_builder configuration file either from a file or from a YAML string.
        :raises: IOError if the config can't be loaded.
        """
        if from_file:
            logging.info("Using config from " + from_file)
            if not os.path.exists(from_file):
                raise Exception("Error: portal data builder config file %s not found." % (from_file))
            self._cfg = yaml.load(open(from_file))
        elif from_string:
            self._cfg = yaml.load(from_string)
        else:
            raise Exception("Error: Unable to load portal data builder config without any configuration")


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


    def find_visual_site_for_datatype(self, datatype):
        """ To find the visualization site for a particular datatype from the configuration.
        :return: the site, or None if not found or not configured.
        """
        visual_site = None
        cfg_sites = self._cfg.get('visual-sites')
        if cfg_sites:
            matched_sites = filter(lambda x: x['data_type']==datatype, cfg_sites)
            # If multiple sites are found for that data_type, only use the first one.
            if matched_sites:
                visual_site = matched_sites[0].get('url')
        return visual_site


    def _build_portal(self, repo_name=None):
        """ Executes the priming process for the portal for all repos configured.
        :param repo_name: if specified, then only the repo with the matching bucket name will be built.
        :raises: Exception if there is any failure.
        """

        # Validate config
        self._check_cfg(self._cfg, ['repos', 'api_key', 'ckan_cfg', 'ckan_url'],)
        logging.debug("Building repository: %s" % (repo_name if repo_name else "ALL"))

        ckan_site = ckanapi.RemoteCKAN(self._cfg['ckan_url'], apikey=self._cfg['api_key'])
        datasets_before_build = ckan_site.action.current_package_list_with_resources()
        datasets_touched = {}
        for repo in self._cfg['repos']:
            self._check_cfg(repo, ['bucket','ds_host','org_name',], name='the repo config')

            if repo_name is not None and repo['bucket'] != repo_name:
                continue

            repo_builder = RepositoryBuilder(self)
            repo_builder.set_dataset_audit(datasets_touched)
            try:
                repo_builder.build_portal_from_repo(
                    ds_host = repo['ds_host'],
                    repo_name = repo['bucket'],
                    org_name = repo['org_name'],
                    api_key = self._cfg['api_key'],
                    ckan_host = self._cfg['ckan_url'],
                    ckan_cfg = self._cfg['ckan_cfg'])


            except Exception as e:
                logging.error("Priming failed " + str(e))
                repo_builder.release()
                raise

        # Clean up leftover (i.e. datasets that were not touched are assume to be deleted from datastore)
        # This will only take place if the priming is for all repo, otherwise some dataset might not be 'touched'.
        if repo_name is None:
            try:
                groups_to_cleanup = {}
                for dataset in datasets_before_build:
                    if not datasets_touched.get(dataset['name'], False):
                        # Found a dataset that was not touched, so remove it from the portal.
                        ckan_site.action.package_delete(id=dataset['name'])
                        purge_ckan_dataset(dataset['name'], self._cfg['ckan_cfg'])
                        
                        # Track the groups that the purged dataset belongs to.
                        for group in dataset['groups']:
                            logging.debug("Marking group %s for audit" % (group['name']))
                            groups_to_cleanup[group['name']] = True
                # end-for dataset

                """
                # DISABLED GROUP DELETION as CKAN's group purging has an issue when there are revisions
                # tied to the groups. Need to either fix CKAN or find another way.
                # Go through all groups whose dataset were touched and see if they are still needed.
                if len(groups_to_cleanup) > 0:
                    # New session
                    for group in groups_to_cleanup.keys():
                        group_info = ckan_site.action.group_show(id=group)
                        if group_info and group_info['package_count'] == 0:
                            # no dataset in that group anymore, delete and purge!
                            ckan_site.action.group_delete(id=group) 
                            logging.info("Purging group '%s' from portal" % (group))
                            ckan_site.action.group_purge(id=group)
                """


            except Exception as e:
                logging.error("Priming failed " + str(e))
                repo_builder.release()
                success = False
            

    def build_portal(self, repo_name=None):
        """ Same as _build_portal() but wraps around a lock so that only one
        portal building can be done at a time.
        """
        # Prevent more than one portal building from taking place.
        build_lock = FileLock("/tmp/portal_build.lock")
        try:
            build_lock.acquire(1)
            self._build_portal(repo_name=repo_name)
            build_lock.release()
        except LockTimeout:
            raise Exception("Unable to obtain build lock, probably another process is building the portal data.")


    def setup_organizations(self, repo_name=None):
        """ Check that the organizations in the configuration file exist
        and if not create them.
        :param repo_name: Only setup the organization for that repo config.
        """
        # Validate config
        self._check_cfg(self._cfg, ['repos', 'api_key', 'ckan_url'],)
        api_key = self._cfg['api_key']

        action = False
        for repo in self._cfg['repos']:
            self._check_cfg(repo, ['bucket','org_name','org_title'], name='the repo config')
            if repo_name is not None and repo['bucket'] != repo_name:
                continue
            action = True
            # Prepare a CKAN connection for use.
            ckan_host = self._cfg['ckan_url']
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
        description='BDKD Portal Data Builder V%s\nTo build the data of a BDKD Portal so that it is synchronized '
                    'with the BDKD Data Repository in an object store.' % (__version__))

    parser.add_argument('command',
                        help='The command to execute, which can be:\n'
                             ' update - to update the portal using metadata from the datastore \n'
                             ' setup - setup the organizations in the config file\n'
    )
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('-b', '--bucket-name', help='Select the bucket to build from (must be in the config)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run in verbose mode')
    parser.add_argument('--debug', action='store_true', help='Run in very verbose mode')
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    cfg_filename = '/etc/bdkd/portal.cfg'
    if args.config:
        cfg_filename = args.config

    portal_builder = PortalBuilder()

    if args.command == 'update':
        portal_builder.load_config(from_file=cfg_filename)
        portal_builder.build_portal(repo_name=args.bucket_name)
        sys.exit(0)

    elif args.command == 'setup':
        portal_builder.load_config(from_file=cfg_filename)
        portal_builder.setup_organizations(repo_name=args.bucket_name)
        sys.exit(0)

    else:
        sys.exit('Unknown command %s' % (args.command))


if __name__=='__main__':
    logging.basicConfig(level=logging.WARN)
    main()
