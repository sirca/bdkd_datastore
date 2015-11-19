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

#!/usr/bin/env python

from setuptools import setup, find_packages
import glob

setup(
        name='bdkd-datastore',
        version='0.1.7',
        description='Store and retrieve sets of files from an object store',
        author='Sirca Ltd',
        author_email='balram.ramanathan@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},
        packages=find_packages('lib'),
        entry_points = {
            'console_scripts': [
                'datastore-util = bdkd.datastore.util.ds_util:ds_util',
            ],
        },
        install_requires=['boto', 'PyYAML']
        )
