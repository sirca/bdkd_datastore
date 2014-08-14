import unittest

import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', 'conf', 'test.conf')
import bdkd.datastore
import bdkd.datastore.util.add as add_utils
import sys

FIXTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures')


class AddUtilitiesTest(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz') 


    def test_add_minimal_arguments(self):
        parser = add_utils.add_parser()
        args_in = [ 'test-repository', 'my_resource', 
                self.filepath ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.repository.name, 'test-repository')
        self.assertEquals(args.resource_name, 'my_resource')
        self.assertEquals(args.force, False)  # See corresponding below
        self.assertEquals(args.filenames[0], self.filepath)


    def test_add_bad_path(self):
        parser = add_utils.add_parser()
        args_in = [ 'test-repository', 'my_resource',
                'some/nonexistent/file' ]
        self.assertRaises(ValueError, parser.parse_args, args_in)


    def test_add_all_arguments(self):
        parser = add_utils.add_parser()
        args_in = [ 'test-repository', 'my_resource', 
                '--metadata', '{"foo": "bar"}',
                '--force',
                self.filepath ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.metadata, dict(foo='bar'))
        self.assertEquals(args.force, True)


    def test_add_bdkd_mandatory_arguments(self):
        parser = add_utils.add_bdkd_parser()
        args_in = [ 'test-repository', 'my_resource', 
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author_email', 'fred@here', 
                self.filepath ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.description, 'Description of resource')
        self.assertEquals(args.author, 'fred')
        self.assertEquals(args.author_email, 'fred@here')


    def test_add_bdkd_all_arguments(self):
        parser = add_utils.add_bdkd_parser()
        args_in = [ 'test-repository', 'my_resource', 
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author_email', 'fred@here', 
                '--tags', '["foo", "bar"]',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer_email', 'joe@here',
                self.filepath 
                ]
        args = parser.parse_args(args_in)
        self.assertEquals(args.tags, ['foo', 'bar'])
        self.assertEquals(args.version, '1.0')
        self.assertEquals(args.maintainer_email, 'joe@here')


    def test_create_parsed_resource(self):
        args_in = [ 'test-repository', 'my_resource', 
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author_email', 'fred@here', 
                '--data_type', 'feature collection',
                '--tags', '["foo", "bar"]',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer_email', 'joe@here',
                '--custom_fields', '{"continent":"asia", "dataset_type":"features"}',
                self.filepath
                ]
        expected_metadata = dict(
                description='Description of resource',
                author='fred',
                author_email='fred@here',
                data_type='feature collection',
                tags=['foo', 'bar'],
                version='1.0',
                maintainer='Joe',
                maintainer_email='joe@here',
                custom_fields= dict(continent='asia', dataset_type='features'),
                )
        resource_args = add_utils.add_bdkd_parser().parse_args(args_in)
        resource = add_utils.create_parsed_resource(
                resource_args,
                add_utils._bdkd_metadata_parser(),
                args_in
                )
        self.assertEquals(resource.metadata, expected_metadata)
        self.assertEquals(resource.files[0].path, self.filepath)


        
