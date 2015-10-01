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
