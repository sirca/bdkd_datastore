#!/usr/bin/env python

"""
Utility to pack raw laser data into HDF5 files.
"""

import argparse
import glob
import h5py
import re


def add_time_series(data_file, x_index, y_index, x_variable, y_variable, data_len, data):
    dataset = data_file.create_dataset("x_{0:03}_y_{1:03}".format(x_index, y_index),
            data=data, chunks=(data_len,), compression=9)
    dataset.attrs['x_index'] = x_index
    dataset.attrs['y_index'] = y_index
    dataset.attrs['x_variable'] = x_variable
    dataset.attrs['y_variable'] = y_variable


def get_variables(maps_filename):
    maps = h5py.File(maps_filename, 'r')
    x_variables = None
    y_variables = None
    for (name, data) in maps.items():
        if data.attrs.get('type', None) == 'x_variables':
            x_variables = data[()]
        if data.attrs.get('type', None) == 'y_variables':
            y_variables = data[()]
    maps.close()
    return (x_variables, y_variables)


def get_raw_files(file_glob):
    filenames = glob.glob(file_glob)
    timeseries_pattern = re.compile(r'FB_(\d+)_INJ_(\d+)\..*')
    raw_files = {}

    x_max = -1
    y_max = -1
    for filename in filenames:
        match = timeseries_pattern.search(filename)
        if match:
            x = int(match.group(2))
            y = int(match.group(1))
            raw_files[(x,y)] = filename
            if x > x_max:
                x_max = x
            if y > y_max:
                y_max = y
    return (x_max, y_max, raw_files)


def pack_raw(x_variables, y_variables, x_max, y_max, raw_files, shard_size):
    """
    Pack all raw data into HDF5 files.
    """
    # Raw data file for *all* data
    raw_all_file = h5py.File('raw_all.hdf5', 'w')
    raw_all_file.attrs['x_index_min'] = 0
    raw_all_file.attrs['y_index_min'] = 0
    
    # Loop on each (x,y) combination
    shard_size = shard_size
    shard_file = None

    for y in xrange(y_max + 1):
        for x in xrange(x_max + 1):
            if not (x % shard_size):
                shard_filename = "raw_shard_{0:03}_{1:03}.hdf5".format(x / shard_size * shard_size, y / shard_size * shard_size)
                print shard_filename
                if shard_file:
                    shard_file.close()
                    shard_file = None
                shard_file = h5py.File(shard_filename, 'a')
                shard_file.attrs['x_index_min'] = shard_file.attrs.get('x_index_min', x)
                shard_file.attrs['y_index_min'] = shard_file.attrs.get('y_index_min', y)
                shard_file.attrs['x_index_max'] = shard_file.attrs.get('x_index_max', x + shard_size - 1)
                shard_file.attrs['y_index_max'] = shard_file.attrs.get('y_index_max', y + shard_size - 1)
                shard_file.attrs['shard_size'] = shard_size
            
            # Data
            time_series_filename = raw_files[(x,y)]
            time_series = [float(line.strip()) for line in open(time_series_filename)]
            
            # Variables
            x_variable = x_variables[x][y]
            y_variable = y_variables[x][y]
            add_time_series(shard_file, x, y, x_variable, y_variable, len(time_series), time_series)
            add_time_series(raw_all_file, x, y, x_variable, y_variable, len(time_series), time_series)
            
        # Close shard file at end of row.
        if shard_file:
            shard_file.close()
            shard_file = None

    raw_all_file.close()


def pack_raw_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maps', default='maps.hdf5',
            help='Name of the maps file for this dataset')
    # Typically too many files for command-line: we need a glob pattern
    parser.add_argument('--pattern', required=True,
            help='Pattern to find raw file name(s)')
    parser.add_argument('--shard-size', type=int, default=9,
            help='(S x S) grid of timeseries')
    return parser


def main(argv=None):
    parser = pack_raw_parser()
    args = parser.parse_args(argv)
    (x_variables, y_variables) = get_variables(args.maps)
    (x_max, y_max, raw_files) = get_raw_files(args.pattern)
    pack_raw(x_variables, y_variables, x_max, y_max, raw_files, 
            args.shard_size)
    

if __name__ == "__main__":
    main()
    exit(0)
