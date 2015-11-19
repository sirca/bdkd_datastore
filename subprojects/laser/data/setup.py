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

from setuptools import setup
import os

package_name = 'bdkd-laser-data'
webdir = 'wsgi'
datafiles = [(os.path.join(package_name, root), [os.path.join(root, f) for f in files])
            for root, dirs, files in os.walk(webdir)]

setup(                         
        name=package_name,
        version='0.1.0',
        description='Access dataset data',
        author='Sirca Ltd',
        author_email='david.nelson@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},        
        packages=['bdkd.laser', 'bdkd.laser.util'],
        data_files = datafiles,
        scripts=[
                'bin/pack_maps.py',            
                'bin/pack_raw.py',            
                ],
        entry_points = {
            'console_scripts': [
                'datastore-add-laser = bdkd.laser.util.add:add_laser_util',
                ],
            },
        install_requires=['boto', 'PyYAML', 'bdkd-datastore', 'h5py']
        )
