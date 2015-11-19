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
"""
Module providing various common components for utilities.
"""

import argparse
import os
import glob
import platform
import urlparse
import bdkd.datastore
import posixpath

class FilesAction(argparse.Action):
    """
    Action to perform for file arguments: check that they are either files or
    remote URIs.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        file_list=[]
        for filename in values:
            if (platform.system().lower() == "windows"):
                if "*" in filename or "?" in filename:
                    for f in glob.glob(filename):
                        file_list.append(f)
                elif os.path.isdir(filename):
                    for root, dir, files in os.walk(filename):
                        for f in files:
                            file_list.append(posixpath.join(root.replace("\\","/"), f))
                else:
                    file_list.append(filename)
            else:
                file_list.append(filename)

        for filename in file_list:
            if not os.path.exists(filename):
                url = urlparse.urlparse(filename)
                if not url.netloc:
                    raise ValueError("The file '{0}' is neither a local filename nor a URL"
                            .format(filename))
        setattr(namespace, self.dest, file_list)

class SingleFileAction(argparse.Action):
    """
    Action to perform for single file argument
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.exists(values):
            raise ValueError("The file '{0}' does not exist".format(values))
        setattr(namespace, self.dest, values)


class RepositoryAction(argparse.Action):
    """
    Action for Repository: get the BDKD datastore repository by name (or raise 
    a ValueError).
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Multiple arguments not allowed")
        super(RepositoryAction, self).__init__(option_strings, dest, **kwargs)


    def __call__(self, parser, namespace, values, option_string=None):
        repository = bdkd.datastore.repository(values)
        if not repository:
            raise ValueError("Repository '{0}' does not exist or is not configured!".format(values))
        setattr(namespace, self.dest, repository)


class OptionalRepositoryAction(argparse.Action):
    """
    Action for Repository: get the BDKD datastore repository by name.  Optional 
    but if specified the repository must exist.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        repository = None
        if values:
            repository = bdkd.datastore.repository(values)
            if not repository:
                raise ValueError("Repository '{0}' does not exist or is not configured!".format(values))
        setattr(namespace, self.dest, repository)


def _repository_parser():
    """
    Parser providing the mandatory option 'repository'.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('repository', action=RepositoryAction,
            help='Name of a defined Repository')
    return parser


def _repository_resource_parser():
    """
    Parser providing the mandatory options 'repository' and 'resource_name'
    """
    parser = argparse.ArgumentParser(add_help=False, parents=[
        _repository_parser(),
        ])
    parser.add_argument('resource_name',
            help='Name of a Resource')
    return parser
