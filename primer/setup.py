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
      long_description = open('README.rst').read(),
      author='Daniel Lau',
      author_email='daniel.lau@sirca.org.au',
      url='http://github.com/sirca/bdkd',
      entry_points = {
          'console_scripts' : [
              'portal_primer = primer.primer:main',
          ],
      },
      packages=['primer'],
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
          "pytz",
      ])
