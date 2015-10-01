#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
        name='datastorewrapper',
        version='0.1.7',
        description='Store and retrieve sets of files from an object store',
        author='Sirca Ltd',
        author_email='balram.ramanathan@sirca.org.au',
        url='http://github.com/sirca/bdkd',
        package_dir={'': 'lib'},
        packages=[''],
        install_requires=['boto', 'PyYAML', 'bdkd-datastore', 'sphinx']
        )
