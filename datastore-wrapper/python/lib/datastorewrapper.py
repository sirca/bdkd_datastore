# Copyright 2015 Nicta
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import os, os.path
import yaml
import json


local_config_file = '~/.bdkd_datastore.conf'
util_name = 'datastore-util'

def configure_datastore(configuration, overwrite=True):
    """Configures datastore by writing to ~/.bdkd_datastore.conf

    :param configuration: dictionary representing configuration
    :param overwrite: whether to overwrite any existing configuration (defaults to True)
    :returns: True if configuration was succesful
    """
    if not isinstance(configuration, dict):
        raise ValueError('configuration must be dictionary')

    if not ('settings' in configuration and 'hosts' in configuration and 'repositories' in configuration):
        raise ValueError('Invalid format for configuration')

    config_path = os.path.expanduser(local_config_file)

    if os.path.exists(config_path) and os.path.getsize(config_path) > 0 and overwrite == False:
        # Do not overwrite file if it has more than 0 bytes
        return False

    with open(config_path, 'w') as outfile:
        outfile.write(yaml.dump(configuration, default_flow_style=True))

    return True


def clear_config():
    """Deletes ~/.bdkd_datastore.conf
    """
    config_path = os.path.expanduser(local_config_file)
    if os.path.exists(config_path):
        os.remove(config_path)

class DatastoreError(Exception):
    """An error occured when running Datastore
    """
    pass

