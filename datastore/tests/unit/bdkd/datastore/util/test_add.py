# coding=utf-8
import unittest
from mock import patch, ANY
import argparse

import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'conf', 'test.conf')
from bdkd.datastore.util import ds_util

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', '..', 'fixtures')


class AddUtilitiesTest(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        self.parser = argparse.ArgumentParser()
        subparser = self.parser.add_subparsers(dest='subcmd')
        ds_util._create_subparsers(subparser)


    def test_add_minimal_arguments(self):
        args_in = [ 'add', 'test-repository', 'my_resource',
                self.filepath ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.repository.name, 'test-repository')
        self.assertEquals(args.resource_name, 'my_resource')
        self.assertEquals(args.force, False)  # See corresponding below
        self.assertEquals(args.filenames[0], self.filepath)


    def test_add_bad_path(self):
        args_in = [ 'add', 'test-repository', 'my_resource',
                'some/nonexistent/file' ]
        self.assertRaises(ValueError, self.parser.parse_args, args_in)


    def test_add_all_arguments(self):
        args_in = [ 'add', 'test-repository', 'my_resource',
                '--metadata', '{"foo": "bar"}',
                '--force',
                '--bundle',
                self.filepath ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.metadata, dict(foo='bar'))
        self.assertEquals(args.force, True)
        self.assertEquals(args.bundle, True)


    def test_add_bdkd_mandatory_arguments(self):
        args_in = [ 'add-bdkd', 'test-repository', 'my_resource',
                '--description', 'Description of resource',
                '--author', u'Dietmar Müller', 
                '--author-email', 'fred@here', 
                self.filepath ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.description, 'Description of resource')
        self.assertEquals(args.author, u'Dietmar Müller')
        self.assertEquals(args.author_email, 'fred@here')


    def test_add_bdkd_all_arguments(self):
        args_in = [ 'add-bdkd', 'test-repository', 'my_resource',
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author-email', 'fred@here', 
                '--tags', '["foo", "bar"]',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer-email', 'joe@here',
                self.filepath 
                ]
        args = self.parser.parse_args(args_in)
        self.assertEquals(args.tags, ['foo', 'bar'])
        self.assertEquals(args.version, '1.0')
        self.assertEquals(args.maintainer_email, 'joe@here')


    def test_create_parsed_resource(self):
        args_in = [ 'add-bdkd', 'test-repository', 'my_resource',
                '--description', 'Description of resource',
                '--author', 'fred', 
                '--author-email', 'fred@here', 
                '--data-type', 'feature collection',
                '--tags', '["foo", "bar"]',
                '--version', '1.0',
                '--maintainer', 'Joe',
                '--maintainer-email', 'joe@here',
                '--custom-fields', '{"continent":"asia", "dataset_type":"features"}',
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
        resource_args = self.parser.parse_args(args_in)
        resource = ds_util.create_parsed_resource(
                resource_args,
                ds_util._bdkd_metadata_parser(),
                args_in
                )
        self.assertEquals(resource.metadata, expected_metadata)
        self.assertEquals(resource.files[0].path, self.filepath)

        
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_create_parsed_resource_just_files(self,
            mock_os_path_isdir,
            mock_os_path_exists):
        resource_args = argparse.Namespace()
        setattr(resource_args, 'bundle', False)
        setattr(resource_args, 'metadata', {})
        setattr(resource_args, 'filenames', ['file1','file2'])
        setattr(resource_args, 'resource_name', 'dummy-resource')

        mock_os_path_exists.return_value = True
        mock_os_path_isdir.return_value = False
        with patch('bdkd.datastore.Resource.new') as mock_Resource_new:
            resource = ds_util.create_parsed_resource(resource_args = resource_args)
        mock_Resource_new.assert_called_once_with('dummy-resource', 
                files_data=['file1','file2'],
                do_bundle=False,
                metadata={})


    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_create_parsed_resource_files_and_remote(self,
            mock_os_path_isdir,
            mock_os_path_exists):
        resource_args = argparse.Namespace()
        setattr(resource_args, 'bundle', False)
        setattr(resource_args, 'metadata', {})
        setattr(resource_args, 'filenames', ['file1','http://test.dummy/file2','file3'])
        setattr(resource_args, 'resource_name', 'dummy-resource')

        mock_os_path_exists.side_effect = lambda f: f[0:4] == 'file'
        mock_os_path_isdir.return_value = False
        with patch('bdkd.datastore.Resource.new') as mock_Resource_new:
            resource = ds_util.create_parsed_resource(resource_args = resource_args)
        mock_Resource_new.assert_called_once_with(
            'dummy-resource',
            files_data=['file1','http://test.dummy/file2', 'file3'],
            metadata={},
            do_bundle=False)


    @patch('bdkd.datastore.Resource.new')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.walk')
    def test_create_parsed_resource_files_and_dirs(self,
            mock_walk,
            mock_os_path_isdir,
            mock_os_path_exists,
            mock_Resource_new):
        resource_args = argparse.Namespace()
        setattr(resource_args, 'bundle', False)
        setattr(resource_args, 'metadata', {})
        setattr(resource_args, 'filenames', ['file1','dir1'])
        setattr(resource_args, 'resource_name', 'dummy-resource')

        mock_os_path_exists.return_value = True
        mock_os_path_isdir.side_effect = lambda f: 'file' not in f
        mock_walk.return_value = [
            ('dir1', ['emptydir','subdir1','subdir2' ], []),
            ('dir1/emptydir', [], []),
            ('dir1/subdir1', [], ['file1']),
            ('dir1/subdir2', [], ['file2'])
            ]
        # Simulates the following file structure:
        # ./file1
        # ./dir1/
        # ./dir1/emptydir/
        # ./dir1/subdir1/
        # ./dir1/subdir1/file1
        # ./dir1/subdir2/
        # ./dir1/subdir2/file2
        # When adding with the parameter 'file1 dir1', it will create a resource
        # containing the file 'file1' and all files inside directory 'dir1'

        resource = ds_util.create_parsed_resource(resource_args = resource_args)
        mock_Resource_new.assert_called_once_with(
            'dummy-resource', 
            do_bundle=False,
            files_data=['file1','dir1/subdir1/file1','dir1/subdir2/file2'],
            metadata={})
