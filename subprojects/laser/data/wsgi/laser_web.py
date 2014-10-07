#!/usr/bin/env python

import hashlib
import os, errno
import csv, json, StringIO
from multiprocessing import Process
from functools import wraps
import urllib

import matplotlib
matplotlib.use('Agg')
from bdkd.laser.data import Dataset
import bdkd.laser.plot as bdkd_plot
from PIL import Image

from flask import ( Flask, request, render_template, send_file, 
        make_response, abort, redirect)

CACHE_ROOT='/var/tmp'
CACHE_LOCATION='static/cache'
CACHE_SALT='55f329b5b9d620090e763a359e102eb0'


app = Flask(__name__)


def cache_key(*args):
    """
    Generate a deterministic, hard-to-guess key for caching.
    """
    cache_str = CACHE_SALT + ':'.join(str(x) for x in args)
    return hashlib.sha1(cache_str).hexdigest()


def make_cache_dir(key):
    """
    Make cache directory for key.  Returns name of the directory.

    The cache directory will be the cache root plus the first three characters 
    of the cache key.  This serves to divide up the cache files into manageable 
    quantities per cache directory.
    """
    cache_dirname = os.path.join(CACHE_LOCATION, key[0:3])
    try:
        os.makedirs(os.path.join(CACHE_ROOT, cache_dirname))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return cache_dirname


def subprocess_plot(filename, target, args):
    if not os.path.exists(filename):
        p = Process(target=target, args=args)
        p.start()
        p.join()
    else:
        os.utime(filename, None)


def cache_time_series_plot(repository_name, dataset_name, x, y, time_series,
        from_time, to_time, z_interval_base):
    key = cache_key('time_series', repository_name, dataset_name, x, y, 
            from_time, to_time)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    subprocess_plot(filename=plot_filename, 
            target=bdkd_plot.render_time_series_plot, 
            args=(time_series, from_time, to_time, z_interval_base, 
                plot_filename))
    return plot_location


def cache_phase_plot(repository_name, dataset_name, x, y, 
        from_time, to_time, time_series, time_series_selected, delay, 
        z_interval_base):
    key = cache_key('phase', repository_name, dataset_name, x, y, 
            from_time, to_time, delay)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    print len(time_series_selected)
    print from_time
    print to_time
    print delay
    print z_interval_base
    subprocess_plot(filename=plot_filename,
            target=bdkd_plot.render_phase_plot, 
            args=(time_series, from_time, to_time, delay, 
                z_interval_base, plot_filename))
    return plot_location


def cache_fft_plot(repository_name, dataset_name, x, y, 
        from_time, to_time, time_series, time_series_selected, 
        z_interval, z_peak_voltage):
    key = cache_key('fft', repository_name, dataset_name, x, y, 
            from_time, to_time)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    subprocess_plot(filename=plot_filename, 
            target=bdkd_plot.render_fft_plot, 
            args=(time_series_selected, z_interval, z_peak_voltage, 
                plot_filename))
    return plot_location



