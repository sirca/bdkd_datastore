#!/usr/bin/env python

import boto.s3.connection
import hashlib
import json
import logging
import os, stat, time
import shutil
import urlparse
import yaml

_config_global_file = '/etc/bdkd/datastore.conf'
_config_user_file = os.path.expanduser(os.environ.get('BDKD_DATASTORE_CONFIG', '~/.bdkd_datastore.conf'))
_settings = None
_hosts = None
_repositories = None

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def checksum(local_path):
    result = None
    if os.path.exists(local_path):
        with open(local_path) as local_file:
            result = hashlib.md5(local_file.read()).hexdigest()
    return result

def mkdir_p(dest_dir):
    try:
        os.makedirs(dest_dir)
    except OSError, e:
        if e.errno != 17:
            raise
        pass

class Host(object):
    def __init__(   self, access_key, secret_key, 
                    host='s3.amazonaws.com', port=None, 
                    secure=True, calling_format=boto.s3.connection.OrdinaryCallingFormat()):

        self.connection = boto.s3.connection.S3Connection(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                host=host, port=port,
                is_secure=secure,
                calling_format=calling_format)
        self.netloc = '{0}:{1}'.format(host,port)


class Repository(object):
    resources_prefix = 'resources'
    files_prefix = 'files'

    def __init__(self, host, name, cache_path=None, working_path=None, stale_time=60):
        self.host = host
        self.name = name

        if cache_path:
            self.local_cache = cache_path
        else:
            self.local_cache = os.path.join(settings()['cache_root'], name)
        if working_path:
            self.working = working_path
        else:
            self.working = os.path.join(settings()['working_root'], name)
        if host:
            try:
                self.bucket = host.connection.get_bucket(name)
            except: #I want to narrow this down, but the docs are not clear on what can be raised...
                print >>sys.stderr, 'Error accessing repository "{0}"'.format(name)
                raise
        else:
            self.bucket = None
        self.stale_time = stale_time

    def __resource_name_key(self, name):
        return os.path.join(type(self).resources_prefix, name)

    def __resource_name_cache_path(self, name):
        return os.path.join(self.local_cache, type(self).resources_prefix, name)

    def __resource_name_working_path(self, name):
        return os.path.join(self.working, str(os.getpid()), 
                type(self).resources_prefix, name)

    def __file_keyname(self, resource_file):
        return resource_file.location()

    def __file_cache_path(self, resource_file):
        return os.path.join(self.local_cache, resource_file.location_or_remote())

    def __file_working_path(self, resource_file):
        return os.path.join(self.working, str(os.getpid()), 
                type(self).files_prefix, resource_file.location_or_remote())

    def __download(self, key_name, dest_path):
        if not self.bucket:
            return False
        local_exists = os.path.exists(dest_path)
        if local_exists and self.stale_time and (time.time() - os.stat(dest_path)[stat.ST_MTIME]) < self.stale_time:
            logger.debug("Not refreshing %s: not stale", dest_path)
            return False
        key = self.bucket.get_key(key_name)
        if key:
            logger.debug("Key %s exists", key_name)
            if local_exists:
                if key.etag.strip('"') == checksum(dest_path):
                    logger.debug("Checksum match -- no need to refresh")
                    return False
                else:
                    logger.debug("Removing destination file %s before overwriting", dest_path)
                    os.remove(dest_path)
            else:
                mkdir_p(os.path.dirname(dest_path))
                with open(dest_path, 'w') as fh:
                    logger.debug("Retrieving repository data to %s", dest_path)
                    key.get_contents_to_file(fh)
                return True
        else:
            logger.debug("Key %s does not exist in repository, not refreshing", key_name)
            return False

    def __upload(self, key_name, src_path):
        do_upload = True
        file_key = self.bucket.get_key(key_name)
        if file_key:
            logger.debug("Existing key %s", key_name)
            if file_key.etag.strip('"') == checksum(src_path):
                logger.debug("Local file %s unchanged", src_path)
                do_upload = False
        else:
            logger.debug("New key %s", key_name)
            file_key = boto.s3.key.Key(self.bucket, key_name)
        if do_upload:
            logger.debug("Uploading to %s from %s", key_name, src_path)
            file_key.set_contents_from_filename(src_path)
        return do_upload

    def __refresh_remote(self, url, cache_path):
        # TODO: implement refresh remote resource based on "last modified" header
        pass

    def _refresh_resource_file(self, resource_file):
        cache_path = self.__file_cache_path(resource_file)
        logger.debug("Cache path for resource file is %s", cache_path)
        if self.bucket:
            location = resource_file.location()
            if location:
                if self.__download(location, cache_path):
                    logger.debug("Refreshed resource file from %s to %s", location, cache_path)
                else:
                    logger.debug("Not refreshing resource file %s to %s", location, cache_path)
            else:
                self.__refresh_remote(resource_file.remote(), cache_path)
            resource_file.path = cache_path
        return cache_path

    def refresh_resource(self, resource, refresh_all=False):
        if not self.bucket:
            return
        cache_path = self.__resource_name_cache_path(resource.name)
        resource_key = self.__resource_name_key(resource.name)
        if self.__download(resource_key, cache_path) or refresh_all:
            if os.path.exists(cache_path):
                resource.reload(cache_path)
            for resource_file in resource.files:
                self._refresh_resource_file(resource_file)
                logger.debug("Refreshed resource file with path %s", resource_file.path)

    def __save_resource_file(self, resource_file):
        if not resource_file.is_edit:
            raise ValueError("Resource file is not currently being edited")
        file_cache_path = self.__file_cache_path(resource_file)
        if resource_file.path and os.path.exists(resource_file.path) and resource_file.location():
            if resource_file.path != file_cache_path:
                resource_file.relocate(file_cache_path)
            if self.bucket:
                file_keyname = self.__file_keyname(resource_file)
                self.__upload(file_keyname, file_cache_path)
        resource_file.is_edit = False
        
    def edit_resource(self, resource):
        self.refresh_resource(resource)
        for resource_file in resource.files:
            file_working_path = self.__file_working_path(resource_file)
            mkdir_p(os.path.dirname(file_working_path))
            resource_file.relocate(file_working_path, stat.S_IRWXU)
            resource_file.is_edit = True
        resource_working_path = self.__resource_name_working_path(resource.name)
        mkdir_p(os.path.dirname(resource_working_path))
        resource.relocate(resource_working_path, stat.S_IRWXU)
        resource.is_edit = True

    def save(self, resource):
        if not resource.is_edit:
            raise ValueError("Resource is not currently being edited")

        for resource_file in resource.files:
            self.__save_resource_file(resource_file)

        resource_cache_path = self.__resource_name_cache_path(resource.name)
        resource.write(resource_cache_path)
        if self.bucket:
            resource_keyname = self.__resource_name_key(resource.name)
            logger.debug("Uploading resource from %s to key %s", resource_cache_path, resource_keyname)
            resource_key = boto.s3.key.Key(self.bucket, resource_keyname)
            resource_key.set_contents_from_filename(resource_cache_path)
        if resource.repository != self:
            logger.debug("Setting the repository for the resource")
            resource.repository = self
        resource.is_edit = False

    def list(self, prefix=''):
        """
        List all Resource names available in the Repository.
        """
        resource_names = []
        resources_prefix = type(self).resources_prefix
        if prefix:
            resources_prefix = os.path.join(resources_prefix, prefix)
        if self.bucket:
            for key in self.bucket.list(resources_prefix):
                resource_names.append(key.name[(len(type(self).resources_prefix) + 1):])
        return resource_names

    def get(self, name):
        """
        Acquire a Resource by name.

        Returns the named resource, or None if no such resource exists in the Repository.
        """
        keyname = self.__resource_name_key(name)
        cache_path = self.__resource_name_cache_path(name)
        self.__download(keyname, cache_path)
        if os.path.exists(cache_path):
            resource = Resource.load(cache_path)
            resource.repository = self
            return resource
        else:
            return None


