#!/usr/bin/env python

# "Reduce" a set of S3 results: read them all and append a map to an existing
# HDF5 file (creates a new maps.hdf5 if not yet exists).

import argparse
import glob
import h5py
import os
from subprocess import call
import sys


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', required=True,
            help='S3 leading path where result files are stored')
    parser.add_argument('--order', type=int, required=True,
            help='Order of permutation entropy (m)')
    parser.add_argument('--delay', type=int, required=True,
            help='Delay of permutation entropy (t)')
    parser.add_argument('--tmpdir', default='/tmp',
            help='Temporary storage directory for results')
    parser.add_argument('--outfile', default='./maps.hdf5',
            help='Output filename')
    return parser


def get_result_files(results_s3, tmpdir):
    # Download all result files from S3, get a list
    call(['s3cmd', 'sync', results_s3, tmpdir])
    results_glob = os.path.join(tmpdir, os.path.basename(os.path.normpath(results_s3)), '*.txt')
    return glob.glob(results_glob)


def read_results(result_files):
    # Read result files
    max_x = 0
    max_y = 0
    results = dict()
    for result_file in result_files:
        with open(result_file) as fh:
            for line in fh:
                (x_str, y_str, pe_str) = line.split(',')
                x = int(x_str)
                if x > max_x:
                    max_x = x
                y = int(y_str)
                if y > max_y:
                    max_y = y
                pe = float(pe_str)
                results[(x, y)] = pe
    # Convert results to 2D array
    rows = []
    for x in range(max_x + 1):
        row = []
        for y in range(max_y + 1):
            row.append(results[(x,y)])
        rows.append(row)
    return rows


def write_results(rows, m, t, out_filename):
    # Write to file
    out_file = h5py.File(out_filename, 'a')
    out_file.attrs['x_size'] = out_file.attrs.get('x_size', default=len(rows))
    out_file.attrs['y_size'] = out_file.attrs.get('y_size', default=len(rows[0]))
    dataset = out_file.create_dataset("m{0:03d}t{1:03d}".format(m, t),
            data = rows, chunks=(len(rows), len(rows[0])), compression=9)
    dataset.attrs['type'] = 'permutation entropy'
    dataset.attrs['order'] = m
    dataset.attrs['delay'] = t
    out_file.close()


def main():
    args = arg_parser().parse_args()

    result_files = get_result_files(args.results, args.tmpdir)
    results = read_results(result_files)
    write_results(results, args.order, args.delay, args.outfile)


if __name__ == '__main__':
    main()
    sys.exit(0)

