#!/usr/bin/env python

"""
Utility to pack laser data maps into a HDF5 file.
"""

import argparse
import h5py
import numpy as np
import os
import re

def add_map(map_file, filename, meta=None, fliplr=True, flipud=False, rot90=1):
    map_name = os.path.splitext(os.path.basename(filename))[0]
    raw_data = []
    for line in open(filename):
        raw_data.append([ float(val) for val in line.strip().split(',') ])
    raw_data = np.array(raw_data)
    if fliplr:
        raw_data = np.fliplr(raw_data)
    if flipud:
        raw_data = np.flipud(raw_data)
    for n in range(0, rot90):
        raw_data = np.rot90(raw_data)
    dataset = map_file.create_dataset(map_name, data=raw_data, 
            chunks=(len(raw_data), len(raw_data[0])), compression=9)
    if meta:
        for (key, val) in meta.iteritems():
            dataset.attrs[key] = val
    # File-level meta-data
    map_file.attrs['x_size'] = len(raw_data)
    map_file.attrs['y_size'] = len(raw_data[0])


def pack_maps(map_filename, filenames, fliplr, flipud, rot90):
    maps = h5py.File(map_filename, 'w')

    for (key, val) in filenames.iteritems():
        add_map(maps, key, val, fliplr, flipud, rot90)
    maps.close()


def pack_maps_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-map', required=True,
            help='Name of the file containing the X variables')
    parser.add_argument('--y-map', required=True,
            help='Name of the file containing the Y variables')
    parser.add_argument('--out', default='maps.hdf5',
            help='Out filename')
    parser.add_argument('--fliplr', type=bool, default=True,
            help='Flip the map files horizontally')
    parser.add_argument('--flipud', type=bool, default=False,
            help='Flip the map files vertically')
    parser.add_argument('--rot90', type=int, default=1,
            help='Rotate the map files')
    parser.add_argument('paths', nargs='+',
            help='Map file name(s)')
    return parser


if __name__ == '__main__':
    parser = pack_maps_parser()
    args = parser.parse_args()
    pe_pat = re.compile(r'PE_map_m(\d+)t(\d+).csv')
    
    filenames = dict()
    for filename in args.paths:
        if os.path.exists(filename):
            meta = dict()
            match = pe_pat.search(filename)
            if match:
                meta['type'] = 'permutation entropy'
                meta['order'] = int(match.group(1))
                meta['delay'] = int(match.group(2))
            filenames[filename] = meta
        else:
            raise ValueError("File '{0}' doesn't exist!".format(filename))

    if os.path.exists(args.x_map):
        meta = dict()
        meta['type'] = 'x_variables'
        filenames[args.x_map] = meta
    else:
        raise ValueError("X variables file '{0}' doesn't exist!".format(args.x_map))

    if os.path.exists(args.y_map):
        meta = dict()
        meta['type'] = 'y_variables'
        filenames[args.y_map] = meta
    else:
        raise ValueError("Y variables file '{0}' doesn't exist!".format(args.y_map))

    pack_maps(args.out, filenames, args.fliplr, args.flipud, args.rot90)
    exit(0)
