#!/usr/bin/env python

import boto.s3.connection
import io
import errno
import hashlib
import json
import logging
import os, stat, sys, time, getpass
from datetime import datetime
import shutil
import urlparse, urllib2
import yaml
import re
import warnings
import copy
import tarfile
import posixpath

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

_config_global_file = '/etc/bdkd/Current/datastore.conf'
_config_user_file = os.path.expanduser(os.environ.get('BDKD_DATASTORE_CONFIG', '~/.bdkd_datastore.conf'))
_settings = None
_hosts = None
_repositories = None

TIME_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'
ISO_8601_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

logger = logging.getLogger(__name__)

def get_uid():
    """
    Get a unique user identifier in a cross-platform manner.
    On Unix type systems, this equates os.getuid; otherwise,
    getpass.getuser
    """
    try:
        return os.getuid()
    except AttributeError:
        return getpass.getuser()

def checksum(local_path):
    """ Calculate the md5sum of the contents of a local file. """
    result = None
    if os.path.exists(local_path):
        md5 = hashlib.md5()
        with open(local_path,'rb') as f: 
            for chunk in iter(lambda: f.read(1048576), b''): 
                md5.update(chunk)
        result = md5.hexdigest()
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
        if len(paths[0]) and paths[0][0] == os.sep:
            leading = os.sep
        common_path = leading + posixpath.join(*common_parts)
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
    def __init__(   self, access_key=None, secret_key=None, 
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
    bundle_prefix = 'bundle'

    def __init__(self, host, name, cache_path=None, stale_time=60):
        """
        Create a "connection" to a Repository.
        """
        self.host = host
        self.name = name

        self.local_cache = posixpath.join(
                (cache_path or settings()['cache_root']),
                str(get_uid()),
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
        return posixpath.join(type(self).resources_prefix, name)

    def __resource_name_cache_path(self, name):
        # For the given Resource name, return the path that would be used for a 
        # local cache file
        return posixpath.join(self.local_cache, type(self).resources_prefix, name)

    def __file_keyname(self, resource_file):
        # For the given ResourceFile, return the S3 key string
        return resource_file.location()

    def __file_cache_path(self, resource_file):
        # For the given ResourceFile, return the path that would be used for a 
        # local cache file
        return os.path.expanduser(posixpath.join(self.local_cache,
            resource_file.location_or_remote()))

    def _rebuild_required(self, resource, obj_list):
        # For the given resource, check if a file list rebuild is necessary by
        # comparing the timestamp most recently modified file to that of metadata
        # file
        resource_keyname = self.__resource_name_key(resource.name)
        resource_key = self.get_bucket().get_all_keys(prefix=resource_keyname)[0]
        resource_timestamp = datetime.strptime(resource_key.last_modified, ISO_8601_UTC_FORMAT)
        rebuild_required = False
        for obj in obj_list:
            obj_timestamp = datetime.strptime(obj.last_modified, ISO_8601_UTC_FORMAT)
            if obj_timestamp > resource_timestamp:      # i.e. if object is newer than resource metadata
                rebuild_required = True
                break

        return rebuild_required


    def file_path(self, resource_file):
        return self.__file_cache_path(resource_file)

    def rebuild_file_list(self, resource):
        bucket = self.get_bucket()
        if not bucket:
            return False
        # TODO: Fix '/' with more general solution with BDKD-262
        prefix = Repository.files_prefix + '/' + resource.name
        obj_list = bucket.get_all_keys(prefix=prefix)
        if not self._rebuild_required(resource, obj_list):
            logger.debug("Rebuild not required")
            return False

        new_files = {}
        for obj in obj_list:
            found = False
            for r_files in resource.files:
                if obj.key == r_files.location():
                    found = True
                    break
            if not found:       # if not currently in resource
                if obj.key.endswith(".bdkd") and obj.key[:-5] in new_files:
                    # If this is a .bdkd file, delete (since S3 always returns
                    # values in alphabetical order, we can assume the main
                    # file is already in the list)
                    obj.delete()
                    continue

                md5file = bucket.get_all_keys(prefix=obj.key + ".bdkd")
                obj_md5 = ""
                if len(md5file) == 1:
                    obj_md5 = md5file[0].get_contents_as_string().strip()
                else:
                    logger.warning("Unable to get MD5 sum for {0}".format(obj.key))
                new_files[obj.key] = obj.size, obj.last_modified, obj_md5

        resource.add_files_from_storage_paths(new_files)
        return True



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
            with open(dest_path, 'wb') as fh:
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
        with open(local_path, 'wb') as fh:
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
        for resource_file in (resource.files + [resource.bundle]):
            if resource_file:
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

    def _resource_file_dest_path(self, resource_file):
        dest_path = self.__file_cache_path(resource_file)
        logger.debug("Cache path for resource file is %s", dest_path)
        return dest_path

    def _refresh_resource_file(self, resource_file):
        dest_path = self._resource_file_dest_path(resource_file)
        bucket = self.get_bucket()
        if bucket and not resource_file.is_bundled():
            location = resource_file.location()
            if location:
                if self.__download(location, dest_path):
                    logger.debug("Refreshed resource file from %s to %s", location, dest_path)
                else:
                    logger.debug("Not refreshing resource file %s to %s", location, dest_path)
            else:
                self.__refresh_remote(resource_file.remote(), dest_path, resource_file.meta('ETag'))
            resource_file.path = dest_path
        return dest_path

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
        file_cache_path = self.__file_cache_path(resource_file)
        if resource_file.path and os.path.exists(resource_file.path) and resource_file.location():
            if resource_file.path != file_cache_path:
                resource_file.relocate(file_cache_path)
            bucket = self.get_bucket()
            if bucket:
                file_keyname = self.__file_keyname(resource_file)
                self.__upload(file_keyname, resource_file.path)

    def save(self, resource, overwrite=False, update_bundle=True):
        """
        Save a Resource to the Repository.
        """
        conflicting_names = self.__resource_name_conflict(resource.name)
        if conflicting_names:
            raise ValueError("The Resource name '" + resource.name +
                    "' conflicts with other Resource names including: " +
                    ', '.join(conflicting_names))

        resource_cache_path = self.__resource_name_cache_path(resource.name)
        resource.write(resource_cache_path)
        resource.path = resource_cache_path

        if resource.repository != self:
            logger.debug("Setting the repository for the resource")
            resource.repository = self

        if resource.bundle:
            if update_bundle:
                resource.update_bundle()
                self.__save_resource_file(resource.bundle)
        else:
            for resource_file in resource.files:
                self.__save_resource_file(resource_file)

        bucket = self.get_bucket()

        if bucket:
            resource_keyname = self.__resource_name_key(resource.name)
            resource_key = bucket.get_key(resource_keyname)
            if resource_key:
                if not overwrite:
                    raise ValueError("Resource already exists!")
            else:
                resource_key = boto.s3.key.Key(bucket, resource_keyname)
            logger.debug("Uploading resource from %s to key %s", resource_cache_path, resource_keyname)
            resource_key.set_contents_from_filename(resource_cache_path)

    def move(self, from_resource, to_name):
        try:
            self.copy(from_resource, to_name)
            from_resource.reload(from_resource.path)
            from_resource.delete()
        except Exception as e:
            print >>sys.stderr, e.message
            raise

    def copy(self, from_resource, to_name):
        """
        Copy resource from its original position to the given name in this repository.
        """
        # Get destination bucket (needs to exist)
        to_bucket = self.get_bucket()
        if not to_bucket:
            raise ValueError("Can only rename into a storage-backed repository")
        # Check that from_resource has a bucket
        from_bucket = None
        if from_resource.repository:
            from_bucket = from_resource.repository.get_bucket()
        if not from_bucket:
            raise ValueError("Can only rename a Resource into a storage-backed repository")
        # Check that to_name has no conflicts with existing resources
        conflicting_names = self.__resource_name_conflict(to_name)
        if conflicting_names:
            raise ValueError("The Resource name '" + to_name +
                    "' conflicts with other Resource names including: " +
                    ', '.join(conflicting_names))
        # Check that name is not already in use
        to_keyname = self.__resource_name_key(to_name)
        to_key = to_bucket.get_key(to_keyname)
        if to_key:
            raise ValueError("Cannot rename: name in use")
        # Create unsaved destination resource (also checks name)
        to_resource = Resource(to_name, files=[],
                metadata=copy.copy(from_resource.metadata))
        # Copy files to to_resource and save
        try:
            from_prefix = posixpath.join(Repository.files_prefix, from_resource.name, '')
            for from_file in from_resource.files:
                to_file = copy.copy(from_file)
                # Do S3 copy if in S3 (i.e. has 'location')
                if 'location' in from_file.metadata:
                    to_location = posixpath.join(Repository.files_prefix,
                            to_resource.name, 
                            from_file.metadata['location'][len(from_prefix):])
                    if not from_file.is_bundled():
                       to_bucket.copy_key(to_location, from_bucket.name, 
                               from_file.metadata['location'])
                    to_file.metadata['location'] = to_location
                # Add file to to_resource
                to_resource.files.append(to_file)
            if from_resource.bundle:
                to_resource.bundle = copy.copy(from_resource.bundle)
                to_resource.bundle.resource = to_resource
                from_location = from_resource.bundle.metadata['location']
                to_location = posixpath.join(Repository.files_prefix,
                        to_resource.name,
                        from_location[len(from_prefix):])
                to_bucket.copy_key(to_location, from_bucket.name,
                        from_location)
                to_resource.bundle.metadata['location'] = to_location

            # Save destination resource
            self.save(to_resource, update_bundle=False)
        except Exception as e:
            print >>sys.stderr, e.message
            # Undo: delete all to-files if save failed
            for to_file in to_resource.files:
                if 'location' in to_file.metadata:
                    self.__delete_resource_file(to_file)
            to_resource.delete()
            raise

    def list(self, prefix=''):
        """
        List all Resource names available in the Repository.

        If 'prefix' is provided then a subset of resources with that leading 
        path will be returned.
        """
        resource_names = []
        resources_prefix = type(self).resources_prefix
        if prefix:
            resources_prefix = posixpath.join(resources_prefix, prefix)
        bucket = self.get_bucket()
        if bucket:
            for key in bucket.list(resources_prefix):
                resource_names.append(key.name[(len(type(self).resources_prefix) + 1):])
        else:
            resource_path = posixpath.join(self.local_cache,
                    type(self).resources_prefix)
            for (dirpath, dirnames, filenames) in os.walk(resource_path):
                if len(filenames):
                    for filename in filenames:
                        resource_names.append(posixpath.join(
                            dirpath[(len(resource_path) + 1):], filename))
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


    def get_resource_key(self, name, key_attr=None):
        """
        Acquire the key for a resource in the object storage.
        :param name:  name of the resource
        :param key_attr:  the attribute of the key of interest (error purposes)
        :returns: the boto key for the resource
        """
        bucket = self.get_bucket()
        if not bucket:
            if key_attr is None:
                key_attr = 'the bucket'
            raise ValueError('Cannot get %s for this repository.' %s (key_attr))
        key_name = self.__resource_name_key(name)
        key = bucket.get_key(key_name)
        if not key:
            raise ValueError('Key %s does not exist in the repository' % (key_name))
        return key


    def get_resource_last_modified(self, name):
        """
        Acquire the last modified time of the resource (only look at the resource
        meta data rather than interrogate every single files under that resource)
        :param name:  name of the resource
        :returns: the last modified date/time in a long string format as per S3
        """
        key = self.get_resource_key(name, key_attr='last modified date')
        return boto.utils.parse_ts(key.last_modified)

class Asset(object):
    """
    Superclass of things that can be stored within a Repository.  This includes 
    Resource and ResourceFile objects.

    :ivar path:
        The local filesystem path of the Asset
    :ivar metadata:
        Dictionary of meta-data key/value pairs
    """
    def __init__(self):
        self.path = None
        self.metadata = None
        self.files = None

    def relocate(self, dest_path, mod=stat.S_IRWXU,
            move=False):
        """
        Relocate an Asset's file to some other path, and set the mode of the 
        relocated file.
        """
        if self.path:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            else:
                mkdir_p(os.path.dirname(dest_path))
            if move:
                shutil.move(self.path, dest_path)
            else:
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


class MetadataException(Exception):
    def __init__(self, missing_fields):
        self.missing_fields = missing_fields

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
                resource = dict(name=o.name)
                if o.metadata:
                    resource['metadata'] = o.metadata
                file_data = []
                if o.files:
                    for resource_file in o.files:
                        file_data.append(resource_file.metadata)
                resource['files'] = file_data
                if o.bundle:
                    resource['bundle'] = o.bundle.metadata
                return resource
            else:
                return json.JSONEncoder.default(self, o)

    mandatory_metadata_fields = ['description', 'author', 'author_email']

    @classmethod
    def validate_name(cls, name):
        if isinstance(name, basestring):
            if ( len(name) and
                    name[0] != '/' and
                    name[-1] != '/' ):
                return True
        return False

    @classmethod
    def bundle_temp_path(cls, name):
        return posixpath.join(settings()['cache_root'], str(get_uid()), name)

    def __init__(self, name, files=None, bundle=None, metadata=None, publish=True):
        """
        Constructor for a Resource given a name, file data and any meta-data.
        """
        if name and not type(self).validate_name(name):
            raise ValueError("Invalid resource name!")

        super(Resource, self).__init__()

        self.repository = None
        self.name = name
        if metadata and not isinstance(metadata, dict):
            raise ValueError("Meta-data must be a dictionary")
        self.metadata = metadata or dict()
        self.bundle = bundle
        self.files = files
        self._published = publish

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
    def new(cls, name, files_data=None, metadata=None, do_bundle=False, publish=True):
        """
        A convenience factory method that creates a new, unsaved Resource of 
        the given name, using file information and metadata.

        The file data can be a single string filename or a dictionary of file 
        metadata.  The filename can either be a local path ('path') or a 
        remote URL ('remote') that is either HTTP or FTP.  For more than one 
        file provide an array of these.

        The rest of the keyword arguments are used as Resource meta-data.

        The Resource and all its ResourceFile objects ready to be saved to a Repository.
        """
        resource_files = []
        bundle = None
        if files_data:
            if do_bundle:
                bundle_path = cls.bundle_temp_path(name)
                bundle = ResourceFile(bundle_path, resource=None, metadata={
                    'location': posixpath.join(Repository.files_prefix, name,
                        '.bundle', 'bundle.tar.gz')})
                mkdir_p(os.path.dirname(bundle_path))
                bundle.files = []
                bundle_archive = tarfile.open(name=bundle_path, mode='w:gz')
                # resource_files.append(bundle)
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
                    if do_bundle:
                        meta['bundled'] = True
                    meta['location'] = posixpath.join(Repository.files_prefix, name, location)
                    if path:
                        path = os.path.expanduser(path)
                        if not 'md5sum' in meta:
                            meta['md5sum'] = checksum(path)
                        if not 'last-modified' in meta:
                            meta['last-modified'] = time.strftime(TIME_FORMAT,
                                    time.gmtime(os.path.getmtime(path)))
                        if not 'content-length' in meta:
                            meta['content-length'] = os.stat(path).st_size
                        if bundle:
                            bundle_archive.add(name=path, arcname=location)
                    else:
                        raise ValueError("For Resource files, either a path to a local file or a remote URL is required")
                resource_file = ResourceFile(path, resource=None, metadata=meta)
                resource_files.append(resource_file)
            if do_bundle:
                bundle_archive.close()
        resource = cls(name, files=resource_files, metadata=metadata, publish=publish)
        if publish:
            missing_fields = resource.validate_mandatory_metadata()
            if missing_fields:
                raise MetadataException(missing_fields)

        if do_bundle:
            resource.bundle = bundle
        for resource_file in resource_files:
            resource_file.resource = resource
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

    def validate_mandatory_metadata(self):
        """
        Checks if mandatory fields are present, and the values are not None.
        Returns list of fields that are not found.

        """
        fields_not_found = []
        for field in Resource.mandatory_metadata_fields:
            if not field in self.metadata or self.metadata[field] is None:
                fields_not_found.append(field)
        return fields_not_found

    def add_files_from_storage_paths(self, file_paths):

        for path, (size, last_modified, md5sum) in file_paths.iteritems():
            meta = {}
            meta['location'] = path
            meta['content-length'] = size
            dt = datetime.strptime(last_modified, ISO_8601_UTC_FORMAT)
            meta['last-modified'] = datetime.strftime(dt, TIME_FORMAT) + " UTC"
            meta['md5sum'] = md5sum
            resource_file = ResourceFile(path, resource=None, metadata=meta)
            self.files.append(resource_file)


    def reload(self, local_resource_filename):
        """
        Reload a Resource from a Resource metadata file (local).
        """
        if local_resource_filename and os.path.exists(local_resource_filename):
            resource_files = []
            with io.open(local_resource_filename, encoding='UTF-8') as fh:
                data = json.load(fh)
            files_data = data.pop('files', [])
            for file_data in files_data:
                resource_files.append(ResourceFile(None, resource=self, 
                    metadata=file_data))
            bundle_data = data.pop('bundle', None)
            if bundle_data:
                self.bundle = ResourceFile(None, resource=self,
                        metadata=bundle_data)
            self.name = data.pop('name', None)
            self.path = local_resource_filename
            self.metadata = data.get('metadata', dict())
            self.files = resource_files

    def to_json(self, **kwargs):
        """
        Create a JSON string representation of the Resource: its files and 
        meta-data.
        """
        return Resource.ResourceJSONEncoder(ensure_ascii=False, 
                encoding='UTF-8', **kwargs).encode(self)

    def write(self, dest_path, mod=stat.S_IRWXU):
        """
        Write the JSON file representation of a Resource to a destination file.
        """
        if os.path.exists(dest_path):
            os.remove(dest_path)
        else:
            mkdir_p(os.path.dirname(dest_path))
        with io.open(dest_path, encoding='UTF-8', mode='w') as fh:
            logger.debug("Writing JSON serialised resource to %s", dest_path)
            fh.write(unicode(self.to_json()))
        os.chmod(dest_path, mod)
        self.path = dest_path
    
    def local_paths(self):
        """
        Get a list of local filenames for all the File data associated with 
        this Resource.

        (Note that this method will trigger a refresh of the Resource, ensuring that all
        locally-stored data is relatively up-to-date.)
        """
        if self.repository:
            self.repository.refresh_resource(self, True)
        paths = []
        do_refresh = True
        if self.bundle:
            self.bundle.unpack_bundle(do_refresh=True)
        for resource_file in self.files:
            paths.append(resource_file.local_path())
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
        match = None
        for resource_file in self.files:
            if resource_file.location_or_remote().endswith(suffix):
                if match:
                    warnings.warn("Found multiple files: also '" +
                            match.location_or_remote() + "'", RuntimeWarning)
                match = resource_file
        return match

    def update_bundle(self):
        """
        Update the bundle with any local file changes.
        """
        if not self.bundle:
            return  # no-op
        bundle_file = tarfile.open(self.bundle.local_path(), mode='w:gz')
        for resource_file in self.files:
            if resource_file.path and resource_file.location():
                storage_location = resource_file.storage_location()
                bundle_file.add(resource_file.path, 
                        resource_file.storage_location())
        bundle_file.close()

    def save(self):
        """
        Helper method that saves the resource back to the repository that
        it was loaded from. Can only save if the resource was loaded from a
        repository, otherwise it throws.
        """
        if not self.repository:
            raise ValueError("Cannot save a resource that is not loaded from a repository")
        # Always overwrite the existing one since it was loaded from the repository anyway.
        self.repository.save(self, overwrite=True)

    def delete(self):
        if not self.repository:
            raise ValueError("Cannot delete a resource that is not loaded from a repository")
        self.repository.delete(self)

    def is_bundled(self):
        return self.bundle != None

class ResourceFile(Asset):
    """
    A file component of a Resource, including any file-specific meta-data 
    fields.

    Note that a ResourceFile may point to a repository object ("location") or 
    some other file stored on the Internet ("remote").
    """
    def __init__(self, path, resource=None, metadata=None):
        """
        Constructor for a Resource file given a local filesystem path, the 
        Resource that owns the ResourceFile, and any other meta-data.
        """
        super(ResourceFile, self).__init__()

        self.metadata = metadata
        self.resource = resource
        self.path = path

    def is_bundled(self):
        return (self.metadata and 'bundled' in self.metadata)

    def bundle_dirname(self):
        """
        Get the directory where bundled files are to be unpacked.
        """
        if self.is_bundled() and self.path and self.path.endswith('.tar.gz'):
            return self.path.split('.tar.gz')[0]
        else:
            return None

    def unpack_bundle(self, do_refresh=True):
        """
        If this ResourceFile is bundled, unpack its contents to the bundle path.
        """
        if not self.resource or not self.resource.repository:
            return
        unpack_path = posixpath.join(self.resource.repository.local_cache,
                Repository.files_prefix, self.resource.name)
        if not self.path:
            do_refresh = True
        resource_filename = self.local_path()
        if not os.path.exists(unpack_path):
            mkdir_p(unpack_path)
        bundle_file = tarfile.open(resource_filename)
        bundle_file.extractall(path=unpack_path)
        bundle_file.close()

    def local_path(self):
        """
        Get the local filename for this File's data.

        (Note that this method will trigger a refresh of this File, ensuring 
        that all locally-stored data is relatively up-to-date.  Only this File 
        is refreshed: not the Resource, nor the Resource's other File objects.)
        """
        if (self.resource and self.resource.repository):
            if self.is_bundled():
                self.path = self.resource.repository._resource_file_dest_path(self)
                if not os.path.exists(self.path):
                    self.resource.local_paths()  # Trigger refresh
            else:
                if self.resource.meta('unified'):
                    self.resource.repository.refresh_resource(self.resource, True)
                else:
                    self.resource.repository._refresh_resource_file(self)
        try:
            return str(self.path)
        except UnicodeEncodeError:
            return self.path

    def location(self):
        """
        Get the meta-data "location" of the ResourceFile (if it is stored in 
        the Repository) or None.
        """
        return self.meta('location')

    def storage_location(self):
        """
        The path of a ResourceFile within its Resource directory.
        """
        if self.resource and self.location():
            return self.location()[(len(posixpath.join(Repository.files_prefix,
                self.resource.name)) + 1):]
        else:
            return None

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
                    if 'access_key' in host_config:
                        params['access_key'] = host_config['access_key']
                    if 'secret_key' in host_config:
                        params['secret_key'] = host_config['secret_key']
                    host = Host(**params)
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
                                posixpath.join(_settings['cache_root'])))
                    stale_time = repo_config.get('stale_time', 60)
                    repo = Repository(host, repo_name, cache_path, stale_time)
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
