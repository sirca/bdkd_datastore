#!/usr/bin/env python

from setuptools import setup, find_packages
import glob

setup(
        name='bdkd-datastore',
        version='0.1.6',
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