class Asset(object):
    def __init__(self):
        self.path = None
        self.is_edit = False

    def relocate(self, dest_path, mod=stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
        if self.path:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            else:
                mkdir_p(os.path.dirname(dest_path))
            shutil.copy2(self.path, dest_path)
            os.chmod(dest_path, mod)
            self.path = dest_path


class Resource(Asset):
    class ResourceJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Resource):
                resource = dict(name=o.name, **o.metadata)
                file_data = []
                for rfile in o.files:
                    file_data.append(rfile.metadata)
                resource['files'] = file_data
                return resource
            else:
                return json.JSONEncoder.default(self, o)


    def __init__(self, name, files=None, **kwargs):
        super(Resource, self).__init__()

        self.repository = None
        self.name = name
        self.metadata = kwargs
        self.files = files

    @classmethod
    def new(cls, name, files_data=None, **kwargs):
        """
        A convenience factory method that creates a new, unsaved Resource of 
        the given name, using file information and metadata.

        The file data can be a single string filename or a dictionary of file 
        metadata.  The filename can either be a local path ('path') or a 
        remote URL ('remote') that is either HTTP or FTP.  For more than one 
        file provide an array of these.

        The rest of the keyword arguments are used as Resource meta-data.

        The Resource and all its ResourceFile objects are set to edit mode, 
        i.e. ready to be saved to a Repository.
        """
        resource_files = []
        if files_data:
            if not isinstance(files_data, list):
                files_data = [ files_data ]
            for file_data in files_data:
                location = None
                remote = None
                path = None
                meta = None
                if isinstance(file_data, dict):
                    meta = file_data
                    remote = meta.pop('remote', None)
                    path = meta.pop('path', None)
                else:
                    # String form: either a repository or remote location
                    meta = {}
                    url = urlparse.urlparse(file_data)
                    if url.netloc:
                        remote = file_data
                    else:
                        path = file_data
                if remote:
                    meta['remote'] = remote
                else:
                    meta['location'] = os.path.join(Repository.files_prefix, name, os.path.basename(path))
                    if path:
                        path = os.path.expanduser(path)
                        meta['chksum'] = checksum(path)
                        meta['size'] = os.stat(path).st_size
                    else:
                        raise ValueError("For Resource files, either a path to a local file or a remote URL is required")
                resource_file = ResourceFile(path, **meta)
                resource_file.is_edit = True
                resource_files.append(resource_file)
        resource = cls(name, resource_files, **kwargs)
        for resource_file in resource_files:
            resource_file.resource = resource
        resource.is_edit = True
        return resource
    
    @classmethod
    def load(cls, local_resource_filename):
        """
        Load a Resource from a local JSON file containing Resource meta-data.
        """
        resource = cls(None, None)
        resource.reload(local_resource_filename)
        resource.path = local_resource_filename
        return resource

    def reload(self, local_resource_filename):
        """
        Reload a Resource from a Resource metadata file (local).
        """
        if local_resource_filename and os.path.exists(local_resource_filename):
            resource_files = []
            with open(local_resource_filename) as fh:
                data = json.load(fh)
            files_data = data.pop('files', [])
            for file_data in files_data:
                resource_files.append(ResourceFile(None, self, **file_data))
            self.name = data.pop('name', None)
            self.path = local_resource_filename
            self.metadata = data
            self.files = resource_files

    def write(self, dest_path, mod=stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
        """
        Write the JSON file representation of a Resource to a destination file.
        """
        if os.path.exists(dest_path):
            os.remove(dest_path)
        else:
            mkdir_p(os.path.dirname(dest_path))
        with open(dest_path, 'w') as fh:
            logger.debug("Writing JSON serialised resource to %s", dest_path)
            fh.write(Resource.ResourceJSONEncoder().encode(self))
        os.chmod(dest_path, mod)
        self.path = dest_path
    
    def local_paths(self):
        """
        Get a list of local filenames for all the File data associated with 
        this Resource.

        (Note that this method will trigger a refresh of the Resource if it is 
        not currently being edited, ensuring that all locally-stored data is 
        relatively up-to-date.)
        """
        if self.repository and not self.is_edit:
            self = self.repository.refresh_resource(self, True)
        paths = []
        for resource_file in self.files:
            paths.append(resource_file.path)
        return paths


class ResourceFile(Asset):
    def __init__(self, path, resource=None, **kwargs):
        super(ResourceFile, self).__init__()

        self.metadata = kwargs
        self.resource = resource
        self.path = path

    def local_path(self):
        """
        Get the local filename for this File's data.

        (Note that this method will trigger a refresh of this File, ensuring 
        that all locally-stored data is relatively up-to-date.  Only this File 
        is refreshed: not the Resource, nor the Resource's other File objects.)
        """
        if self.resource and self.resource.repository and not self.is_edit:
            self.resource.repository._refresh_resource_file(self)
        return self.path

    def location(self):
        if self.metadata:
            return self.metadata.get('location', None)

    def remote(self):
        if self.metadata:
            return self.metadata.get('remote', None)

    def location_or_remote(self):
        return self.location() or self.remote()


def __load_config():
    global _settings, _hosts, _repositories
    _settings = {}
    _hosts = {}
    _repositories = {}
    for file_name in [_config_global_file, _config_user_file]:
        if os.path.exists(file_name):
            with open(file_name) as f:
                config = yaml.load(f)

            # Update settings
            if 'settings' in config and config['settings']:
                _settings.update(config['settings'])
            
            # Update hosts
            if 'hosts' in config and config['hosts']:
                for host_name, host_config in config['hosts'].iteritems():
                    # create host
                    params = {}
                    if 'host' in host_config:
                        params['host'] = host_config['host']
                    if 'port' in host_config:
                        params['port'] = host_config['port']
                    if 'secure' in host_config:
                        params['secure'] = host_config['secure']
                    host = Host(
                            host_config['access_key'], 
                            host_config['secret_key'],
                            **params)
                    _hosts[host_name] = host
            
            # Update repositories
            if 'repositories' in config and config['repositories']:
                for repo_name, repo_config in config['repositories'].iteritems():
                    cache_path = None
                    if 'cache_path' in repo_config:
                        if repo_config['cache_path'][0] == '~':
                            cache_path = os.path.expanduser(repo_config['cache_path'])
                        elif not repo_config['cache_path'][0] == '/':
                            cache_path = os.path.join(_settings['cache_root'], repo_config['cache_path'])
                        else:
                            cache_path = repo_config['cache_path']
                    if 'host' in repo_config:
                        host = _hosts[repo_config['host']]
                    else:
                        host = None
                    repo = Repository(host, repo_name, cache_path)
                    _repositories[repo_name] = repo


def settings():
    global _settings
    if not _settings:
        __load_config()
    return _settings

def hosts():
    global _hosts
    if not _hosts:
        __load_config()
    return _hosts

def repositories():
    global _repositories
    if not _repositories:
        __load_config()
    return _repositories

def repository(name):
    return repositories().get(name, None)
