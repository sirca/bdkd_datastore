# coding=utf-8
import unittest
import bdkd.datastore
import glob, os, shutil
import boto
import time

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', 'fixtures')

class RepositoryTest(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.repository = bdkd.datastore.repository("bdkd-datastore-test")
        self.assertTrue(self.repository)
        self.assertTrue(self.repository.get_bucket())
        self.resources = dict(
                single=self._create_single_file_fixture(),
                multi=self._create_multi_file_fixture(),
                shapefile=self._create_shapefile_fixture(),
                bundled=self._create_bundled_fixture(),
                )

    def setUp(self):
        # Start with the test bucket empty
        for key in self.repository.get_bucket().list():
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

    def test_name_collisions(self):
        resource = self.resources.get('single')
        other_resource = self.resources.get('multi')

        resource.name = 'a/b'
        # Save the resource to the repository
        self.repository.save(resource)

        # Conflicts with the shorter name 'a/b'
        other_resource.name = 'a/b/c'
        self.assertRaises(ValueError, self.repository.save, other_resource)

        # Conflicts with the longer name 'a/b'
        other_resource.name = 'a'
        self.assertRaises(ValueError, self.repository.save, other_resource)

    def test_multi_file_resource(self):
        resource = self.resources.get('multi')
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
        self._check_bucket_count('', 3)
        # Check that the cache has two files in it
        self._check_file_count(self.repository.local_cache, 3)

    def test_shapefile_resource(self):
        resource = self.resources.get('shapefile')
        self.assertTrue(resource)
        self.repository.save(resource)
        # The shapefile consists of five files (plus one resource)
        self._check_bucket_count('', 6)
        self._check_file_count(self.repository.local_cache, 6)

    def test_unified_resource(self):
        """ Unified: all resource parts fetched together. """
        resource = self.resources.get('shapefile')
        self.assertTrue(resource)
        self.repository.save(resource)
        self._clear_local()
        shp = resource.file_ending('.shp')
        shp.local_path()
        # The shapefile consists of five files (plus one resource)
        self._check_file_count(self.repository.local_cache, 6)

    def test_bundled_resource(self):
        resource = self.resources.get('bundled')
        self.assertTrue(resource)
        self.repository.save(resource)
        self._check_bucket_count('', 2)
        self._check_file_count(self.repository.local_cache, 2)
        self.assertEquals(5, len(resource.local_paths()))

    def test_remote_resource(self):
        resource = bdkd.datastore.Resource.new('Caltech/Continuously Closing Plate Polygons',
                'http://www.gps.caltech.edu/~gurnis/GPlates/Caltech_Global_20101129.tar.gz',
                publish=False)
        self.assertTrue(resource.files[0].meta('etag'))
        self.repository.save(resource)
        paths = resource.local_paths()
        self.assertEquals(len(paths), 1)
        self.assertEquals(bdkd.datastore.checksum(paths[0]), '412f9bfd1fc6c6ba1b5fc8bc450fef61')

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

    def test_overwrite_resource_blocked(self):
        # You shouldn't be able to save over an existing resource
        # (overwrite=True is required)
        resource = self.resources.get('single')
        self.repository.save(resource)
        self.assertRaises(ValueError, self.repository.save, resource)

    def test_overwrite_resource(self):
        resource = self.resources.get('single')
        self.repository.save(resource)
        self.repository.save(resource, overwrite=True)

    def test_copy_resource(self):
        from_resource = self.resources.get('shapefile')
        self.repository.save(from_resource)
        self._check_bucket_count('', 6)
        self.repository.copy(from_resource, 'copied/shapefile')
        self._check_bucket_count('', 12)

    def test_copy_bundled_resource(self):
        from_resource = self.resources.get('bundled')
        self.repository.save(from_resource)
        self._check_bucket_count('', 2)
        self.repository.copy(from_resource, 'copied/bundled')
        self._check_bucket_count('', 4)
        copied_resource = self.repository.get('copied/bundled')
        self.assertEquals(len(copied_resource.local_paths()), 5)

    def test_copy_resource_with_metadata(self):
        metadata = {'author': 'fred', 'author-email': 'fred@localhost'}
        from_resource = self.resources.get('shapefile')
        from_resource.metadata = metadata
        self.repository.save(from_resource)
        self.repository.copy(from_resource, 'copied/shapefile')
        copied = self.repository.get('copied/shapefile')
        self.assertTrue(
                len(set(metadata.items()) ^ set(copied.metadata.items())) == 0)

    def test_copy_resource_with_files(self):
        from_resource = self.resources.get('shapefile')
        self.repository.save(from_resource)
        self.repository.copy(from_resource, 'copied/shapefile')
        copied = self.repository.get('copied/shapefile')
        self.assertEquals(len(from_resource.files), len(copied.files))

    def test_copy_resource_conflict(self):
        from_resource = self.resources.get('shapefile')
        self.repository.save(from_resource)
        # This name conflicts with an existing pseudopath
        self.assertRaises(ValueError, self.repository.copy, from_resource,
                'FeatureCollections/Coastlines')

    def test_copy_resource_clash(self):
        from_resource = self.resources.get('shapefile')
        self.repository.save(from_resource)
        # Can't copy over an existing resource
        self.assertRaises(ValueError, self.repository.copy, from_resource,
                'FeatureCollections/Coastlines/Shapefile')

    def test_move_resource(self):
        from_resource = self.resources.get('shapefile')
        self.repository.save(from_resource)
        self._check_bucket_count('', 6)
        self.repository.move(from_resource, 'copied/shapefile')
        self._check_bucket_count('', 6)
        moved_resource = self.repository.get('copied/shapefile')
        self.assertTrue(moved_resource)

    def test_move_bundled_resource(self):
        from_resource = self.resources.get('bundled')
        self.repository.save(from_resource)
        self._check_bucket_count('', 2)
        self.repository.move(from_resource, 'moved/bundled')
        self._check_bucket_count('', 2)
        moved_resource = self.repository.get('moved/bundled')
        self.assertTrue(moved_resource)
        self.assertEquals(len(moved_resource.local_paths()), 5)

    def test_resource_last_modified(self):
        # Force resource into remote storage.
        resource = self.resources.get('single')
        self.repository.save(resource)
        datetime1 = self.repository.get_resource_last_modified(resource.name)
        # Force an update to the resource 1 second later.
        time.sleep(1) 
        self.repository.save(resource, overwrite=True)
        datetime2 = self.repository.get_resource_last_modified(resource.name)
        # The sequence of events should produce a sequential set of times.
        self.assertTrue(datetime1 < datetime2)

    def test_delete_resource(self):
        resource = self.resources.get('single')
        self.repository.save(resource)
        # Before delete: two files
        self._check_bucket_count('', 2)
        self._check_file_count(self.repository.local_cache, 2)

        self.repository.delete(resource)
        # After delete: no files
        self._check_bucket_count('', 0)
        self._check_file_count(self.repository.local_cache, 0)

    def test_delete_bundled_resource(self):
        resource = self.resources.get('bundled')
        self.repository.save(resource)
        # Before delete: two files
        self._check_bucket_count('', 2)
        self._check_file_count(self.repository.local_cache, 2)

        self.repository.delete(resource)
        # After delete: no files
        self._check_bucket_count('', 0)
        self._check_file_count(self.repository.local_cache, 0)

    def _clear_local(self):
        for tmp_path in [ self.repository.local_cache ]:
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
        for key in self.repository.get_bucket().list(pseudopath):
            key_count += 1
        self.assertTrue(key_count == expected)

    def _create_single_file_fixture(self):
        path = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        resource = bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                path, publish=False, metadata=dict(citation=u'M. Seton, R.D. Müller, S. Zahirovic, C. Gaina, T.H. Torsvik, G. Shephard, A. Talsma, M. Gurnis, M. Turner, S. Maus, M. Chandler, Global continental and ocean basin reconstructions since 200 Ma, Earth-Science Reviews, Volume 113, Issues 3-4, July 2012, Pages 212-270, ISSN 0012-8252, 10.1016/j.earscirev.2012.03.002. (http://www.sciencedirect.com/science/article/pii/S0012825212000311)'))
        return resource

    def _create_multi_file_fixture(self):
        return bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                [
                    os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                        'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz'),
                    os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines',
                        'Shapefile', 'Seton_etal_ESR2012_Coastlines_2012.1.shp')
                    ],
                publish=False)

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
                files, metadata=dict(unified=True), publish=False)
        return resource

    def _create_bundled_fixture(self):
        shapefile_dir = os.path.join(FIXTURES, 'FeatureCollections', 
                'Coastlines', 'Shapefile')
        shapefile_parts = glob.glob(os.path.join(shapefile_dir, '*.*'))
        resource = bdkd.datastore.Resource.new('bundled resource', 
                shapefile_parts,
                do_bundle=True, publish=False)
        return resource

    def test_publish_resource(self):
        resource = self.resources.get('single')
        self.assertTrue(resource)

        # Check mandatory fields
        self.repository.save(resource)
        saved_resource = self.repository.get(resource.name)
        self.assertRaises(ValueError, saved_resource.publish)
        self.assertFalse(saved_resource.is_published())

        # Publish
        resource.metadata = {'description':'Resource name', 'author': 'fred', 'author_email': 'fred@localhost'}
        self.repository.save(resource, overwrite=True)
        saved_resource = self.repository.get(resource.name)
        saved_resource.publish()
        self.assertTrue(saved_resource.is_published())
        
        # Unpublish
        saved_resource = self.repository.get(resource.name)
        saved_resource.unpublish()
        self.assertFalse(saved_resource.is_published())

if __name__ == '__main__':
    unittest.main()
