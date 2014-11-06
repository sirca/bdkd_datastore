#!/usr/bin/env python

"""
Utility library for adding resources.
"""

import argparse
import bdkd.datastore
import bdkd.datastore.util.common as util_common
import json
import os
import sys
import urlparse


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
    parser.add_argument('filenames', nargs='+', action=FilesAction,
            help='List of local file names or URLs of remote files (HTTP, FTP)')
    return parser


def _metadata_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metadata', 
            action=util_common.JsonDictionaryAction, 
            default=dict(),
            help="Meta-data for resource (JSON string dictionary: '{...}')")
    return parser


def _add_options_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--force', action='store_true', default=False,
            help="Force overwriting any existing resource")
    return parser


def _bdkd_metadata_parser(enforce=True):
    """
    Parser for BDKD-specific meta-data options.
    """
    parser = argparse.ArgumentParser(add_help=False)
    # Mandatory arguments
    parser.add_argument('--description', required=enforce,
            help='Human-readable description of the resource')
    parser.add_argument('--author', required=enforce,
            help='Name of the author/creator')
    parser.add_argument('--author-email', required=enforce,
            help='Email address of the author/creator')

    # Optional arguments
    parser.add_argument('--data-type',
            help='String describing the kind of data provided by the Resource')
    parser.add_argument('--tags', action=util_common.JsonArrayAction,
            help='JSON list of additional tags for the Resource')
    parser.add_argument('--version',
            help='Version string for the Resource')
    parser.add_argument('--maintainer',
            help='Name of the person responsible for maintaining the Resource')
    parser.add_argument('--maintainer-email',
            help='Email address of the maintainer')
    parser.add_argument('--custom-fields', action=util_common.JsonDictionaryAction,
            help="A JSON dictionary ('{...}') containing additional custom "
            "fields to be stored in the Resource's meta-data")

    return parser


def add_parser():
    """
    Parser for the generic 'datastore-add' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-add', 
            description="Add a Resource to a datastore, optionally "
            "overwriting any other Resource of the same name.", 
            parents=[
                util_common._repository_resource_parser(),
                _files_parser(),
                _metadata_parser(),
                _add_options_parser(),
            ])
    return parser


def add_bdkd_parser():
    """
    Parser for the BDKD 'datastore-add-bdkd' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-add-bdkd', 
            description="Add a Resource to a datastore, including options "
            "related to BDKD.", 
            parents=[
                util_common._repository_resource_parser(),
                _files_parser(),
                _metadata_parser(),
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
    metadata = dict((k, v) for k, v in metadata.items() if v != None)
    resource_items = []
    for item in resource_args.filenames:
        if os.path.exists(item) and os.path.isdir(item):
            # item is a dir, so recursively expands directories into files
            for root, dir, files in os.walk(item):
                for f in files:
                    resource_items.append(os.path.join(root, f))
        else:
            resource_items.append(item)

    if len(resource_items) == 0:
        raise ValueError("Unable to create an empty resource")
    resource = bdkd.datastore.Resource.new(resource_args.resource_name, 
            resource_items,
            metadata)
    return resource


def _save_resource(repository, resource, force=False):
    existing = repository.get(resource.name)
    if existing:
        if force:
            repository.delete(existing)
        else:
            raise ValueError("Resource '{0}' already exists (use '--force' to overwrite)"
                    .format(resource.name))
    repository.save(resource)


def add_util(argv=None):
    """
    Add a Resource to a Repository, based on the provided arguments.
    """
    resource_args = add_parser().parse_args(argv)
    resource = create_parsed_resource(resource_args, argv=argv)
    _save_resource(resource_args.repository, resource, resource_args.force)


def add_bdkd_util(argv=None):
    resource_args = add_bdkd_parser().parse_args(argv)
    resource = create_parsed_resource(resource_args, 
            meta_parser=_bdkd_metadata_parser(), 
            argv=argv)
    _save_resource(resource_args.repository, resource, resource_args.force)
