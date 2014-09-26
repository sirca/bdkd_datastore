import pytest
import yaml
import time
from subprocess import call
from bdkd import datastore
import ckanapi
import psutil

default_test_bucket = "bdkd-qa-bucket"

class SampleData:
    
    def __init__(self, dataset_name, dataset_files = [], auto_delete=True, meta_data=None):
        self._repo = None
        self._auto_delete = auto_delete
        self.dataset_name = dataset_name
        self._dataset_files = dataset_files
        self._repo_name = default_test_bucket
        self._meta_data = meta_data

    def get_dataset_name(self):
        return self.dataset_name

    def get_repo_name(self):
        return self._repo_name

    def get_dataset_id(self):
        return '{0}-{1}'.format(
            self.get_repo_name(),
            self.get_dataset_name())
        
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
            self._meta_data)
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
                if (time.time() - tm_start) > 5:
                    raise Exception("Timeout waiting for the test dataset to appear in the datastore")
                time.sleep(1)
            self._prepared = True


class Portal_Builder_Runner:
    """ For starting/stopping a portal builder during test.
    """
    def __init__(self):
        self._cfg_filename = 'test_data/portal.cfg'
        self._cfg = None

    def use_config(self, cfg_filename):
        self._cfg_filename = cfg_filename
        self._cfg = None # reset

    def run_update(self):
        """ Run the portal dat builder to build up the portal immediately.
        """
        call(["portal-data-builder", "-c", self._cfg_filename, "update"])

    def daemon_running(self):
        """ check if the portal builder is running and return it as a process,
        otherwise returns None
        """
        for proc in psutil.process_iter():
            if proc.name() == 'portal-data-bui':
                return proc
        return None

    def start_daemon(self):
        """ Starts the portal data builder as a daemon process.
        """
        proc = self.daemon_running()
        if not proc:
            call(["portal-data-builder", "-c", self._cfg_filename, "daemon"])
            # wait a bit
            tm_start = time.time()
            while self.daemon_running() == None:
                if (time.time() - tm_start) > 5:
                    raise Exception("Timeout waiting for the portal builder daemon to start")
                time.sleep(1)


    def stop_daemon(self):
        """ Stop the portal data builder daemon process.
        """
        proc = self.daemon_running()
        if proc:
            proc.kill()

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
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'],
                      meta_data={
                          'description': 'laser in ocean',
                          'author': 'test author',
                          'author_email': 'test@test.email'})


@pytest.fixture(scope='session')
def sample_data2():
    return SampleData(dataset_name='sample_dataset2',
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'],
                      meta_data={
                          'description': 'laser in space',
                          'author': 'test author',
                          'author_email': 'test@test.email'})


# short live - only for test
@pytest.fixture()
def short_sample_data():
    return SampleData(dataset_name='shortlive_dataset',
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'],
                      meta_data={
                          'description': 'short live dataset',
                          'author': 'test author',
                          'author_email': 'test@test.email'})


@pytest.fixture(scope='session')
def visual_data1():
    return SampleData(dataset_name='visual_dataset1',
                      dataset_files=['test_data/sample_dataset/sample001.csv',
                                     'test_data/sample_dataset/sample002.txt'],
                      meta_data={
                          'description': 'visual data test',
                          'data_type': 'qa data',
                          'author': 'test author',
                          'author_email': 'test@test.email'})
