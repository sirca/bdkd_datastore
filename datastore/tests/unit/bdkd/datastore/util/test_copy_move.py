# coding=utf-8
import unittest
import argparse
import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'conf', 'test.conf')
import bdkd.datastore.util.ds_util as ds_util


FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', '..', 'fixtures')


class CopyMoveUtilitiesTest(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        self.parser = argparse.ArgumentParser()
        subparser = self.parser.add_subparsers(dest='subcmd')
        ds_util._create_subparsers(subparser)


    def test_copy_same_repository_arguments(self):
        args_in = [ 'copy', 'test-repository', 'from_resource', 'to_resource' ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository, None)
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_copy_across_repositories_arguments(self):
        args_in = [ 'copy', 'test-repository', 'from_resource', 'test-repository',
                'to_resource' ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository.name, 'test-repository')
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_move_same_repository_arguments(self):
        args_in = [ 'move', 'test-repository', 'from_resource', 'to_resource' ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository, None)
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_move_across_repositories_arguments(self):
        args_in = [ 'move', 'test-repository', 'from_resource', 'test-repository',
                'to_resource' ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository.name, 'test-repository')
        self.assertEquals(args.to_resource_name, 'to_resource')

