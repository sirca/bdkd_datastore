#!/usr/bin/env python

import argparse
import bdkd.datastore
import bdkd.datastore.util.common as util_common
import bdkd.datastore.util.add as util_add
from bdkd.laser.data import Dataset
import h5py

def _laser_metadata_parser():
    """
    Parser for laser-specific meta-data options.
    """
    parser = argparse.ArgumentParser(add_help=False)

    # Mandatory arguments
    parser.add_argument('--x-name', required=True)
    parser.add_argument('--y-name', required=True)
    parser.add_argument('--z-name', required=True)
    parser.add_argument('--z-interval-base', type=int, required=True)
    parser.add_argument('--z-interval-exponent', type=float, required=True)
    parser.add_argument('--z-peak-voltage', type=float, required=True)

    # Optional arguments
    parser.add_argument('--maps', default='maps.hdf5')
    parser.add_argument('--x-variables', default=None)
    parser.add_argument('--y-variables', default=None)
    parser.add_argument('--raw-all', default='raw_all.hdf5')
    parser.add_argument('--shard-size', type=int, default=None)
    parser.add_argument('--readme', default=None)

    return parser


def add_laser_parser():
    parser = argparse.ArgumentParser(prog='datastore-add-laser', 
            description="Add a BDKD Resource to a datastore", 
            parents=[
                util_common._repository_resource_parser(),
                util_add._files_parser(),
                util_add._add_options_parser(),
                util_add._bdkd_metadata_parser(),
                _laser_metadata_parser(),
            ])
    return parser


def _laser_metadata_raw(resource):
    """
    Set raw file meta-data, from meta-data inside the original HDF5 files. 
    (Existing meta-data is not overwritten.)

    This also involves setting the shard size and Z size (timeseries length) if 
    not already known.
    """
    shard_size = resource.metadata.get(Dataset.META_SHARD_SIZE, None)
    z_size = None
    raw_files = resource.files_matching(r'raw.*\.hdf5$')
    for raw_file in raw_files:
        print raw_file.location()
        raw = h5py.File(raw_file.local_path(), 'r')
        # Get Z size if not yet known
        if not z_size:
            (name, raw_data) = raw.iteritems().next()
            z_size = len(raw_data)
        # Get all meta-data
        for key, value in raw.attrs.items():
            # Get shard size if available
            if key == Dataset.META_SHARD_SIZE:
                if not shard_size:
                    shard_size = value
            # Other meta-data
            else:
                raw_file.metadata[key] = raw_file.metadata.get(key, value)
        raw.close()
    resource.metadata[Dataset.META_SHARD_SIZE] = resource.metadata.get(
            Dataset.META_SHARD_SIZE, shard_size)
    resource.metadata[Dataset.META_Z_SIZE] = resource.metadata.get(
            Dataset.META_Z_SIZE, z_size)


def _laser_metadata_maps(resource):
    """
    Get X and Y sizes from the maps.

    Also set resource-file meta-data from the HDF5 file.
    """
    maps_name = resource.metadata.get(Dataset.META_MAPS)
    if not maps_name:
        raise ValueError("Maps filename not defined")
    maps_file = resource.file_ending(maps_name)
    if not maps_file:
        raise ValueError("Maps filename not valid")
    maps = h5py.File(maps_file.local_path(), 'r')
    # Set x_size and y_size if not already
    resource.metadata[Dataset.META_X_SIZE] = (
            resource.metadata.get(Dataset.META_X_SIZE,
                maps.attrs.get(Dataset.META_X_SIZE, None))
            )
    resource.metadata[Dataset.META_Y_SIZE] = (
            resource.metadata.get(Dataset.META_Y_SIZE,
                maps.attrs.get(Dataset.META_Y_SIZE, None))
            )
        
    # Set x_variables and y_variables if not already
    for name, data in maps.iteritems():
        map_type = data.attrs.get('type', None)
        if map_type:
            if map_type == Dataset.META_X_VARIABLES:
                resource.metadata[Dataset.META_X_VARIABLES] = (
                        resource.metadata.get(Dataset.META_X_VARIABLES, name)
                        )
            if map_type == Dataset.META_Y_VARIABLES:
                resource.metadata[Dataset.META_Y_VARIABLES] = (
                        resource.metadata.get(Dataset.META_Y_VARIABLES, name)
                        )
    maps.close()


def _laser_readme(resource):
    """
    Ensure the README name is set (if possible)
    """
    readme_name = resource.metadata.get(Dataset.META_README, None)
    if not readme_name:
        text_files = resource.files_matching(r'\.txt$')
        if len(text_files) == 1:
            readme_name = text_files[0].location_or_remote()
        resource.metadata[Dataset.META_README] = (
                resource.metadata.get(Dataset.META_README, readme_name)
                )


def add_laser_util(argv=None):
    resource_args = add_laser_parser().parse_args(argv)
    resource = util_add.create_parsed_resource(resource_args, 
            meta_parser=argparse.ArgumentParser(parents=[
                util_add._bdkd_metadata_parser(),
                _laser_metadata_parser(),
                ]), 
            argv=argv)
    _laser_metadata_raw(resource)
    _laser_metadata_maps(resource)
    _laser_readme(resource)
    Dataset.validate(resource)
    util_add._save_resource(resource_args.repository, resource)
