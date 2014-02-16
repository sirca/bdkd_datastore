#!/usr/bin/env python

"""
Search directories for dataset files, divide the raw data into a grid of 
shards, and write HDF5 files containing the data packed/compressed to an output 
directory.
"""

import argparse, csv, h5py, os, re, shutil, sys
from multiprocessing import Pool


class TimeSeries(object):
    """
    A file at path/name for a combination of feedback and injection.
    """
    def __init__(self, fb, inj, filename):
        self.fb = fb
        self.inj = inj
        self.filename = filename


class TimeSeriesShard(object):
    """
    A set of files, starting at a given feedback/injection combination, for a 
    given shard size.
    """
    def __init__(self, fb_start, inj_start, shard_size, time_series_files):
        self.fb_start = fb_start
        self.inj_start = inj_start
        self.shard_size = shard_size
        self.time_series_files = time_series_files


def expand_paths(paths):
    """
    Check and expand all file search paths provided on the command-line.
    """
    ds_paths = []
    for path in paths:
        full_path = os.path.expanduser(path)
        if os.path.isdir(full_path):
            ds_paths.append(full_path)
        else:
            raise ValueError("Path '{0}' is not a valid directory!".format(path))
    return ds_paths


def find_files(ds_paths):
    """
    Go through all provided search paths finding files, dividing them up by pattern.

    For the timeseries files, keeps track of the maximum feedback and injection values.

    Returns:
     - Dictionary of timeseries files, by (FB,INJ) combination.
     - List of map files
     - List of text files
     - Maximum feedback number
     - Maximum injection number
    """
    re_ts = re.compile('FB_(\d+)_INJ_(\d+).csv')
    re_map = re.compile('.*_map.*\.csv')
    re_txt = re.compile('.*\.txt')
    time_series = dict()
    max_fb = 0
    max_inj = 0
    maps = []
    text = []
    for ds_path in ds_paths:
        for dirpath, dirnames, filenames in os.walk(ds_path):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                m_ts = re_ts.match(filename)
                if m_ts:
                    fb = int(m_ts.group(1))
                    if fb > max_fb:
                        max_fb = fb
                    inj = int(m_ts.group(2))
                    if inj > max_inj:
                        max_inj = inj
                    time_series[(fb, inj)] = full_path
                elif re_map.match(filename):
                    maps.append(full_path)
                elif re_txt.match(filename):
                    text.append(full_path)
    return (time_series, maps, text, max_fb, max_inj)


def shard_time_series(time_series, max_fb, max_inj, shard_size):
    """
    Divide up the time series files into a grid based on shard size.
    """
    shards = []
    for fb_shard in range(0, max_fb, shard_size):
        for inj_shard in range(0, max_inj, shard_size):
            series_files = []
            for i_fb in range(0, shard_size):
                for i_inj in range(0, shard_size):
                    key = (fb_shard + i_fb, inj_shard + i_inj)
                    if key in time_series:
                        in_filename = time_series[key]
                        series_files.append(TimeSeries(fb_shard + i_fb, inj_shard + i_inj, in_filename))
            if len(series_files):
                shards.append(TimeSeriesShard(fb_shard, inj_shard, shard_size, series_files))
    return shards


def write_shard(shard, out_dir):
    """
    Write a time series shard to a HDF5 file in the output directory.
    """
    out_filename = os.path.join(out_dir,
            'FB_{0:03d}_INJ_{1:03d}_{2:02}.hdf5'.format(
                shard.fb_start, shard.inj_start, shard.shard_size))
    out_file = h5py.File(out_filename, 'w')
    out_file.attrs['FB_start'] = shard.fb_start
    out_file.attrs['INJ_start'] = shard.inj_start
    out_file.attrs['shard_size'] = shard.shard_size

    for time_series in shard.time_series_files:
        data = []
        with open(time_series.filename) as in_file:
            for line in in_file:
                data.append(float(line))
        dataset = out_file.create_dataset(os.path.basename(time_series.filename),
            data=data, chunks=(len(data),), compression=9)
        dataset.attrs['FB'] = time_series.fb
        dataset.attrs['INJ'] = time_series.inj
    out_file.close()


def write_shards(shards, out_dir, threads):
    """
    Write all shards out to HDF5 in the output directory, using 
    multi-processing.
    """
    pool = Pool(processes=threads)
    results = []
    for shard in shards:
        results.append(pool.apply_async(write_shard, [shard, out_dir]))
    for result in results:
        result.wait()

def write_maps(maps, out_dir):
    """
    Write all maps into a HDF5 file called "maps.hdf5".
    """
    out_filename = os.path.join(out_dir, 'maps.hdf5')
    out_file = h5py.File(out_filename, 'w')
    
    for map in maps:
        data = []
        with open(map) as in_file:
            rows = csv.reader(in_file)
            for row in rows:
                figures = []
                for figure in row:
                    figures.append(float(figure))
                data.append(figures)
        dataset = out_file.create_dataset(os.path.basename(map),
                data=data, chunks=(len(data), len(data[0])), compression=9)
    out_file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shard', type=int, default=9, 
            help='Time series shard size: [N x N] squares of time series data')
    parser.add_argument('--dest', default='.', 
            help='Destination directory')
    parser.add_argument('--threads', type=int, default=4,
            help='# of threads of execution for writing data')
    parser.add_argument('paths', metavar='path', nargs='+', 
            help='Directory (or directories) containing files')

    args = parser.parse_args()

    print 'Finding files...'
    ds_paths = expand_paths(args.paths)
    dest_dir = os.path.expanduser(args.dest)
    (time_series, maps, text, max_fb, max_inj) = find_files(ds_paths)

    print 'Sharding data...'
    shards = shard_time_series(time_series, max_fb, max_inj, args.shard)
    write_shards(shards, dest_dir, args.threads)

    print 'Writing other files to destination directory...'
    write_maps(maps, dest_dir)
    for text_file in text:
        shutil.copy(text_file, dest_dir)

    print 'Done.'
    sys.exit(0)

