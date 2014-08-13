#!/usr/bin/env python

"""
Module providing various common components for utilities.
"""

import argparse
import bdkd.datastore


class RepositoryAction(argparse.Action):

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Multiple arguments not allowed")
        super(RepositoryAction, self).__init__(option_strings, dest, **kwargs)


    def __call__(self, parser, namespace, values, option_string=None):
        repository = bdkd.datastore.repository(values)
        if not repository:
            raise ValueError("Repository '{0}' does not exist or is not configured!".format(values))
        setattr(namespace, self.dest, repository)



def _repository_resource_parser():
    """
    Parser providing the mandatory options 'repository_name' and 'resource_name'
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('repository', action=RepositoryAction)
    parser.add_argument('resource_name')
    return parser


