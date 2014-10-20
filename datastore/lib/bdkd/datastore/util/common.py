#!/usr/bin/env python
"""
Module providing various common components for utilities.
"""

import argparse
import bdkd.datastore
import json

class JsonAction(argparse.Action):
    """
    The action to perform for arguments with a JSON string payload: convert to 
    object.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Multiple arguments not allowed for {0}"
                    .format(dest))
        super(JsonAction, self).__init__(option_strings, dest, **kwargs)


    def __call__(self, parser, namespace, values, option_string=None):
        json_obj = {}
        if values:
            try:
                json_obj = json.loads(values)
            except ValueError as error:
                raise ValueError("Could not parse {0}: {1}"
                        .format(self.dest, error.message))
        setattr(namespace, self.dest, json_obj)


class JsonDictionaryAction(JsonAction):
    """
    The action to perform for arguments with a JSON string payload: convert to 
    object (dictionary).
    """
    def __call__(self, parser, namespace, values, option_string=None):
        super(JsonDictionaryAction, self).__call__(parser, namespace, 
                values, option_string)
        if not isinstance(getattr(namespace, self.dest), dict):
            raise ValueError("The JSON string for {0} must contain a dictionary"
                    .format(self.dest))


class JsonArrayAction(JsonAction):
    """
    The action to perform for arguments with a JSON string payload: convert to 
    object (array).
    """
    def __call__(self, parser, namespace, values, option_string=None):
        super(JsonArrayAction, self).__call__(parser, namespace, 
                values, option_string)
        if not isinstance(getattr(namespace, self.dest), list):
            raise ValueError("The JSON string for {0} must contain an array"
                    .format(self.dest))


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
