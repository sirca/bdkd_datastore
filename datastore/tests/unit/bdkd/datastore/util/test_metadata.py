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

import unittest
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


    def test_metadata_minimal_arguments(self):
        args_in = [ 'update-metadata', 'test-repository', 'my_resource' ]
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.repository.name, 'test-repository')
        self.assertEquals(args.resource_name, 'my_resource')


    def test_metadata_all_arguments(self):
        args_in = [ 'update-metadata', 'test-repository', 'my_resource',
                    '--description', 'something', '--author', 'Fred',
                    '--author-email', 'fred@up.com']
        args = self.parser.parse_args(args_in)
        self.assertTrue(args)
        self.assertEquals(args.description, 'something')
        self.assertEquals(args.author, 'Fred')
        self.assertEquals(args.author_email, 'fred@up.com')
