#!/usr/bin/env python
import sys
import os
import argparse
import re
import ckanapi
import tempfile
import yaml
from yaml import YAMLError
import logging
import urllib
import dateutil.parser
from lockfile import FileLock
from lockfile import LockTimeout
from argparse import RawTextHelpFormatter
from bdkd import datastore
import paste.script.command
import ckan.lib.cli
import daemon
import time
import shutil
import signal
import json
import hashlib


MANIFEST_FILENAME = "manifest.txt"
METADATA_FILENAME = "metadata.json"
S3_PREFIX = 's3://'

# Constants
__version__ = '0.0.7'


class FatalError(Exception):
    """ For capture fatal exception that cannot be recovered """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def check_cfg(cfg_dict, req_keys, name=None):
    """ Checks if the mandatory keys are present in the config dictionary object.
    :param cfg_dict:  the config data dictionary to check.
    :param req_keys: the list of keys to check for.
    :param name: the name of the token that should have those keys.
    :throws FatalError if it is an unrecoverable error
    """
    for item in req_keys:
        if item not in cfg_dict:
            sect = ""
            if name is not None:
                sect = " from '%s'" % (name)
            raise FatalError("Error: missing mandatory configuration token '%s'%s" % (item, sect))
        else:
           logging.getLogger(__name__).debug("config:%s = %s" % (item, cfg_dict[item]))


def ckan_dataset_name(dataset_name, repo_name=None):
    """ Takes a BDKD datastore dataset name and turn it into a dataset that
    is usable as a dataset name in CKAN. This basically involves turning anything
    that is not an alphanumeric, underscores, or dashes, into dashes.
    If the dataset name came from datastore, it is likely to be a pseudo path of the
    resource name. In the case, it is possible that collusion can happen if the pseudo path
    contains too many non alphanumeric characters.
    """
    if repo_name:
        full_name = "{0}:{1}".format(repo_name, dataset_name) 
    else:
        full_name = dataset_name
    return hashlib.sha384(full_name).hexdigest()


def ckan_usable_string(s):
    """ Takes a string and replace characters that are not usable by CKAN
    with those that are. Note that during the replacement, it is possible that
    collusion can happen if the string contains too many non alphanumeric characters.
    """
    return re.sub(r'[^0-9a-zA-Z_-]', '-', s).lower()


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
    logging.getLogger(__name__).info("Purging dataset '%s' from portal" % (ds_to_purge))
    dataset_cmd = ckan.lib.cli.DatasetCmd("purger")
    dataset_cmd.run(["purge", ds_to_purge, "-c", ckan_ini])


def prepare_lock_file(filename):
    """ Entry function to request a lock object. This function makes mocking easier
    when testing.
    """
    return FileLock(filename)


