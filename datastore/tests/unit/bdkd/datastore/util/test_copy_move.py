# coding=utf-8
import unittest

import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'conf', 'test.conf')
import bdkd.datastore
import bdkd.datastore.util.copy_move as copy_move_utils
import sys

FIXTURES = os.path.join(os.path.dirname(__file__), 
    '..', '..', '..', '..', 'fixtures')


class CopyMoveUtilitiesTest(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(FIXTURES, 'FeatureCollections', 'Coastlines', 
                    'Seton_etal_ESR2012_Coastlines_2012.1.gpmlz') 


    def test_copy_same_repository_arguments(self):
        parser = copy_move_utils.copy_parser()
        args_in = [ 'test-repository', 'from_resource', 'to_resource' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository, None)
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_copy_across_repositories_arguments(self):
        parser = copy_move_utils.copy_parser()
        args_in = [ 'test-repository', 'from_resource', 'test-repository', 
                'to_resource' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository.name, 'test-repository')
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_move_same_repository_arguments(self):
        parser = copy_move_utils.move_parser()
        args_in = [ 'test-repository', 'from_resource', 'to_resource' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository, None)
        self.assertEquals(args.to_resource_name, 'to_resource')


    def test_move_across_repositories_arguments(self):
        parser = copy_move_utils.move_parser()
        args_in = [ 'test-repository', 'from_resource', 'test-repository', 
                'to_resource' ]
        args = parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.from_repository.name, 'test-repository')
        self.assertEquals(args.from_resource_name, 'from_resource')
        self.assertEquals(args.to_repository.name, 'test-repository')
        self.assertEquals(args.to_resource_name, 'to_resource')

