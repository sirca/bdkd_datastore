# Copyright 2015 Nicta
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding=utf-8
import unittest
import argparse
import os
# Load a custom configuration for unit testing
os.environ['BDKD_DATASTORE_CONFIG'] = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'conf', 'test.conf')
from bdkd.datastore.util import ds_util


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