class RepositoryBuilder:
    """
    The RepositoryBuilder class is used to build/update all the portal information for a single
    datastore repository.
    """

    def _reset(self):
        self._repo_name = None
        self._ckan_site = None
        self._tmp_dir = None


    def __init__(self, portal_builder, portal_cfg, logger=None):
        """
        :param portal_builder: The portal builder object that created this builder object.
        :type  portal_builder: PortalBuilder
        :param portal_cfg:   The portal configuration
        """
        self._reset()
        self._dataset_audit = None
        self._portal_builder = portal_builder
        self._portal_cfg = portal_cfg
        self.logger = logger or logging.getLogger(__name__)


    def release(self):
        """ End the building process, cleaning up any temporary resources used.
        """
        if self._tmp_dir:
            shutil.rmtree(self._tmp_dir)
        self._reset()


    def _create_ckan_dataset(self, dataset):
        """ Create a CKAN dataset using this dataset object.
        :param dataset: the dataset object to create in CKAN
        :type  dataset: Dataset
        :return: the CKAN dataset object created.
        """
        self.logger.info("Creating CKAN dataset '%s'" % (dataset.name))
        ckan_ds = self._ckan_site.action.package_create(
            name = dataset.name,
            owner_org = dataset.owner_org,
            title = dataset.title,
            version = dataset.version,
            author = dataset.author,
            author_email = dataset.author_email,
            maintainer = dataset.maintainer,
            maintainer_email = dataset.maintainer_email,
            notes = dataset.description,
            groups = dataset.groups,
            extras = dataset.extras)
        return ckan_ds


    def _create_manifest_file(self, dataset_name, ds_resource):
        """ Creates a manifest file for all the files in a datastore resource.
        :param dataset_name: the name of the dataset
        :param ds_resource: the datastore resource to build the manifest file from
        :type  ds_resource: datastore.Resource
        """
        manifest_filename = self._tmp_dir + "/" + MANIFEST_FILENAME
        manifest_file = open(manifest_filename, 'w')
        if ds_resource.is_bundled():
            manifest_file.write('#Bundled dataset\n')
        for f in ds_resource.files:
            # If the file is in the bucket, give it a "s3://<bucket_name>/" style URL prefix.
            # Otherwise assume it is a remote file and just push that directly into the manifest.
            if f.location():
                manifest_file.write('%s%s/%s\n' % (S3_PREFIX, self._repo_name, f.location()))
            elif f.remote():
                manifest_file.write(f.remote() + '\n')
            else:
                # Unknown resource error.
                self.logger.error('Unable to determine file location in resource %s.' % (ds_resource.name))

        manifest_file.close()
        self.logger.info("Creating manifest file for %s" % (ds_resource.name))
        self._ckan_site.action.resource_create(
            package_id = dataset_name,
            description = 'Manifest for resource ' + ds_resource.name,
            name = 'manifest',
            upload=open(manifest_filename))


    def _create_metadata_file(self, dataset_name, ds_resource):
        """ Creates a metadata json file to be uploaded as the resource 'metadata'
        :param dataset_name: the name of the dataset
        :param ds_resource: the datastore resource (dataset) to build the meta data for
        :type  ds_resource: datastore.Resource
        """
        if ds_resource.metadata:
            self.logger.info("Creating metadata file for %s" % (ds_resource.name))
            metadata_filename = self._tmp_dir + "/" + METADATA_FILENAME
            metadata_file = open(metadata_filename, 'w')
            metadata_file.write(json.dumps(ds_resource.metadata,
                                           sort_keys=True,
                                           indent=4,
                                           separators=(',', ': ')))
            metadata_file.close()
            self.logger.info("Uploading metadata file for %s" % (ds_resource.name))
            self._ckan_site.action.resource_create(
                package_id = dataset_name,
                description = 'Metadata for ' + ds_resource.name,
                name = 'metadata',
                format = 'JSON',
                upload=open(metadata_filename))
        else:
            self.logger.info("No metadata found for %s, no metadata resource created" % (ds_resource.name))


    def _create_download_file(self, dataset, ds_resource, repo_cfg):
        """ Creates a "download page" CKAN resource that can be used to selectively
        download a file from the datastore.
        :param dataset: the name of the CKAN dataset to create the download resource under.
        :type  dataset: CKAN dataset dictionary
        :param ds_resource: the datastore resource to build the download file for
        :type  ds_resource: datastore.Resource
        """
        url_format = repo_cfg.get('download_url_format', None)
        if url_format is None:
            self.logger.debug('No download_url_format configured so no download page generated')
            return 
        download_template = self._portal_cfg.get('download_template', None)
        bundled_download_template = self._portal_cfg.get('bundled_download_template', None)
        for temp in download_template, bundled_download_template:
            if temp is None:
                self.logger.debug("No download template '%s' configured so no download page generated" % temp)
                return
            if not os.path.exists(temp):
                self.logger.warn("Download template '%s' is not readable or does not exist." % temp)
                return

        self.logger.info("Creating download file for dataset %s" % (ds_resource.name))
        from jinja2 import FileSystemLoader, Environment, PackageLoader
        template_loader = FileSystemLoader(searchpath='/')
        template_env = Environment(loader=template_loader)
        template = template_env.get_template(download_template)
        bundled_template = template_env.get_template(bundled_download_template)
        items = []
        resource_name_len = len(ds_resource.name)
        for f in ds_resource.files:
            name = None
            if f.location():
                # If file_key is "files/resource_name/resource_file_name"
                # resource_file_name's position starts after the '/' character that follows the
                # resource_name substring.
                file_key = f.location()
                resource_name_idx = file_key.find(ds_resource.name)
                if resource_name_idx >= 0:
                    name = file_key[resource_name_idx + resource_name_len + 1:]
                    file_url = url_format.format(datastore_host=repo_cfg['ds_host'],
                                                 repository_name=repo_cfg['bucket'],
                                                 resource_id=urllib.quote_plus(f.location()))
            elif f.remote():
                name = f.remote()
                file_url = f.remote()
            if name:
                items.append({'name':name, 'url':file_url})
            else:
                # Unknown resource error.
                self.logger.error("Error determining file location while generating download links for resource '%s'."
                                  % (ds_resource.name))

        generated_page = ''
        if ds_resource.is_bundled():
            bundled_file_url = url_format.format(datastore_host=repo_cfg['ds_host'],
                                                 repository_name=repo_cfg['bucket'],
                                                 resource_id=urllib.quote_plus(ds_resource.bundle.location()))
            bundled_item = { 'url': bundled_file_url}
            generated_page = bundled_template.render(
                    repository_name=ds_resource.repository.name,
                    dataset_name=ds_resource.name,
                    items=items,
                    bundled_item=bundled_item)
        else:
            generated_page = template.render(
                    repository_name=ds_resource.repository.name,
                    dataset_name=ds_resource.name,
                    items=items)

        download_filename = self._tmp_dir + "/download.html"
        download_file = open(download_filename, "w")
        download_file.write(generated_page)
        download_file.close()
        self._ckan_site.action.resource_create(
                package_id = dataset.name,
                description = 'Provides individual links to download files',
                name = 'download',
                format = 'html',
                upload = open(download_filename))


    def _create_visualization_resource(self, dataset_name, ds_resource):
        """ To create a visualization ckan resource for the datastore resource.
        :param dataset_name: the name of the CKAN dataset to put the visual link under
        :param ds_resource: the resource in datastore to create visualization for
        :type  ds_resource: datastore.Resource
        """
        datatype = ds_resource.metadata.get('data_type', None)
        if datatype:
            visual_site = self._portal_builder.find_visual_site_for_datatype(datatype)
            if visual_site:
                url = visual_site.format(repository_name=urllib.quote_plus(self._repo_name),
                                         resource_name=urllib.quote_plus(ds_resource.name))
                self.logger.info("Created explore link for '%s' is '%s'" % (ds_resource.name, url))
                self._ckan_site.action.resource_create(
                    package_id = dataset_name,
                    description = 'Explore/visualise the dataset',
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


    def build_portal_from_repo(self, repo_cfg):
        """ Prepare to build a single datastore repository into a CKAN portal.
        :param repo_cfg: the repository configuration dict
        """
        self.release() # in case someone forgot to cleanup
        for key in ['api_key','ckan_url','ckan_cfg']:
            if self._portal_cfg.get(key) is None:
                raise Exception("Portal config missing key %s" % (key))
        for key in ['ds_host','bucket','org_name']:
            if repo_cfg.get(key) is None:
                raise Exception("Repository config missing key %s" % (key))
        self._repo_name = repo_cfg.get('bucket')
        self._ckan_site = ckanapi.RemoteCKAN(self._portal_cfg.get('ckan_url'),
                                             apikey=self._portal_cfg.get('api_key'))
        self._ckan_cfg = self._portal_cfg.get('ckan_cfg')
        self._tmp_dir = tempfile.mkdtemp()
        org_name = repo_cfg.get('org_name')
        ds_host = repo_cfg.get('ds_host')

        try:
            self.logger.debug('Building portal data from bucket: %s' % (self._repo_name))
            repo = datastore.Repository(datastore.Host(host=ds_host), self._repo_name)
            repo_dataset_names = repo.list()

            # Get a list of existing CKAN groups so repeated groups don't get recreated.
            existing_groups = self._ckan_site.action.group_list()
            groups_to_cleanup = {}
            self.logger.debug("Existing groups:" + str(existing_groups))

            # Get a full list of all existing dataset in CKAN along side their meta data so that
            # 1. deleted dataset can be tracked and removed
            # 2. last mod time of the dataset can be compare to decide if that dataset needs to be rebuild.
            datasets_in_portal = self._ckan_site.action.current_package_list_with_resources()
    
            for ds_dataset_name in repo_dataset_names:
                self.logger.debug("Building repository:%s dataset:%s" % (self._repo_name, ds_dataset_name))
                dataset_name = ckan_dataset_name(ds_dataset_name, repo_name=self._repo_name)
                build_dataset_portal_data = True
                # Look for the dataset in the portal.
                for dataset in datasets_in_portal:
                    if dataset['name'] == dataset_name:
                        if self._dataset_audit is not None:
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
                    # Only published resources/datasets should show on portal
                    if not resource.is_published():
                        continue

                    pseudo_path = ds_dataset_name.split('/')
                    dataset = Dataset(
                        name = dataset_name,
                        title = pseudo_path[-1], # the last directory of the pseudo path is the title of the dataset
                        owner_org = org_name,
                        description = resource.metadata.get('description',''))
                    # Bring over other optional fields from the metadata.
                    optional_fields = ['author','author_email','maintainer','maintainer_email','version']
                    for field in optional_fields:
                        setattr(dataset, field, resource.metadata.get(field, ""))

                    # Create the groups if there are not there yet. Needs to happen before the dataset is created in CKAN.
                    group_names = pseudo_path[0:-1]
                    dataset.groups = []
                    for group_name in group_names:
                        group_ckan_name = ckan_usable_string(group_name)
                        if group_ckan_name not in existing_groups:
                            self.logger.info("Group %s not found, creating group..." % (group_ckan_name))
                            self._ckan_site.action.group_create(name=group_ckan_name, title=group_name)
                            existing_groups.append(group_ckan_name)
                        dataset.groups.append({'name':group_ckan_name})

                    # Custom fields
                    dataset.extras = []
                    # Exclude these fields to avoid error when adding to ckan dataset
                    exclude_fields = optional_fields + ['name', 'title', 'owner_org', 'description', 'state']
                    for k,v in resource.metadata.iteritems():
                        if k in exclude_fields:
                           continue
                        dataset.extras.append({'key':k, 'value':v})

                    # Build and upload the manifest file into this dataset.
                    self._create_ckan_dataset(dataset)
                    self._create_visualization_resource(dataset_name=dataset.name, ds_resource=resource)
                    self._create_download_file(dataset=dataset, ds_resource=resource, repo_cfg=repo_cfg)
                    self._create_metadata_file(dataset_name=dataset.name, ds_resource=resource)
                    self._create_manifest_file(dataset_name=dataset.name, ds_resource=resource)

                # else don't need to update the dataset as it hasn't changed.

                if not is_running():
                    break # 
            # end-for ds_dataset_name in repo_dataset_names

        finally:
            self.release()


"""
PortalBuilder is a class that encapsulates operations required to build a data portal with
information about research data and resources store in an object storage (such as S3).
"""
class PortalBuilder:
    def __init__(self, logger=None):
        self._cfg = {}
        self._ckan_site = None
        self.logger = logger or logging.getLogger(__name__)
        pass


    def load_config(self, from_file=None, from_string=None):
        """ Loads the portal builder configuration file either from a file or from a YAML string.
        :raises: IOError if the config can't be loaded.
        """
        try:
            if from_file:
                self.logger.info("Using config from " + from_file)
                if not os.path.exists(from_file):
                    raise FatalError("Error: portal data builder config file %s not found." % (from_file))
                cfg_file = open(from_file)
                if not cfg_file:
                    raise IOError("Unable to open config file %s".format(from_file))
                self._cfg = yaml.load(cfg_file)

            elif from_string:
                self._cfg = yaml.load(from_string)

            else:
                raise FatalError("Error: Unable to load portal data builder config without any configuration")

        except IOError as e:
            raise FatalError("Failed to load load config file, reason:" + str(e))

        except YAMLError as e:
            raise FatalError("Failed to parse configuration, reason:" + str(e))


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
        :raises: Exception if there is any critical failure.
        :returns: True if build was completely successful, False if there was a non-critical failure
        """

        # Validate config
        check_cfg(self._cfg, ['repos', 'api_key', 'ckan_cfg', 'ckan_url', 'download_template'],)
        self.logger.info("Building portal: %s" % (repo_name if repo_name else "ALL"))

        ckan_site = ckanapi.RemoteCKAN(self._cfg['ckan_url'], apikey=self._cfg['api_key'])
        datasets_before_build = ckan_site.action.current_package_list_with_resources()
        datasets_touched = {}
        for repo in self._cfg['repos']:
            check_cfg(repo, ['bucket','ds_host','org_name',], name='the repo config')

            if repo_name is not None and repo['bucket'] != repo_name:
                continue

            repo_builder = RepositoryBuilder(portal_builder=self, portal_cfg=self._cfg)
            repo_builder.set_dataset_audit(datasets_touched)
            try:
                repo_builder.build_portal_from_repo(repo_cfg=repo)

            except Exception as e:
                self.logger.error("Portal data building failed " + str(e))
                repo_builder.release()
                raise

            repo_builder.release()
            if not is_running():
                break # terminate asap

        # Clean up leftover (i.e. datasets that were not touched are assume to be deleted from datastore)
        # This will only take place if the priming is for all repo, otherwise some dataset might not be 'touched'.
        no_failure = True
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
                            self.logger.debug("Marking group %s for audit" % (group['name']))
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
                            self.logger.info("Purging group '%s' from portal" % (group))
                            ckan_site.action.group_purge(id=group)
                """

            except Exception as e:
                self.logger.error("Portal data building failed " + str(e))
                no_failure = False

        return no_failure
            

    def build_portal(self, repo_name=None):
        """ Same as _build_portal() but wraps around a lock so that only one
        portal building can be done at a time.
        :raises: Exception if there is any critical failure.
        :returns: True if build was completely successful, False if there was a non-critical failure
        """
        # Prevent more than one portal building from taking place.
        build_lock = prepare_lock_file(self._cfg.get('build_lock_file', "/tmp/portal_building"))
        try:
            self.logger.debug("Attempt to acquire build lock")
            build_lock.acquire(1)
        except LockTimeout:
            self.logger.warn("Unable to acquire build lock")
            raise Exception("Unable to obtain build lock, probably another process is building the portal data.")

        no_failure = False
        try:
            no_failure = self._build_portal(repo_name=repo_name)
        finally:
            build_lock.release()
            self.logger.debug("Build lock released")

        return no_failure


    def get_nap_duration(self):
        """ Return the configured cycle nap duration in seconds """
        return self._cfg.get('cycle_nap_in_mins', 60) * 60


    def get_config(self, key, default):
        """ Return a config setting from the configuration file, returning 'default' if setting is not there """
        return self._cfg.get(key, default)


    def setup_organizations(self, repo_name=None):
        """ Check that the organizations in the configuration file exist
        and if not create them.
        :param repo_name: Only setup the organization for that repo config.
        """
        # Validate config
        check_cfg(self._cfg, ['repos', 'api_key', 'ckan_url'],)
        api_key = self._cfg['api_key']

        for repo in self._cfg['repos']:
            check_cfg(repo, ['bucket','org_name','org_title'], name='the repo config')
            if repo_name is not None and repo['bucket'] != repo_name:
                continue
            # Prepare a CKAN connection for use.
            ckan_host = self._cfg['ckan_url']
            org_name = repo['org_name']
            site = ckanapi.RemoteCKAN(ckan_host, apikey=api_key)
            orgs = site.action.organization_list()
            if org_name not in orgs:
                self.logger.info("Organization %s does not exist yet, creating one..." % (org_name))
                site.action.organization_create(name=org_name,
                                                title=repo['org_title'],
                                                description=repo['org_title'])
            else:
                self.logger.info("Organization %s already exists, skipping setup" % (org_name))


    def remove_all_datasets(self):
        """ Remove all datasets that are in the current portal.  """
        # Validate config
        check_cfg(self._cfg, ['api_key', 'ckan_cfg', 'ckan_url'],)

        ckan_site = ckanapi.RemoteCKAN(self._cfg['ckan_url'], apikey=self._cfg['api_key'])
        datasets_in_portal = ckan_site.action.package_list()
        self.logger.info("Removing {0} datasets from the portal".format(len(datasets_in_portal)))

        for ds in datasets_in_portal:
            purge_ckan_dataset(ds, self._cfg['ckan_cfg'])



def _prepare_logging(args):
    """ Prepare logging mode based on args passed in during launch. """
    if args.log_ini:
        logging.config.fileConfig(args.log_ini)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARN)


