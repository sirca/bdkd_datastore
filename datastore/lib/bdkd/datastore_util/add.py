#!/usr/bin/env python

"""
Utility library for adding resources.
"""

import argparse
import bdkd.datastore
import bdkd.datastore_util.common
import json
import os
import sys
import urlparse

class MetaDataAction(argparse.Action):
    """
    Action to perform for meta-data arguments: parse as JSON and check that 
    it's a dictionary.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Multiple arguments not allowed")
        super(MetaDataAction, self).__init__(option_strings, dest, **kwargs)


    def __call__(self, parser, namespace, values, option_string=None):
        metadata = {}
        if values:
            try:
                metadata = json.loads(values)
            except ValueError as error:
                raise ValueError("Could not parse metadata: {0}".format(error.message))
            if not isinstance(metadata, dict):
                raise ValueError("The JSON meta-data string must contain a dictionary")
        setattr(namespace, self.dest, metadata)


class TagsAction(argparse.Action):
    """
    Action to perform for tags arguments: parse as JSON and check that it's an array.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("Multiple arguments not allowed")
        super(TagsAction, self).__init__(option_strings, dest, **kwargs)


    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            try:
                tags = json.loads(values)
            except ValueError as error:
                raise ValueError("Could not parse metadata: {0}".format(error.message))
            if not isinstance(tags, list):
                raise ValueError("The JSON tags string must contain a list")
        else:
            tags = []
        setattr(namespace, self.dest, tags)


class FilesAction(argparse.Action):
    """
    Action to perform for file arguments: check that they are either files or 
    remote URIs.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        for filename in values:
            if not os.path.exists(filename):
                url = urlparse.urlparse(filename)
                if not url.netloc:
                    raise ValueError("The file '{0}' is neither a local filename nor a URL"
                            .format(filename))
        setattr(namespace, self.dest, values)


def _files_parser():
    """
    Parser that handles the list of files provided on the command line
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('filenames', nargs='+', action=FilesAction)
    return parser


def _add_options_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metadata', action=MetaDataAction, default=dict(),
            help="Meta-data for resource (JSON string)")
    parser.add_argument('--force', action='store_true',
            help="Force overwriting any existing resource")
    return parser


def _bdkd_metadata_parser():
    """
    Parser for BDKD-specific meta-data options.
    """
    parser = argparse.ArgumentParser(add_help=False)
    # Mandatory arguments
    parser.add_argument('--description', required=True)
    parser.add_argument('--author', required=True)
    parser.add_argument('--author_email', required=True)

    # Optional arguments
    parser.add_argument('--tags', action=TagsAction)
    parser.add_argument('--version')
    parser.add_argument('--maintainer')
    parser.add_argument('--maintainer_email')

    return parser


def add_parser():
    """
    Parser for the generic 'datastore-add' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-add', 
            description="Add a Resource to a datastore", 
            parents=[
                bdkd.datastore_util.common._repository_resource_parser(),
                _files_parser(),
                _add_options_parser(),
            ])
    return parser


def add_bdkd_parser():
    """
    Parser for the BDKD 'datastore-add-bdkd' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-add-bdkd', 
            description="Add a BDKD Resource to a datastore", 
            parents=[
                bdkd.datastore_util.common._repository_resource_parser(),
                _files_parser(),
                _add_options_parser(),
                _bdkd_metadata_parser(),
            ])
    return parser


def create_parsed_resource(resource_args, meta_parser=None, argv=None):
    """
    Creates an unsaved Resource object by parsing the provided arguments 
    (default: sys.argv) using the given resource arguments and metadata parser.

    If a metadata parser is provided it will be used to parse arguments from 
    argv.  These arguments will be treated as meta-data: they will be merged 
    into the metadata dictionary and used when creating the resource.
    """
    metadata = dict(**resource_args.metadata)
    if meta_parser:
        meta_args = meta_parser.parse_known_args(argv)
        metadata.update(meta_args[0].__dict__)
    resource = bdkd.datastore.Resource.new(resource_args.resource_name, 
            resource_args.filenames,
            **metadata)
    return resource


def _save_resource(repository, resource, force=False):
    existing = repository.get(resource.name)
    if existing:
        if resource_args.force:
            repository.delete(existing)
        else:
            raise ValueError("Resource '{}' already exists (use '--force' to overwrite)"
                    .format(resource.name))
    repository.save(resource)


def add_util(argv=None):
    """
    Add a Resource to a Repository, based on the provided arguments.
    """
    resource_args = add_parser().parse_args(argv)
    resource = create_parsed_resource(resource_args, argv=argv)
    _save_resource(resource_args.repository, resource)


def add_bdkd_util(argv=None):
    resource_args = add_bdkd_parser().parse_args(argv)
    resource = create_parsed_resource(resource_args, 
            meta_parser=_bdkd_metadata_parser(), 
            argv=argv)
    _save_resource(resource_args.repository, resource)
