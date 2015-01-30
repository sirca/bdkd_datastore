#!/usr/bin/env python

import os
import errno
import sys
import numpy as np
from subprocess import call
import h5py


def pe_single(TS, m, t):
    """
    TS: time series column vector
    m: order of permutation entropy (e.g. 5)
    t: delay of permutation entropy (e.g. 2)
    """
    # permlist = perms(1:m);              % list of possible permutations of order m
    # c = zeros(1,length(permlist));      % initialise array of permutation counts
    perms = dict()

    # for a = 1:length(TS)-t*(m-1)
    for a in range(len(TS) - t*(m-1)):
        # [~,V] = sort(TS(a:t:a+t*(m-1)));
        # % Ranges: MatLab is start:step:stop, Python is start:stop:step
        V = tuple(np.argsort(TS[a:(a + t*(m-1) + 1):t]))
        # for b = 1:length(permlist)
        if V in perms:
            perms[V] += 1
        else:
            perms[V] = 1

    # c = c(c~=0);                % remove zeroes for PE calculation
    c = np.array(perms.values())
    # p = c/sum(c);               % probability dist with zeroes removed
    p = c / float(np.sum(c))
    # pe = -sum(p .* log(p));     % Shannon entropy of p
    pe = -np.sum(np.dot(p, np.log(p)))
    # pe = pe/log(factorial(m));  % Normalised Permutation entropy
    pe = pe / np.log(np.math.factorial(m))
    return pe


def pe_shard(m, t, filename, tmpdir):
    bucket_filename = filename.split('://')[1]
    local_path = os.path.join(tmpdir, bucket_filename)
    local_dir = os.path.dirname(local_path) + '/'
    try:
        os.makedirs(local_dir)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(local_dir):
            pass
        else: raise
    call(['s3cmd', 'sync', filename, local_dir])
    h5f = h5py.File(local_path)
    results = []
    for ds in h5f:
        x_index = h5f[ds].attrs['x_index']
        y_index = h5f[ds].attrs['y_index']
        TS = h5f[ds][()]
        pe = pe_single(TS, m, t)
        results.append([x_index, y_index, pe])
    return results


def store_pes(results, tmpfile, outfile):
    with open(tmpfile, 'w') as tmpfh:
        for result in results:
            print >>tmpfh, ','.join(str(x) for x in result)
    call(['s3cmd', 'sync', tmpfile, outfile])


def main(argv=None):
    for task in sys.stdin.readlines():
        (order, delay, infile, outfile) = task.split("\t")
        print "Order: {0}, delay {1}, infile: {2}, outfile: {3}".format(order, delay, infile, outfile)
        results = pe_shard(int(order), int(delay), infile, '/var/tmp')
        store_pes(results, '/tmp/results', outfile)


if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)