_running = True
def is_running():
    # Can be mocked during unit test
    global _running
    return _running  


def stop_running():
    global _running
    _running = False


def init_running_state():
    """ Used by unit test to reset the running state of the daemon """
    global _running
    _running = True
 
def sigterm_handler(signal, frame):
    """ When SIGTERM is received, start shutting down the daemon """
    stop_running()
    logging.getLogger(__name__).warning("Terminate signal received, daemon shutting down")


def portal_data_builder_entry(cmd_args):
    ret_code = 0
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
        description='BDKD Portal Data Builder V%s\nTo build the data of a BDKD Portal so that it is synchronized '
                    'with the BDKD Data Repository in an object store.' % (__version__))

    parser.add_argument('command',
                        help='The command to execute, which can be:\n'
                             ' update - to update the portal using metadata from the datastore\n'
                             ' daemon - to run the portal update as a daemon process\n'
                             ' setup  - setup the organizations in the config file\n'
                             ' purge  - purge all datasets from this portal\n'
                             ' reprime  - purge and rebuild all datasets for this portal\n'
    )
    parser.add_argument('--cycle', type=int, help='Maximum number of build cycle to run when running as daemon')
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('-b', '--bucket-name', help='Select the bucket to build from (must be in the config)')
    parser.add_argument('-l', '--log-ini', help='Specify a logging ini file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run in verbose mode (INFO)')
    parser.add_argument('--debug', action='store_true', help='Run in very verbose mode (DEBUG)')
    if len(cmd_args)<=1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args(args=cmd_args[1:])

    if args.command not in ['update','daemon','setup','purge','reprime']:
        sys.exit('Unknown command %s' % (args.command))

    if not args.config:
        sys.exit('Please specify the configuration file to use')

    if args.command == 'update':
        _prepare_logging(args)
        portal_builder = PortalBuilder()
        portal_builder.load_config(from_file=args.config)
        portal_builder.build_portal(repo_name=args.bucket_name)

    elif args.command == 'setup':
        _prepare_logging(args)
        portal_builder = PortalBuilder()
        portal_builder.load_config(from_file=args.config)
        portal_builder.setup_organizations(repo_name=args.bucket_name)

    elif args.command == 'purge' or args.command == 'reprime':
        _prepare_logging(args)
        portal_builder = PortalBuilder()
        portal_builder.load_config(from_file=args.config)
        portal_builder.remove_all_datasets()
        if args.command == 'reprime':
            portal_builder.build_portal()

    elif args.command == 'daemon':
        # run builder in daemonize mode (note: setup logging after daemonized)
        # pidfile = FileLock('/tmp/portal_data_builder.pid'))
        portal_builder = PortalBuilder()
        try:
            portal_builder.load_config(from_file=args.config)
        except FatalError as e:
            logging.getLogger(__name__).critical(
                "Portal data building not started due to a critical failure: " + str(e))
            return 1

        from lockfile.pidlockfile import PIDLockFile
        context = daemon.DaemonContext(
            pidfile = PIDLockFile(portal_builder.get_config('pidfile','/tmp/portal_data_builder.pid')),
            signal_map = {
                signal.SIGTERM: sigterm_handler,
                }
            )
        with context:
            init_running_state()
            _prepare_logging(args)
            nap_duration = portal_builder.get_nap_duration()
            max_cycle = args.cycle
            while is_running():
                try:
                    portal_builder.build_portal()
                except FatalError as e:
                    logging.getLogger(__name__).critical(
                        "Portal data building terminating due to a critical failure: " + str(e))
                    stop_running()
                    ret_code = 1
                except Exception as e:
                    logging.getLogger(__name__).error("Portal data building has failed: " + str(e))
                    # If there is a monitoring system, we will raise an alert here.
                    # Otherwise drop back to sleep, hopefully next cycle the failure
                    # would have recovered.
                    # We don't want to re-raise here or the daemon will terminates.

                # during testing, we can put cap on the number of build cycles.
                if max_cycle:
                    max_cycle -= 1
                    if max_cycle <= 0 and is_running():
                        stop_running()

                if is_running():
                    time.sleep(nap_duration)
            logging.getLogger(__name__).info("Daemon terminated")

    return ret_code

def main():
    portal_data_builder_entry(sys.argv)

if __name__=='__main__':
    main()
