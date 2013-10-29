#!/usr/bin/env python

import boto.s3.connection
import errno
import hashlib
import json
import logging
import os, stat, sys, time
import shutil
import urlparse, urllib2
import yaml
import re

_config_global_file = '/etc/bdkd/Current/datastore.conf'
_config_user_file = os.path.expanduser(os.environ.get('BDKD_DATASTORE_CONFIG', '~/.bdkd_datastore.conf'))
_settings = None
_hosts = None
_repositories = None

TIME_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'

logger = logging.getLogger(__name__)

def checksum(local_path):
    """ Calculate the md5sum of the contents of a local file. """
    result = None
    if os.path.exists(local_path):
        with open(local_path) as local_file:
            result = hashlib.md5(local_file.read()).hexdigest()
    return result

def mkdir_p(dest_dir):
    """ Make a directory, including all parent directories. """
    try:
        os.makedirs(dest_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

def common_directory(paths):
    """
    Find the directory common to a set of paths.

    This function differs from os.path.commonprefix() which has no concept of 
    directories (it works a character at a time).  This function breaks each 
    path up into directories for comparison.
    """
    common_parts = []
    shortest_path = None
    for path in paths:
        parts = path.split(os.sep)
        if shortest_path == None:
            shortest_path = len(parts)
        elif len(parts) < shortest_path:
            shortest_path = len(parts)
        for i in range(0, len(parts)):
            if i >= len(common_parts):
                common_parts.append(parts[i])
            else:
                if parts[i] != common_parts[i]:
                    common_parts[i] = None
    common_count = 0
    common_parts = common_parts[0:shortest_path]
    for common_part in common_parts:
        if common_part == None:
            break
        else:
            common_count += 1
    common_parts = common_parts[0:common_count]
    if common_count:
        leading = ''
        if paths[0][0] == os.sep:
            leading = os.sep
        common_path = leading + os.path.join(*common_parts)
    else:
        common_path = ''

    return common_path
    

def touch(fname, times=None):
    """ Update the timestamps of a local file. """
    with file(fname, 'a'):
        os.utime(fname, times)

class Host(object):
    """
    A host that provides a S3-compatible service.
    """
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
    """
    Storage container for a Resource and its Files.

    The Repository may be backed by a S3 host, in which case operations may 
    involve coordinating reads and writes between a remote object store and a 
    local filesystem cache.
    """
    resources_prefix = 'resources'
    files_prefix = 'files'

    def __init__(self, host, name, cache_path=None, working_path=None, stale_time=60):
        """
        Create a "connection" to a Repository.
        """
        self.host = host
        self.name = name

        self.local_cache = os.path.join(
                (cache_path or settings()['cache_root']),
                str(os.getuid()),
                name)
        self.working = os.path.join(
                (working_path or settings()['working_root']), 
                str(os.getuid()), 
                str(os.getpid()), 
                name)
        self.bucket = None
        self.stale_time = stale_time

    def get_bucket(self):
        """
        Get the S3 bucket for this Repository (or None if no host is configured).
        """
        if self.host and not self.bucket:
            try:
                self.bucket = self.host.connection.get_bucket(self.name)
            except: #I want to narrow this down, but the docs are not clear on what can be raised...
                print >>sys.stderr, 'Error accessing repository "{0}"'.format(self.name)
                raise
        return self.bucket

    def __resource_name_key(self, name):
        # For the given Resource name, return the S3 key string
        return os.path.join(type(self).resources_prefix, name)

    def __resource_name_cache_path(self, name):
        # For the given Resource name, return the path that would be used for a 
        # local cache file
        return os.path.join(self.local_cache, type(self).resources_prefix, name)

    def __resource_name_working_path(self, name):
        # For the given Resource name, return the working path to which that 
        # Resource would be copied if it were edited.
        return os.path.join(self.working, type(self).resources_prefix, name)

    def __file_keyname(self, resource_file):
        # For the given ResourceFile, return the S3 key string
        return resource_file.location()

    def __file_cache_path(self, resource_file):
        # For the given ResourceFile, return the path that would be used for a 
        # local cache file
        return os.path.expanduser(os.path.join(self.local_cache, 
            resource_file.location_or_remote()))

    def __file_working_path(self, resource_file):
        return os.path.join(self.working, type(self).files_prefix, 
            resource_file.location_or_remote())

    def __download(self, key_name, dest_path):
        # Ensure that a file on the local system is up-to-date with respect to 
        # an object in the S3 repository, downloading it if required.  Returns 
        # True if the remote object was downloaded.
        bucket = self.get_bucket()
        if not bucket:
            return False
        local_exists = os.path.exists(dest_path)
        if local_exists and self.stale_time and (time.time() - os.stat(dest_path)[stat.ST_MTIME]) < self.stale_time:
            logger.debug("Not refreshing %s: not stale", dest_path)
            return False
        key = bucket.get_key(key_name)
        if key:
            logger.debug("Key %s exists", key_name)
            if local_exists:
                if key.etag.strip('"') == checksum(dest_path):
                    logger.debug("Checksum match -- no need to refresh")
                    try:
                        touch(dest_path)
                    except IOError, e:
                        if e.errno != errno.EACCES:
                            raise
                        else:
                            mode = os.stat(dest_path).st_mode
                            os.chmod(dest_path, stat.S_IRWXU|stat.S_IRWXG)
                            touch(dest_path)
                            os.chmod(dest_path, mode)
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
        # Ensure that an object in the S3 repository is up-to-date with respect 
        # to a file on the local system, uploading it if required.  Returns 
        # True if the local file was uploaded.
        bucket = self.get_bucket()
        if not bucket:
            return False
        do_upload = True
        file_key = bucket.get_key(key_name)
        if file_key:
            logger.debug("Existing key %s", key_name)
            if file_key.etag.strip('"') == checksum(src_path):
                logger.debug("Local file %s unchanged", src_path)
                do_upload = False
        else:
            logger.debug("New key %s", key_name)
            file_key = boto.s3.key.Key(bucket, key_name)
        if do_upload:
            logger.debug("Uploading to %s from %s", key_name, src_path)
            file_key.set_contents_from_filename(src_path)
        return do_upload

    def __delete(self, key_name):
        # Delete the object identified by the key name from the S3 repository
        bucket = self.get_bucket()
        if bucket:
            key = boto.s3.key.Key(bucket, key_name)
            bucket.delete_key(key)

    def __refresh_remote(self, url, local_path, etag=None, mod=stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
        remote = urllib2.urlopen(urllib2.Request(url))
        if remote.info().has_key('etag'):
            if remote.info().getheader('etag') == etag:
                return False
        if remote.info().has_key('last-modified')and os.path.exists(local_path):
            local_mtime = os.stat(local_path).st_mtime
            last_modified = time.mktime(time.strptime(
                remote.info().getheader('last-modified'),
                TIME_FORMAT))
            if last_modified < local_mtime:
                return False
        # Need to download file
        if os.path.exists(local_path):
            os.remove(local_path)
        mkdir_p(os.path.dirname(local_path))
        with open(local_path, 'w') as fh:
            shutil.copyfileobj(remote, fh)
        remote.close()
        os.chmod(local_path, mod)
        return True

    def __delete_resource_file(self, resource_file):
        key_name = self.__file_keyname(resource_file)
        bucket = self.get_bucket()
        if bucket and key_name:
            self.__delete(key_name)
        cache_path = self.__file_cache_path(resource_file)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def __delete_resource(self, resource):
        for resource_file in resource.files:
            self.__delete_resource_file(resource_file)
        key_name = self.__resource_name_key(resource.name)
        bucket = self.get_bucket()
        if bucket and key_name:
            self.__delete(key_name)
        cache_path = self.__resource_name_cache_path(resource.name)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def __resource_name_conflict(self, resource_name):
        """ 
        Check whether a Resource name conflicts with some existing Resource.
        
        Returns the name(s) of any conflicting Resources or None if no conflict 
        found.
        """
        resources_prefix = type(self).resources_prefix

        bucket = self.get_bucket()
        if bucket:
            # Check for conflict with a longer path name
            key_prefix = self.__resource_name_key(resource_name) + '/'
            resource_names = []
            for key in bucket.list(key_prefix):
                resource_names.append(key.name[(len(type(self).resources_prefix) + 1):])
            if len(resource_names) > 0:
                # There are other Resources whose names start with this 
                # Resource name
                return resource_names

            # Check for conflict with a shorter name
            name_parts = resource_name.split('/')[0:-1]
            while len(name_parts):
                key_name = self.__resource_name_key('/'.join(name_parts))
                key = bucket.get_key(key_name)
                if key:
                    return [ key_name ]
                name_parts = name_parts[0:-1]
        return None


    def _refresh_resource_file(self, resource_file):
        cache_path = self.__file_cache_path(resource_file)
        logger.debug("Cache path for resource file is %s", cache_path)
        bucket = self.get_bucket()
        if bucket:
            location = resource_file.location()
            if location:
                if self.__download(location, cache_path):
                    logger.debug("Refreshed resource file from %s to %s", location, cache_path)
                else:
                    logger.debug("Not refreshing resource file %s to %s", location, cache_path)
            else:
                self.__refresh_remote(resource_file.remote(), cache_path, resource_file.meta('ETag'))
            resource_file.path = cache_path
        return cache_path

    def refresh_resource(self, resource, refresh_all=False):
        """
        Synchronise a locally-cached Resource with the Repository's remote host 
        (if applicable).

        This method ensures that the local Resource is up-to-date with respect 
        to the S3 object store.  However if there is no Host for this 
        Repository then no action needs to be performed.
        """
        bucket = self.get_bucket()
        if not bucket:
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
            bucket = self.get_bucket()
            if bucket:
                file_keyname = self.__file_keyname(resource_file)
                self.__upload(file_keyname, file_cache_path)
        resource_file.is_edit = False
        
    def edit_resource(self, resource):
        """
        Copy a Resource to the working area of the Repository and make it 
        read/write.

        The Resource is refreshed first, to ensure that its files in the cache 
        are current, then it is copied to the Repository's working area so that 
        it can be edited independently of other processes.  After editing 
        save() may be called to write the modified Resource back to the 
        repository.

        Note that no locking mechanism is provided here: it is possible for two 
        independent processes to edit the same Resource and for stale data to 
        be saved back to the Repository.  In contexts where synchronous edits 
        are required that process should be managed by some other means.
        """
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

    def save(self, resource, overwrite=False):
        """
        Save a Resource that is either new or being edited to the Repository.
        """
        if not resource.is_edit:
            raise ValueError("Resource is not currently being edited")

        conflicting_names = self.__resource_name_conflict(resource.name)
        if conflicting_names:
            raise ValueError("The Resource name '" + resource.name +
                    "' conflicts with other Resource names including: " +
                    ', '.join(conflicting_names))

        resource_cache_path = self.__resource_name_cache_path(resource.name)
        resource.write(resource_cache_path)
        bucket = self.get_bucket()
        if bucket:
            resource_keyname = self.__resource_name_key(resource.name)
            resource_key = bucket.get_key(resource_keyname)
            if resource_key:
                if overwrite:
                    self.delete(resource)
                else:
                    raise ValueError("Resource already exists!")
            else:
                resource_key = boto.s3.key.Key(bucket, resource_keyname)
            logger.debug("Uploading resource from %s to key %s", resource_cache_path, resource_keyname)
            resource_key.set_contents_from_filename(resource_cache_path)
        if resource.repository != self:
            logger.debug("Setting the repository for the resource")
            resource.repository = self
        resource.is_edit = False

        for resource_file in resource.files:
            self.__save_resource_file(resource_file)

    def list(self, prefix=''):
        """
        List all Resource names available in the Repository.

        If 'prefix' is provided then a subset of resources with that leading 
        path will be returned.
        """
        resource_names = []
        resources_prefix = type(self).resources_prefix
        if prefix:
            resources_prefix = os.path.join(resources_prefix, prefix)
        bucket = self.get_bucket()
        if bucket:
            for key in bucket.list(resources_prefix):
                resource_names.append(key.name[(len(type(self).resources_prefix) + 1):])
        return resource_names

    def get(self, name):
        """
        Acquire a Resource by name.

        Returns the named resource, or None if no such resource exists in the 
        Repository.
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

    def delete(self, resource_or_name):
        """
        Delete a Resource -- either directly or by name.
        """
        resource = None
        if isinstance(resource_or_name, Resource):
            resource = resource_or_name
            self.refresh_resource(resource)
        else:
            resource = self.get(resource_or_name)
            if not resource:
                return
        self.__delete_resource(resource)
        resource.repository = None


class Asset(object):
    """
    Superclass of things that can be stored within a Repository.  This includes 
    Resource and ResourceFile objects.

    :ivar path:
        The local filesystem path of the Asset
    :ivar is_edit:
        Whether the Asset is currently in edit mode
    :ivar metadata:
        Dictionary of meta-data key/value pairs
    """
    def __init__(self):
        self.path = None
        self.is_edit = False
        self.metadata = None

    def relocate(self, dest_path, mod=stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
        """
        Relocate an Asset's file to some other path, and set the mode of the 
        relocated file.

        This method is used when moving a Resource or a ResourceFile to a 
        working path so that it can be edited.
        """
        if self.path:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            else:
                mkdir_p(os.path.dirname(dest_path))
            shutil.copy2(self.path, dest_path)
            os.chmod(dest_path, mod)
            self.path = dest_path
    
    def meta(self, keyname):
        """
        Get the meta-data value for the given key.
        """
        if self.metadata:
            return self.metadata.get(keyname, None)
        else:
            return None


class Resource(Asset):
    """
    A source of data consisting of one or more files plus associated meta-data.

    :ivar repository:
        The Repository to which this Resource belongs (if applicable)
    :ivar name:
        The name of the Resource (uniquely identifying it within its 
        Repository)
    :ivar files:
        A list of the ResourceFile instances associated with this Resource
    """
    class ResourceJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Resource):
                resource = dict(name=o.name, **o.metadata)
                file_data = []
                if o.files:
                    for resource_file in o.files:
                        file_data.append(resource_file.metadata)
                resource['files'] = file_data
                return resource
            else:
                return json.JSONEncoder.default(self, o)


    def __init__(self, name, files=None, **kwargs):
        """
        Constructor for a Resource given a name, file data and any meta-data.
        """
        super(Resource, self).__init__()

        self.repository = None
        self.name = name
        self.metadata = kwargs
        self.files = files

    @classmethod
    def __normalise_file_data(cls, raw_data):
        files_data = [] ; common_prefix = ''
        location_paths = []
        if not isinstance(raw_data, list):
            raw_data = [ raw_data ]
        for file_data in raw_data:
            path = None
            location = None
            meta = None
            if isinstance(file_data, dict):
                meta = file_data
                path = meta.pop('path', None)
            else:
                # String form: either a repository or remote location
                meta = {}
                url = urlparse.urlparse(file_data)
                if url.netloc:
                    meta['remote'] = file_data
                else:
                    path = file_data
            if not 'remote' in meta:
                location = os.path.expanduser(path)
                location_paths.append(os.path.dirname(location))
            files_data.append(dict(path=path, location=location, meta=meta))
        # Get the common prefix of all local paths
        if len(location_paths):
            if len(location_paths) > 1:
                common_prefix = common_directory(location_paths)
            else:
                common_prefix = location_paths[0]
            # Strip common prefix from all files with a location
            for file_data in files_data:
                if file_data['location'] != None:
                    file_data['location'] = file_data['location'][len(common_prefix):]
                    if file_data['location'][0] == '/':
                        file_data['location'] = file_data['location'][1:]
        return files_data

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
            files_data = cls.__normalise_file_data(files_data)
            for file_data in files_data:
                path = file_data.pop('path', None)
                location = file_data.pop('location', None)
                meta = file_data.pop('meta', None)
                if 'remote' in meta:
                    remote_url = urllib2.urlopen(urllib2.Request(meta['remote']))
                    keyset = set(k.lower() for k in meta)
                    for header_name in [ 'etag', 'last-modified', 'content-length', 'content-type' ]:
                        if not header_name in keyset and remote_url.info().has_key(header_name):
                            meta[header_name] = remote_url.info().getheader(header_name)
                else:
                    meta['location'] = os.path.join(Repository.files_prefix, name, location)
                    if path:
                        path = os.path.expanduser(path)
                        if not 'md5sum' in meta:
                            meta['md5sum'] = checksum(path)
                        if not 'last-modified' in meta:
                            meta['last-modified'] = time.strftime(TIME_FORMAT,
                                    time.gmtime(os.path.getmtime(path)))
                        if not 'content-length' in meta:
                            meta['content-length'] = os.stat(path).st_size
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

    def to_json(self, **kwargs):
        """
        Create a JSON string representation of the Resource: its files and 
        meta-data.
        """
        return Resource.ResourceJSONEncoder(**kwargs).encode(self)

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
            fh.write(self.to_json())
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
            self.repository.refresh_resource(self, True)
        paths = []
        for resource_file in self.files:
            paths.append(resource_file.path)
        return paths

    def files_matching(self, pattern):
        """
        Return a list of ResourceFile objects where the location or remote 
        matches a given pattern.

        If no files match an empty array is returned.
        """
        matches = []
        for resource_file in self.files:
            if re.search(pattern, resource_file.location_or_remote()):
                matches.append(resource_file)
        return matches

    def file_ending(self, suffix):
        """
        Returns the first ResourceFile ending with the given suffix.

        If no ResourceFiles match, None is returned.
        """
        for resource_file in self.files:
            if resource_file.location_or_remote().endswith(suffix):
                return resource_file
        return None

class ResourceFile(Asset):
    """
    A file component of a Resource, including any file-specific meta-data 
    fields.

    Note that a ResourceFile may point to a repository object ("location") or 
    some other file stored on the Internet ("remote").
    """
    def __init__(self, path, resource=None, **kwargs):
        """
        Constructor for a Resource file given a local filesystem path, the 
        Resource that owns the ResourceFile, and any other meta-data.
        """
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
        """
        Get the meta-data "location" of the ResourceFile (if it is stored in 
        the Repository) or None.
        """
        return self.meta('location')

    def remote(self):
        """
        Get the "remote" URL of the ResourceFile (if it is stored elsewhere on 
        the Internet) or None.
        """
        return self.meta('remote')

    def location_or_remote(self):
        """
        Get either the "location" or "remote" -- whichever is applicable.
        """
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
                    if 'host' in repo_config:
                        host = _hosts[repo_config['host']]
                    else:
                        host = None
                    cache_path = os.path.expanduser(
                            repo_config.get('cache_path', 
                                os.path.join(_settings['cache_root'])))
                    working_path = os.path.expanduser(
                            repo_config.get('working_path', 
                                os.path.join(_settings['working_root'])))
                    stale_time = repo_config.get('stale_time', 60)
                    repo = Repository(host, repo_name, cache_path, working_path, stale_time)
                    _repositories[repo_name] = repo

def settings():
    """
    Get a dictionary of the configured settings for BDKD Datastore.

    These settings may originate from the system-wide configuration (in /etc) 
    or user-specific configuration.
    """
    global _settings
    if not _settings:
        __load_config()
    return _settings

def hosts():
    """
    Get a dictionary of the configured hosts for BDKD Datastore.
    """
    global _hosts
    if not _hosts:
        __load_config()
    return _hosts

def repositories():
    """
    Get a dictionary of all configured Repositories, by name.
    """
    global _repositories
    if not _repositories:
        __load_config()
    return _repositories

def repository(name):
    """
    Get a configured Repository by name, or None if no such Repository was 
    configured.
    """
    return repositories().get(name, None)
