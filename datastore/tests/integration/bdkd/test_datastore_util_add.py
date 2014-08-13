import unittest
import bdkd.datastore
import bdkd.datastore_util.add as add_utils
import glob, os, shutil

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures')

class DatastoreUtilsAddTest(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.repository = bdkd.datastore.repository("bdkd-datastore-test")
        self.assertTrue(self.repository)
        self.assertTrue(self.repository.get_bucket())


    def setUp(self):
        # Start with the test bucket empty
        for key in self.repository.get_bucket().list():
            key.delete()
        self._clear_local()
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz') 


    def test_add_resource(self):
        """
        Simulate adding a Resource from the command-line, with only a basic set 
        of options (same as `datastore-add`).
        """
        args_in = [ 'bdkd-datastore-test', 'my_resource', 
                self.filepath 
                ]
        add_utils.add_util(args_in)
        self._check_bucket_count('', 2)


    def test_add_bdkd_resource(self):
        """
        Simulate adding a Resource from the command-line, including all BDKD 
        options (same as `datastore-add-bdkd`).
        """
        args_in = [ 'bdkd-datastore-test', 'my_resource', 
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author_email', 'fred@here', 
                '--tags', '["foo", "bar"]',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer_email', 'joe@here',
                self.filepath 
                ]
        add_utils.add_bdkd_util(args_in)
        self._check_bucket_count('', 2)


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

