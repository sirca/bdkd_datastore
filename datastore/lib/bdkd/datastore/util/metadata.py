#!/usr/bin/env python

"""
Utility library for editing meta-data.
"""

import argparse
import bdkd.datastore
import bdkd.datastore.util.common as util_common
import bdkd.datastore.util.add as util_add


def update_metadata_bdkd_parser():
    """
    Parser for the BDKD 'datastore-update-metadata' utility
    """
    parser = argparse.ArgumentParser(prog='datastore-update-metadata', 
            description="Update a resource's meta-data, including BDKD options", 
            parents=[
                util_common._repository_resource_parser(),
                util_add._metadata_parser(),
                util_add._bdkd_metadata_parser(enforce=False),
            ])
    return parser


def _update_metadata(repository, resource_name, metadata):
    existing = repository.get(resource_name)
    if existing:
        repository.edit_resource(existing)
        existing.metadata.update(metadata)
        existing.metadata = dict((k, v) for k, v in existing.metadata.items()
                if v != None)
        repository.save(existing, overwrite=True)
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))


def _update_with_parser(all_parser, meta_parser, argv):
    all_args = all_parser.parse_args(argv)
    metadata = dict()
    if meta_parser:
        meta_args = meta_parser.parse_known_args(argv)
        metadata = dict((k, v) for k, v in meta_args[0].__dict__.items() 
                if v != None)
    metadata.update(all_args.metadata)
    _update_metadata(all_args.repository, all_args.resource_name, metadata)


def update_metadata_util(argv=None):
    """
    Update the metadata for a resource.
    """
    _update_with_parser(update_metadata_bdkd_parser(),  
            util_add._bdkd_metadata_parser(enforce=False), argv)
