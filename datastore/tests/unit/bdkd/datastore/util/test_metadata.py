import unittest

import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'conf', 'test.conf')
import bdkd.datastore
import bdkd.datastore.util.metadata as metadata_utils
import sys

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', '..', 'fixtures')


class AddUtilitiesTest(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz') 


    def test_metadata_minimal_arguments(self):
        parser = metadata_utils.update_metadata_bdkd_parser()
        args_in = [ 'test-repository', 'my_resource' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.repository.name, 'test-repository')
        self.assertEquals(args.resource_name, 'my_resource')


    def test_metadata_all_arguments(self):
        parser = metadata_utils.update_metadata_bdkd_parser()
        args_in = [ 'test-repository', 'my_resource', 
                '--metadata', '{"foo": "bar"}' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.metadata, dict(foo='bar'))
