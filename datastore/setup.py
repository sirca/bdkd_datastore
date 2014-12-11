#!/usr/bin/env python

from setuptools import setup, find_packages
import glob

setup(
        name='bdkd-datastore',
        version='0.1.3',
        description='Store and retrieve sets of files from an object store',
        author='Sirca Ltd',
        author_email='david.nelson@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},
        packages=find_packages('lib'),
        scripts=[
                'bin/datastore-delete',
                'bin/datastore-files',
                'bin/datastore-get',
                'bin/datastore-list',
                'bin/datastore-repositories',
                ],
        entry_points = {
            'console_scripts': [
                'datastore-add = bdkd.datastore.util.add:add_util',
                'datastore-add-bdkd = bdkd.datastore.util.add:add_bdkd_util',
                'datastore-copy = bdkd.datastore.util.copy_move:copy_util',
                'datastore-getkey = bdkd.datastore.util.info:getkey_util',
                'datastore-lastmod = bdkd.datastore.util.info:lastmod_util',
                'datastore-move = bdkd.datastore.util.copy_move:move_util',
                'datastore-update-metadata = bdkd.datastore.util.metadata:update_metadata_util',
            ],
        },
        install_requires=['boto', 'PyYAML']
        )
