import unittest
import bdkd.datastore
import glob, os, shutil

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures')

class RepositoryTest(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.repository = bdkd.datastore.repository("bdkd-datastore-test")
        self.assertTrue(self.repository)
        self.assertTrue(self.repository.bucket)
        self.resources = dict(
                single=self._create_single_file_fixture(),
                shapefile=self._create_shapefile_fixture(),
                )

    def setUp(self):
        # Start with the test bucket empty
        for key in self.repository.bucket.list():
            key.delete()
        self._clear_local()

    def test_single_file_resource(self):
        resource = self.resources.get('single')
        self.assertTrue(resource)
        # Save the resource to the repository
        self.repository.save(resource)
        # Check that the repository was set properly
        self.assertTrue(resource.repository == self.repository)
        # Check that the Resource was copied to the local cache
        resource_path = os.path.join(self.repository.local_cache,
                'resources', resource.name)
        self.assertTrue(os.path.exists(resource_path))
        # Check that S3 repository has two keys in it (resource + one file)
        self._check_bucket_count('', 2)
        # Check that the cache has two files in it
        self._check_file_count(self.repository.local_cache, 2)

    def test_shapefile_resource(self):
        resource = self.resources.get('shapefile')
        self.assertTrue(resource)
        self.repository.save(resource)
        # The shapefile consists of five files (plus one resource)
        self._check_bucket_count('', 6)
        self._check_file_count(self.repository.local_cache, 6)

    def test_refresh_cache(self):
        resource = self.resources.get('single')
        self.repository.save(resource)
        # Clear the local cache, refresh the resource and see if the cache is restored
        self._clear_local()
        self._check_file_count(self.repository.local_cache, 0)
        self.repository.refresh_resource(resource)
        self._check_file_count(self.repository.local_cache, 2)

    def test_list_resources(self):
        # Starts with nothing there
        resource_names = self.repository.list()
        self.assertEquals(len(resource_names), 0)
        # One resource
        resource = self.resources.get('single')
        self.repository.save(resource)
        resource_names = self.repository.list()
        self.assertEquals(len(resource_names), 1)
        self.assertEquals(resource_names[0], resource.name)
        # More than one
        shapefile = self.resources.get('shapefile')
        self.repository.save(shapefile)
        resource_names = self.repository.list()
        self.assertEquals(len(resource_names), 2)
        # Listing by pseudopath
        resource_names = self.repository.list(resource.name)
        self.assertEquals(len(resource_names), 1)
        # Listing by nonexistent pseudopath
        resource_names = self.repository.list('foo/bar')
        self.assertEquals(len(resource_names), 0)

    def test_edit_resource(self):
        resource = self.resources.get('single')
        self.repository.save(resource)
        # After saving, the Resource should not be in editing mode.
        self.assertFalse(resource.is_edit)
        # The Resource path should be a file in the cache directory that is not writable.
        self.assertTrue(resource.path.startswith(self.repository.local_cache))
        self.assertFalse(os.access(resource.path, os.W_OK))
        self._check_file_count(self.repository.working, 0)
        # Now set resource to editing mode
        self.repository.edit_resource(resource)
        self.assertTrue(resource.is_edit)
        # There should be a writable file in the repository's working path
        self.assertTrue(resource.path.startswith(self.repository.working))
        self.assertTrue(os.access(resource.path, os.W_OK))
        self._check_file_count(self.repository.working, 2)

    def _clear_local(self):
        for tmp_path in [ self.repository.local_cache, self.repository.working ]:
            if tmp_path and tmp_path.startswith('/var/tmp'):
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)

    def _check_file_count(self, dir_path, expected):
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(dir_path):
            file_count += len(filenames)
        self.assertTrue(file_count == expected)

    def _check_bucket_count(self, pseudopath, expected):
        # Check that S3 repository has two keys in it
        key_count = 0
        for key in self.repository.bucket.list(pseudopath):
            key_count += 1
        self.assertTrue(key_count == expected)

    def _create_single_file_fixture(self):
        path = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        resource = bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                path)
        return resource

    def _create_shapefile_fixture(self):
        shapefile_dir = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 'Shapefile')
        shapefile_parts = glob.glob(os.path.join(shapefile_dir, '*.*'))
        files = []
        for part in shapefile_parts:
            file_meta = dict(path=os.path.expanduser(part))
            if part.endswith('shp'):
                file_meta['type'] = 'ESRI shapefile'
                files.insert(0, file_meta)
            else:
                files.append(file_meta)
        resource = bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Shapefile/Seton',
                files)
        return resource

