import unittest
import bdkd.datastore
from bdkd.datastore.util import ds_util
import glob, os, shutil

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', '..', 'fixtures')

class DatastoreUtilsAddTest(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.repository_name = 'bdkd-datastore-test'
        self.repository = bdkd.datastore.repository(self.repository_name)
        self.assertTrue(self.repository)
        self.assertTrue(self.repository.get_bucket())
        self.resource_name = 'FeatureCollections/Coastlines/Seton'
        self.resource = self._create_single_file_fixture()


    def setUp(self):
        # Work with a single resource in the test bucket
        for key in self.repository.get_bucket().list():
            key.delete()
        self._clear_local()
        self.repository.save(self.resource)


    def test_update_metadata(self):
        args_in = [ 'update-metadata', self.repository_name, self.resource_name,
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author-email', 'fred@here',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer-email', 'joe@here',
                ]
        ds_util.ds_util(args_in)
        updated = self.repository.get(self.resource_name)
        self.assertTrue(updated)
        self.assertEquals('Description of resource', 
                updated.meta('description'))
        self.assertEquals('fred',
                updated.meta('author'))
        self.assertEquals('fred@here',
                updated.meta('author_email'))
        self.assertEquals('1.0',
                updated.meta('version'))
        self.assertEquals('Joe',
                updated.meta('maintainer'))
        self.assertEquals('joe@here',
                updated.meta('maintainer_email'))

    def test_change_updated_metadata(self):
        # Set description to something
        args_in = [ 'update-metadata', self.repository_name, self.resource_name,
                '--description', 'Description of resource',
                ]
        ds_util.ds_util(args_in)
        updated = self.repository.get(self.resource_name)
        self.assertEquals('Description of resource', 
                updated.meta('description'))
        # Then check that it is altered subsequently
        args_in = [ 'update-metadata', self.repository_name, self.resource_name,
                '--description', 'Altered description',
                ]
        ds_util.ds_util(args_in)
        updated = self.repository.get(self.resource_name)
        self.assertEquals('Altered description', 
                updated.meta('description'))

    def _create_single_file_fixture(self):
        path = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        resource = bdkd.datastore.Resource.new(self.resource_name,
                path)
        return resource

    def _check_bucket_count(self, pseudopath, expected):
        # Check that S3 repository has two keys in it
        key_count = 0
        for key in self.repository.get_bucket().list(pseudopath):
            key_count += 1
        self.assertTrue(key_count == expected)

        
    def _clear_local(self):
        for tmp_path in [ self.repository.local_cache, self.repository.working ]:
            if tmp_path and tmp_path.startswith('/var/tmp'):
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)