class Datastore:
    """Represents Datastore. 
    Attempts to connect to datastore-util on initialisation. Throws DatastoreError if unable to do so.
    """

    def _run_with_args(self, arg_list):
        run_args = [util_name] + arg_list
        p = subprocess.Popen(run_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        return out, err

    def __init__(self):
        """Init Datastore object
        """

        # Check if installed and ready
        try:
            out, err = self._run_with_args(['--help'])
        except OSError as e:
            raise DatastoreError('Could not run {0}'.format(util_name))

        out, err = self._run_with_args(['repositories'])
        if not out:
            raise DatastoreError('No repositories configured')


    def get_repositories(self):
        """Get list of configured Datastore repositories
        :returns: list of strings of datastore repository names
        """
        out, err = self._run_with_args(['repositories'])
        if err:
            raise DatastoreError('Unable to obtain repositories: {0}'.format(err))

        return out.strip().split('\n')

    def list(self, repository):
        """Lists contents of given Datastore repository

        :param repository: name of repository to list
        :return: list of strings representing files in datastore
        """
        if not repository:
            raise ValueError('Must specify a valid repository')

        out, err = self._run_with_args(['list', repository])

        if err:
            raise DatastoreError('Unable to list contents of repository "{0}": {1}'.format(repository, err))

        return out.strip().split('\n')

    def _validate_repository_and_dataset(self, repository, dataset):
        if not repository:
            raise ValueError('Must specify a valid repository')
        if not dataset:
            raise ValueError('Must specify a valid dataset')

    def get(self, repository, dataset):
        """For a given dataset in a repository, get all metadata and list of contents

        :param repository: name of repository
        :param dataset: name of dataset
        :return: dictionary containing list of files and all metadata
        """
        self._validate_repository_and_dataset(repository, dataset)

        out, err = self._run_with_args(['get', repository, dataset])

        if err:
            raise DatastoreError('Unable to get information on dataset "{0}": {1}'.format(dataset, err))

        val = {}
        try:
            val = json.loads(out)
        except ValueError as e:
            raise DatastoreError('Unable to parse JSON: {0}'.format(e))

        return val

    def files(self, repository, dataset):
        """Get all files from dataset and make them available locally

        :param repository: name of the repository
        :param dataset: name of the dataset
        :return: list of paths of locally cached files
        """
        self._validate_repository_and_dataset(repository, dataset)

        out, err = self._run_with_args(['files', repository, dataset])

        if err:
            raise DatastoreError('Unable to get local file list: {0}'.format(err))

        return out.strip().split('\n')

    def create(self, repository, dataset, metadata = {}, metadata_file = '', filenames = [], publish = False, force = False):
        """Creates a dataset on a given repository

        :param repository: name of repository
        :param dataset: name of dataset
        :param metadata: dictionary of 'description', 'author', 'author_email', 'data-type', 'version', 
               'maintainer' and 'maintainer-email'. Optional if 'metadata_file' parameter provided
        :param metadata_file: YAML file containing metadata. Optional if 'metadata' parameter provided
        :param filenames: List of local file names or URLs of remote files (HTTP, FTP)
        :param publish: Publish the dataset. Default False
        :param force: Force overwriting any existing dataset. Default False
        :return: True if dataset is successfully created
        """
        self._validate_repository_and_dataset(repository, dataset)
        
        # Validates metadata parameters
        if publish and not (metadata or metadata_file):
            raise ValueError('"metadata" or "metadata_file" parameters required when creating a published dataset')

        cmd = ['create']

        if metadata:
            for field in ['description', 'author', 'author-email', 'data-type', 'version', 'maintainer', 'maintainer-email']:
                if metadata.get(field):
                    cmd.append("--{0}={1}".format(field, metadata[field]))

        if metadata_file:
            cmd.append("--metadata-file={0}".format(metadata_file))

        if publish:
            cmd.append('--publish')
        else:
            cmd.append('--no-publish')
            
        if force:
            cmd.append('--force')

        cmd.append(repository)
        cmd.append(dataset)

        if filenames:
            for f in filenames:
                cmd.append(f)

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable to create dataset "{0}": {1}'.format(dataset, err))

        return True

    def delete(self, repository, dataset, force = False):
        """Deletes a dataset from a given repository

        :param repository: name of the repository
        :param dataset: name of the dataset
        :param force: Force deleting a published dataset. Default False
        :return: True if dataset is successfully deleted
        """
        self._validate_repository_and_dataset(repository, dataset)

        cmd = ['delete']
        if force:
            cmd.append('--force-delete-published')

        cmd.append(repository)
        cmd.append(dataset)

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable to delete: {0}'.format(err))

        return True


    def publish(self, repository, dataset):
        """Publishes a dataset from a given repository

        :param repository: name of the repository
        :param dataset: name of the dataset
        :return: True if dataset is successfully published
        """
        self._validate_repository_and_dataset(repository, dataset)

        cmd = ['publish', repository, dataset]

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable to publish: {0}'.format(err))

        return True


    def rebuild_file_list(self, repository, dataset):
        """Regenerates the file list metadata on a dataset

        :param repository: name of the repository
        :param dataset: name of the dataset
        :return: True if file list successfully regenerated
        """
        self._validate_repository_and_dataset(repository, dataset)

        cmd = ['rebuild-file-list', repository, dataset]

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable to rebuild file list : {0}'.format(err))

        return True

    def update_metadata(self, repository, dataset, metadata = {}, metadata_file = ''):
        """Updates the metadata of a dataset on a given repository

        :param repository: name of the repository
        :param dataset: name of the dataset
        :param metadata: dictionary of 'description', 'author', 'author_email', 'data-type', 'version', 
               'maintainer' and 'maintainer-email'. Optional if 'metadata_file' parameter provided
        :param metadata_file: YAML file containing metadata. Optional if 'metadata' parameter provided
        :return: True if metadata successfully updated
        """
        self._validate_repository_and_dataset(repository, dataset)

        cmd = ['update-metadata']

        if metadata:
            for field in ['description', 'author', 'author-email', 'data-type', 'version', 'maintainer', 'maintainer-email']:
                if metadata.get(field):
                    cmd.append("--{0}={1}".format(field, metadata[field]))

        if metadata_file:
            cmd.append("--metadata-file={0}".format(metadata_file))

        cmd.append(repository)
        cmd.append(dataset)

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable to update metadata : {0}'.format(err))

        return True

    def add_files(self, repository, dataset, filenames, add_to_published = False, 
                  overwrite = False, no_metadata = False):
        """Add files to an existing dataset from a given repository

        :param repository: name of the repository
        :param dataset: name of the dataset
        :param filenames: List of local file names or URLs of remote files (HTTP, FTP)
        :param add_to_published: Force adding files to a published dataset. Default False
        :param overwrite: Overwrite any existing file with the same name. Default False
        :param no_metadata: Do not update file list metadata. Default False
        :return: True if files successfully added
        """
        self._validate_repository_and_dataset(repository, dataset)
        
        if type(filenames) != list:
            raise ValueError('"filenames" parameter is not a list')

        cmd = ['add-files']
        
        if add_to_published:
            cmd.append('--add-to-published')

        if overwrite:
            cmd.append('--overwrite')

        if no_metadata:
            cmd.append('--no-metadata')

        cmd.append(repository)
        cmd.append(dataset)

        if filenames:
            for f in filenames:
                cmd.append(f)

        out, err = self._run_with_args(cmd)

        if err:
            raise DatastoreError('Unable add files: {0}'.format(err))

        return True
