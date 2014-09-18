#!/usr/bin/env python

from setuptools import setup
import os

package_name = 'bdkd-laser-data'
webdir = 'wsgi'
datafiles = [(os.path.join(package_name, root), [os.path.join(root, f) for f in files])
            for root, dirs, files in os.walk(webdir)]

setup(                         
        name=package_name,
        version='0.0.1',
        description='Access dataset data',
        author='Sirca Ltd',
        author_email='david.nelson@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},        
        packages=['bdkd.laser'],
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
