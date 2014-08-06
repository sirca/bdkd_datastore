#!/usr/bin/env python

from setuptools import setup
import glob

setup(
        name='bdkd-datastore',
        version='0.0.1',
        description='Store and retrieve sets of files from an object store',
        author='Sirca Ltd',
        author_email='david.nelson@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},
        packages=['bdkd'],
        scripts=[
                'bin/datastore-add',
                'bin/datastore-delete',
                'bin/datastore-files',
                'bin/datastore-get',
                'bin/datastore-list',
                'bin/datastore-repositories',
                ],
        entry_points = {
            'console_scripts': [
                'datastore-getkey = bdkd.util:getkey_util',
                'datastore-lastmod = bdkd.util:lastmod_util',
            ],
        },
        install_requires=['boto', 'PyYAML']
        )
