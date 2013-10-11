import unittest
import os, shutil

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
                os.path.join(bdkd.datastore.settings()['cache_root'], repository.name))
        self.assertEquals(repository.working, 
                os.path.join(bdkd.datastore.settings()['working_root'], repository.name))
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

    def test_resource_write(self):
        out_filename = os.path.join(self.repository.working, 'test-resource.json')
        fixture_filename = os.path.join(FIXTURES, 'resource.json')
        self.resource.write(out_filename)
        self.assertEquals(bdkd.datastore.checksum(out_filename), bdkd.datastore.checksum(fixture_filename))

class ResourceFileTest(unittest.TestCase):
    pass

