# coding=utf-8
import codecs
import unittest
from mock import MagicMock
import os, shutil, re
import glob

# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(os.path.dirname(__file__), 
    '..', '..', 'conf', 'test.conf')
import bdkd.datastore

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', 'fixtures')
TEST_PATH='/var/tmp/test'


class UtilitiesTest(unittest.TestCase):

    def test_common_directory_single(self):
        self.assertEquals(bdkd.datastore.common_directory(['a/b']),
                'a/b')

    def test_common_directory_common(self):
        self.assertEquals(bdkd.datastore.common_directory(['a/b', 'a/c']),
                'a')

    def test_common_directory_different(self):
        self.assertEquals(bdkd.datastore.common_directory(['a/b', 'c/d']),
                '')

    def test_common_directory_blanks(self):
        self.assertEquals(bdkd.datastore.common_directory(['', '']),
                '')


class ConfigurationTest(unittest.TestCase):
    def test_config_settings(self):
        settings = bdkd.datastore.settings()
        self.assertTrue(isinstance(settings, dict))
        self.assertTrue(settings['cache_root'] == 
                os.path.join(TEST_PATH, 'bdkd/cache'))

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
        for tmp_path in [ repository.local_cache ]:
            if tmp_path and tmp_path.startswith(TEST_PATH):
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
        self.assertEquals(repository.bucket, None)

    def test_list(self):
        self.assertEquals(len(self.repository.list()), 0)
        self.repository.save(self.resource)
        self.assertEquals(len(self.repository.list()), 1)

    def test_get(self):
        self.assertEquals(self.repository.get(self.resource_name), None)
        self.repository.save(self.resource)
        self.assertTrue(self.repository.get(self.resource_name))

    def test_save(self):
        self.assertEquals(self.repository.get(self.resource_name), None)
        self.repository.save(self.resource)
        self.assertEquals(self.resource.repository, self.repository)

    def test_save_from_resource_no_repo(self):
        self.resource.repository = None;
        # Calling save() on a resource without a repository should raise a 
        # ValueError
        self.assertRaises(ValueError, self.resource.save)

    def test_save_from_resource(self):
        self.resource.repository = MagicMock();
        # Calling save() on a resource should call its repository's save() 
        # method with overwrite=True
        self.resource.save()
        self.resource.repository.save.assert_called_with(self.resource, 
                overwrite=True)

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
        self.bundled_resource = ResourceTest.bundled_fixture()

    @classmethod
    def fixture(cls):
        return bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz'),
                publish=False,
                metadata=dict(citation=u'M. Seton, R.D. Müller, S. Zahirovic, C. Gaina, T.H. Torsvik, G. Shephard, A. Talsma, M. Gurnis, M. Turner, S. Maus, M. Chandler, Global continental and ocean basin reconstructions since 200 Ma, Earth-Science Reviews, Volume 113, Issues 3-4, July 2012, Pages 212-270, ISSN 0012-8252, 10.1016/j.earscirev.2012.03.002. (http://www.sciencedirect.com/science/article/pii/S0012825212000311)'))

    @classmethod
    def bundled_fixture(self):
        shapefile_dir = os.path.join(FIXTURES, 'FeatureCollections', 
                'Coastlines', 'Shapefile')
        shapefile_parts = glob.glob(os.path.join(shapefile_dir, '*.*'))
        resource = bdkd.datastore.Resource.new('bundled resource', 
                shapefile_parts,
                publish=False,
                do_bundle=True)
        return resource

    @classmethod
    def _resource_sans_modified(cls, filename):
        """
        The "last-modified" date of a Resource is variable: it depends on when 
        the test is run.  For the purposes of comparing actual versus expected, 
        the content of this field needs to be ignored.
        """
        with codecs.open(filename, encoding='utf-8') as fh:
            content = fh.read()
        return re.sub(r'"last-modified": "[^"]*"', 
            r'"last-modified": ""', content.strip())
        
    def test_resource_init(self):
        resource = bdkd.datastore.Resource('test-resource', [])
        self.assertEquals(resource.name, 'test-resource')
        self.assertEquals(len(resource.files), 0)

    def test_resource_new(self):
        self.assertTrue(self.resource)

    def test_resource_metadata(self):
        # Bad: metadata is not a dictionary
        with self.assertRaises(ValueError):
            resource = bdkd.datastore.Resource.new("a", [],
                    ['bad', 'metadata'], publish=False)
        # Good
        resource = bdkd.datastore.Resource.new("a", [], dict(metadata='ok'), publish=False)
        self.assertTrue(resource)

    def test_resource_validate_name(self):
        self.assertFalse(bdkd.datastore.Resource.validate_name(None))
        self.assertFalse(bdkd.datastore.Resource.validate_name(42))
        self.assertFalse(bdkd.datastore.Resource.validate_name(''))
        self.assertFalse(bdkd.datastore.Resource.validate_name('/a'))
        self.assertFalse(bdkd.datastore.Resource.validate_name('a/'))
        self.assertTrue(bdkd.datastore.Resource.validate_name('a'))
        self.assertTrue(bdkd.datastore.Resource.validate_name('a/b'))

    def test_resource_new_invalid_name(self):
        with self.assertRaises(ValueError):
            resource = bdkd.datastore.Resource.new('/a', [], publish=False)

    def test_resource_validate_metadata(self):
        with self.assertRaises(bdkd.datastore.MetadataException):
            resource = bdkd.datastore.Resource.new('TestResource', [], publish=True)

    def test_resource_load(self):
        resource = bdkd.datastore.Resource.load(os.path.join(FIXTURES, 'resource.json'))
        self.assertTrue(resource)

    def test_reload(self):
        self.resource.reload(os.path.join(FIXTURES, 'resource.json'))
        self.assertTrue(self.resource)

    def test_write(self):
        out_filename = os.path.join(self.repository.local_cache, 'test-resource.json')
        fixture_filename = os.path.join(FIXTURES, 'resource.json')
        self.resource.write(out_filename)
        self.assertEquals(out_filename, fixture_filename)
        self.assertEquals(
                type(self)._resource_sans_modified(out_filename), 
                type(self)._resource_sans_modified(fixture_filename))

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

    def test_bundled_local_paths(self):
        local_paths = self.bundled_resource.local_paths()
        self.assertEquals(5, len(local_paths))


class ResourceFileTest(unittest.TestCase):

    def setUp(self):
        self.repository = RepositoryTest.fixture()
        self.resource = ResourceTest.fixture()
        self.bundled_resource = ResourceTest.bundled_fixture()
        self.resource_file = self.resource.files[0]
        self.url = 'http://www.gps.caltech.edu/~gurnis/GPlates/Caltech_Global_20101129.tar.gz'
        self.remote_resource = bdkd.datastore.Resource.new('Caltech/Continuously Closing Plate Polygons',
                self.url, publish=False)

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

    def test_is_bundled(self):
        self.assertFalse(self.resource.files[0].is_bundled())
        self.assertTrue(self.bundled_resource.files[0].is_bundled())


if __name__ == '__main__':
    unittest.main()
