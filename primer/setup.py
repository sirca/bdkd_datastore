#!/usr/bin/env python

import os
from setuptools import setup, find_packages
import glob

# Make sure we are in the directory where setup.py is.
root_dir = os.path.dirname(__file__)
if root_dir != "":
    os.chdir(root_dir)

setup(name='bdkd-portal-primer',
      version='0.1',
      description='BDKD Data Portal Primer',
      long_description = open('README.md').read(),
      install_requires=['boto', 'PyYAML', 'ckanapi', 'argparse', 'bdkd-datastore'],
      author='Daniel Lau',
      author_email='daniel.lau@sirca.org.au',
      url='http://github.com/sirca/bdkd',
      entry_points = {
          'console_scripts' : [
              'portal_primer = portal_primer:main',
          ],
      },
      # package_dir={'': 'primer'},
      packages=find_packages(exclude='tests'),
      scripts=[
          'bin/purge_dataset.sh',
          ],
      )
