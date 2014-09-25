import pytest
import yaml
import time
from subprocess import call
from bdkd import datastore
import ckanapi

default_test_bucket = "bdkd-qa-bucket"

class SampleData:
    
    def __init__(self, dataset_name, dataset_files = [], auto_delete=True, description=None):
        self._repo = None
        self._auto_delete = auto_delete
        self.dataset_name = dataset_name
        self._dataset_files = dataset_files
        self._repo_name = default_test_bucket
        self._desc = description

    def _get_dataset_name(self):
        return self.dataset_name

    def _get_repo_name(self):
        return self._repo_name

    def get_dataset_id(self):
        return '{0}-{1}'.format(
            self._get_repo_name(), 
            self._get_dataset_name())
        
    def data_repo(self):
        if not self._repo:
            self._repo = datastore.repository(self._repo_name)
        return self._repo


    def _save_dataset(self):
        """ Adds a sample dataset into the test bucket for use.
        """
        dataset = datastore.Resource.new(
            self.dataset_name,
            self._dataset_files,
            {
                'description': self._desc,
                'author': 'test author',
                'author_email': 'test@test.email',
            })
        repo = self.data_repo()
        repo.save(dataset, overwrite=True)

    def get_ds_resource(self):
        return self.data_repo().get(self.dataset_name)

    def delete_dataset(self):
        """ Remove the sample dataset.
        """
        repo = self.data_repo()
        repo.delete(self.dataset_name)

    def __del__(self):
        if self._auto_delete:
            self.delete_dataset()

    def prepare(self):
        repo = self.data_repo()
        datasets = repo.list()
        if not self.dataset_name in datasets:
            # Not there yet, add it.
            self._save_dataset()
            # Wait until it is there or if the time has exceeded.
            tm_start = time.time()
            while not self.dataset_name in repo.list():
                time.sleep(1)
                if (time.time() - tm_start) > 5:
                    raise Exception("Timeout waiting for the test dataset to appear in the datastore")
            self._prepared = True


class Portal_Builder_Runner:
    """ For starting/stopping a portal builder during test.
    """
    def __init__(self):
        self._cfg_filename = '/etc/bdkd/portal.cfg'
        self._cfg = None

    def use_config(self, cfg_filename):
        self._cfg_filename = cfg_filename
        self._cfg = None # reset

    def run_update(self):
        """ Run the portal dat builder to build up the portal immediately.
        """
        call(["portal-data-builder", "-c", self._cfg_filename, "update"])

    def start_daemon(self):
        """ Starts the portal data builder as a daemon process.
        """
        # TODO
    pass

    def stop_daemon(self):
        """ Stop the portal data builder daemon process.
        """
        # TODO
    pass

    def get_portal_config(self):
        if not self._cfg:
            self._cfg = yaml.load(open(self._cfg_filename))
        return self._cfg

    def get_ckan_api_key(self):
        cfg = self.get_portal_config()
        return cfg['api_key']


@pytest.fixture
def portal_builder():
    return Portal_Builder_Runner()
    

@pytest.fixture
def ckan_site(portal_builder):
    return ckanapi.RemoteCKAN("http://localhost", apikey=portal_builder.get_ckan_api_key())


@pytest.fixture(scope='session')
def sample_data1():
    return SampleData(dataset_name='sample_dataset1',
                      description='laser in ocean',
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'])


@pytest.fixture(scope='session')
def sample_data2():
    return SampleData(dataset_name='sample_dataset2',
                      description='laser in space',
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'])

