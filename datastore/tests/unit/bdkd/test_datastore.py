import unittest
import os, shutil

# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(os.path.dirname(__file__), '..', 'conf', 'test.conf')
import bdkd.datastore

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures')

class ConfigurationTest(unittest.TestCase):
    def test_config_settings(self):
        settings = bdkd.datastore.settings()
        self.assertTrue(isinstance(settings, dict))
        self.assertTrue(settings['cache_root'] == '/var/tmp/bdkd/cache')
        self.assertTrue(settings['working_root'] == '/var/tmp/bdkd/working')

    def test_config_hosts(self):
        hosts = bdkd.datastore.hosts()
        self.assertTrue(isinstance(hosts, dict))
        self.assertTrue('test-host' in hosts)
        
    def test_config_repositories(self):
        self.assertTrue(isinstance(bdkd.datastore.repositories(), dict))

    def test_config_repository(self):
        self.assertTrue(bdkd.datastore.repository('test-repository'))
        self.assertFalse(bdkd.datastore.repository('does-not-exist'))


class HostTest(unittest.TestCase):

    def test_configured_host(self):
        hosts = bdkd.datastore.hosts()
        self.assertTrue(isinstance(hosts['test-host'], bdkd.datastore.Host))

    def test_host_init(self):
        host = bdkd.datastore.Host('access-key', 'secret-key', host='hostname', port=80, secure=True, calling_format=None)
        self.assertTrue(host)
        self.assertTrue(host.connection)
        self.assertTrue(host.netloc)


class RepositoryTest(unittest.TestCase):

    @classmethod
    def _clear_local(cls, repository):
        for tmp_path in [ repository.local_cache, repository.working ]:
            if tmp_path and tmp_path.startswith('/var/tmp'):
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)

    @classmethod
    def fixture(cls):
        return bdkd.datastore.repository('test-repository')

    def setUp(self):
        self.repository = bdkd.datastore.repository('test-repository')
        self.resource = ResourceTest.fixture()
        self.resource_name = self.resource.name
        RepositoryTest._clear_local(self.repository)

    def test_configured_repository(self):
        repositories = bdkd.datastore.repositories()
        self.assertTrue(isinstance(repositories['test-repository'], bdkd.datastore.Repository))

    def test_repository_init_defaults(self):
        repository = bdkd.datastore.Repository(None, 'defaults')
        self.assertEquals(repository.host, None)
        self.assertEquals(repository.name, 'defaults')
        self.assertEquals(repository.local_cache, 
                os.path.join(bdkd.datastore.settings()['cache_root'], 
                    str(os.getuid()), 
                    repository.name))
        self.assertEquals(repository.working, 
                os.path.join(bdkd.datastore.settings()['working_root'], 
                    str(os.getuid()), 
                    str(os.getpid()), 
                    repository.name))
        self.assertEquals(repository.bucket, None)

    def test_list(self):
        self.assertEquals(len(self.repository.list()), 0)

    def test_get(self):
        self.assertEquals(self.repository.get(self.resource_name), None)
        self.repository.save(self.resource)
        self.assertTrue(self.repository.get(self.resource_name))

    def test_save(self):
        self.assertEquals(self.repository.get(self.resource_name), None)
        self.repository.save(self.resource)
        self.assertEquals(self.resource.repository, self.repository)
        self.assertFalse(self.resource.is_edit)

    def test_edit_resource(self):
        # This is the default starting state of a Resource (i.e. unsaved)
        self.assertTrue(self.resource.is_edit)
        self.repository.save(self.resource)
        # After saving the resource should no longer be in edit mode
        self.assertFalse(self.resource.is_edit)
        self.assertTrue(self.resource.path.startswith(self.repository.local_cache))
        self.assertFalse(os.access(self.resource.path, os.W_OK))
        # Change to edit; path should be changed to repository's working
        self.repository.edit_resource(self.resource)
        self.assertTrue(self.resource.is_edit)
        self.assertTrue(self.resource.path.startswith(self.repository.working))
        self.assertTrue(os.access(self.resource.path, os.W_OK))

    def test_refresh_resource(self):
        self.repository.save(self.resource)
        self.repository.refresh_resource(self.resource)
        self.assertTrue(self.resource)

    def test_delete_resource(self):
        self.assertEquals(self.repository.get(self.resource_name), None)
        self.repository.save(self.resource)
        self.assertEquals(self.resource.repository, self.repository)
        self.repository.delete(self.resource)
        self.assertFalse(self.resource.repository)


class ResourceTest(unittest.TestCase):

    def setUp(self):
        self.repository = RepositoryTest.fixture()
        self.resource = ResourceTest.fixture()

    @classmethod
    def fixture(cls):
        return bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz'))

    def test_resource_init(self):
        resource = bdkd.datastore.Resource('test-resource', [])
        self.assertEquals(resource.name, 'test-resource')
        self.assertEquals(len(resource.files), 0)

    def test_resource_new(self):
        self.assertTrue(self.resource)

    def test_resource_load(self):
        resource = bdkd.datastore.Resource.load(os.path.join(FIXTURES, 'resource.json'))
        self.assertTrue(resource)

    def test_reload(self):
        self.resource.reload(os.path.join(FIXTURES, 'resource.json'))
        self.assertTrue(self.resource)

    def test_write(self):
        out_filename = os.path.join(self.repository.working, 'test-resource.json')
        fixture_filename = os.path.join(FIXTURES, 'resource.json')
        self.resource.write(out_filename)
        self.assertEquals(bdkd.datastore.checksum(out_filename), 
                bdkd.datastore.checksum(fixture_filename))

    def test_local_paths(self):
        local_paths = self.resource.local_paths()
        self.assertEquals(len(local_paths), 1)

    def test_files_matching(self):
        matches = self.resource.files_matching('.*Seton.*\.gpmlz$')
        self.assertTrue(len(matches))
        matches = self.resource.files_matching('foo')
        self.assertFalse(len(matches))

    def test_file_ending(self):
        self.assertTrue(self.resource.file_ending('.gpmlz'))
        self.assertFalse(self.resource.file_ending('foo'))


class ResourceFileTest(unittest.TestCase):

    def setUp(self):
        self.repository = RepositoryTest.fixture()
        self.resource = ResourceTest.fixture()
        self.resource_file = self.resource.files[0]
        self.url = 'http://www.gps.caltech.edu/~gurnis/GPlates/Caltech_Global_20101129.tar.gz'
        self.remote_resource = bdkd.datastore.Resource.new('Caltech/Continuously Closing Plate Polygons',
                self.url)

    def test_init(self):
        resource_file = bdkd.datastore.ResourceFile(None, self.resource)
        self.assertTrue(resource_file)

    def test_local_path(self):
        self.assertEquals(self.resource_file.local_path(),
                os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz'))

    def test_location(self):
        self.assertEquals(self.resource_file.location(),
                self.resource_file.metadata['location'])

    def test_remote(self):
        self.assertEquals(self.remote_resource.files[0].remote(), self.url)
        self.assertFalse(self.remote_resource.files[0].location())

    def test_location_or_remote(self):
        self.assertTrue(self.resource.files[0].location_or_remote())
        self.assertTrue(self.remote_resource.files[0].location_or_remote())