def open_dataset(f):
    """
    Wrapper for routes using 'repository_name', 'dataset_name' and 'map_name', 
    to provide a dataset.

    Uses the 'dataset_name' kwarg to open and provide a kwarg called 'dataset'.  
    If the dataset is not found, aborts with 404.

    Furthermore, if a map_name kwarg is provided this is checked for existence 
    in the dataset.  If it does not exist, 404 is returned.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'repository_name' in kwargs and 'dataset_name' in kwargs:
            try:
                kwargs['dataset_name'] = urllib.unquote_plus(
                        kwargs['dataset_name'])
                dataset = Dataset.open(kwargs['repository_name'], 
                        kwargs['dataset_name'])
                if not dataset:
                    abort(404)
            except ValueError:
                return redirect('/static/unsupported.html')

            kwargs['dataset'] = dataset
            if 'map_name' in kwargs:
                if not kwargs['map_name'] in dataset.get_map_names():
                    abort(404)
            return f(*args, **kwargs)
        else:
            abort(400)
    return wrapper


def open_dataset_and_time_series(f):
    """
    Wrapper for loading time series data.  Provides 'y', 'x' and 
    'time_series' to the kwargs.

    Uses the @open_dataset decorator to ensure a valid dataset first.  Then it 
    relies on 'y' and 'x' to be provided in the request args 
    (otherwise 400).  If the time series exists, it  will be provided in the 
    kwargs as time_series; otherwise 404.

    The 'from_time' and 'to_time' are the times (in picoseconds) of the 
    selected timeseries -- defaulting to 0 and the last value in the timeseries 
    (respectively).  If provided, these figures will be rounded down and up 
    resp. to the nearest 50ps interval.
    """
    @wraps(f)
    @open_dataset
    def wrapper(*args, **kwargs):
        dataset = kwargs['dataset']
        if not 'y' in request.args or not 'x' in request.args:
            abort(400)
        x = int(request.args.get('x', 0))
        y = int(request.args.get('y', 0))
        interval = dataset.z_interval_base
        time_series = dataset.get_time_series(x, y)
        if time_series == None or len(time_series) == 0:
            abort(404)
        from_time = int(request.args.get('from', 0))
        to_time = int(request.args.get('to', (len(time_series) - 1) * interval))
        from_idx = (from_time // interval)
        to_idx = -(-to_time // interval)
        kwargs['y'] = y
        kwargs['x'] = x
        kwargs['time_series'] = time_series
        kwargs['time_series_selected'] = time_series[from_idx:to_idx]
        kwargs['from_time'] = from_idx * interval
        kwargs['to_time'] = to_idx * interval
        return f(*args, **kwargs)
    return wrapper


@app.route("/repositories/<repository_name>/datasets")
def get_datasets(repository_name):
    dataset_names = Dataset.list(repository_name, None)
    if not dataset_names:
        abort(404)
    return json.dumps(dataset_names)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/readme")
@open_dataset
def get_readme(repository_name, dataset_name, dataset):
    readme_txt = dataset.get_readme()
    if readme_txt:
        return readme_txt
    else:
        abort(404)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/map_names")
@open_dataset
def get_map_names(repository_name, dataset_name, dataset):
    map_names = dataset.get_map_names(include_variables=False)
    return json.dumps(map_names)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>"
        "/map_data/<map_name>")
@open_dataset
def get_map_data(repository_name, dataset_name, dataset, map_name):
    map_data = dataset.get_map_and_variables_data(map_name)
    if map_data != None:
        return json.dumps(map_data)
    else:
        abort(404)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/time_series_plots")
@open_dataset_and_time_series
def get_time_series_plot(repository_name, dataset_name, dataset, x, y,
        from_time, to_time, time_series, time_series_selected):
    cache_path = cache_time_series_plot(repository_name, dataset_name, 
            x, y, time_series_selected, from_time, to_time, 
            dataset.z_interval_base)
    return redirect(cache_path, code=302)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/time_series_data")
@open_dataset_and_time_series
def get_time_series_data(repository_name, dataset_name, dataset, x, y,
        from_time, to_time, time_series, time_series_selected):
    output = StringIO.StringIO()
    output.writelines(["{0}\n".format(str(val)) for val in time_series_selected])
    output.seek(0)
    return send_file(output, 
            attachment_filename="X_{0:03d}_Y_{1:03d}_{2}_{3}.csv".format(
                x, y, from_time, to_time), mimetype='text/csv',
            as_attachment=True)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>"
        "/phase_plots")
@open_dataset_and_time_series
def get_phase_plot(repository_name, dataset_name, dataset, x, y,
        from_time, to_time, time_series, time_series_selected):
    delay = int(request.args.get('delay', 1))
    print time_series_selected
    cache_path = cache_phase_plot(repository_name, dataset_name, x, y, 
            from_time, to_time, time_series, time_series_selected, delay,
            dataset.z_interval_base)
    return redirect(cache_path, code=302)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/fft_data")
@open_dataset_and_time_series
def get_fft_data(repository_name, dataset_name, dataset, x, y,
        from_time, to_time, time_series, time_series_selected):
    (freq, dBm) = bdkd_plot.time_series_fft(time_series_selected, 
            dataset.z_interval, dataset.z_peak_voltage)
    return json.dumps({'fftfreq': freq.tolist(), 
        'fft_real': dBm.real.data.tolist(),
        'fft_imag': dBm.imag.data.tolist() })


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/fft_plots")
@open_dataset_and_time_series
def get_fft_plot(repository_name, dataset_name, dataset, x, y,
        from_time, to_time, time_series, time_series_selected):
    delay = int(request.args.get('delay', 1))
    cache_path = cache_fft_plot(repository_name, dataset_name, x, y, 
            from_time, to_time, time_series, time_series_selected,
            dataset.z_interval, dataset.z_peak_voltage)
    return redirect(cache_path, code=302)


@app.route("/repositories/<repository_name>"
        "/datasets/<path:dataset_name>/")
@open_dataset
def view_dataset(repository_name, dataset_name, dataset):
    return render_template('resource.html',
            repository_name=repository_name,
            dataset_name=dataset_name,
            dataset=dataset, 
            ) 


@app.route("/")
def index():
    return render_template('index.html')


if __name__=="__main__":
    # Dev mode: allow Flask to serve the cache from the static directory.
    CACHE_ROOT='./'
    app.run(host='0.0.0.0', debug = True)
