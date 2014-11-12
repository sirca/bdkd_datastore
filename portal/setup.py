#!/usr/bin/env python

import os
from setuptools import setup, find_packages
import glob

# Make sure we are in the directory where setup.py is.
root_dir = os.path.dirname(__file__)
if root_dir != "":
    os.chdir(root_dir)

setup(name='bdkd-portal',
      version='0.0.6',
      description='BDKD Portal Utilities ',
      long_description = open('README.rst').read(),
      author='Daniel Lau',
      author_email='daniel.lau@sirca.org.au',
      url='http://github.com/sirca/bdkd',
      entry_points = {
          'console_scripts' : [
              'portal-data-builder = bdkdportal.databuild:main',
              ]
          },
      package_dir={'':'src'},
      packages=find_packages('src'),
      scripts=[
          'scripts/purge_portal_dataset',
          ],
      install_requires=[
          "ckan",
          "ckanapi",
          "PyYAML",
          "argparse",
          "bdkd-datastore",
          "python-dateutil",
          "python-daemon",
          "formencode", # this is actually needed by ckanapi 
          "filelock",
          "Jinja2"
      ])
