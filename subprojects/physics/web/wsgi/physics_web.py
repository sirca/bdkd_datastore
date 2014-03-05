#!/usr/bin/env python

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
import hashlib
import os, errno
import csv, json, StringIO
from multiprocessing import Process
from PIL import Image
from functools import wraps

from bdkd.physics.data import Dataset

from flask import ( Flask, request, render_template, send_file, 
        make_response, abort, redirect)

CACHE_ROOT='/var/tmp'
CACHE_LOCATION='static/cache'
CACHE_SALT='55f329b5b9d620090e763a359e102eb0'
REPOSITORY='bdkd-laser-demo'
DEFAULT_DATASET='datasets/Sample dataset'
FBT_MAP='FBT_map.csv'
INJ_MAP='INJ_map.csv'

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


def render_map_plot(dataset, map_name, plot_filename, plot_large_filename):
    mapX = np.array(dataset.get_map_data(INJ_MAP))
    mapY = np.array(dataset.get_map_data(FBT_MAP))
    mapZ = np.array(dataset.get_map_data(map_name))
    fig = plt.figure(figsize=(4.07, 4.40), dpi=100)
    plt.pcolor(mapX,mapY,mapZ)
    plt.axes().set_xlim(np.min(mapX), np.max(mapX))
    plt.axes().set_ylim(np.min(mapY), np.max(mapY))
    plt.colorbar()
    # Regular sized plot
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)
    # Large plot
    img = Image.open(plot_filename)
    large_img = img.resize([x * 10 for x in img.size])
    large_img.save(plot_large_filename)


def cache_map_plot(dataset, map_name, large=False):
    key = cache_key('map', dataset.name, map_name)
    cache_dirname = make_cache_dir(key)
    plot_name = os.path.join(cache_dirname, key)
    plot_location = plot_name + '.png'
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    plot_large_location = plot_name + '-large.png'
    plot_large_filename = os.path.join(CACHE_ROOT, plot_large_location)
    if not os.path.exists(plot_filename):
        p = Process(target=render_map_plot, args=(dataset, map_name, 
            plot_filename, plot_large_filename))
        p.start()
        p.join()
    if large:
        return plot_large_location
    return plot_location


def render_time_series_plot(time_series, from_time, to_time, plot_filename):
    ts_x = range(from_time, to_time, 50)
    fig = plt.figure()
    plt.plot(ts_x, np.array(time_series))
    plt.axes().set_xlim(ts_x[0], ts_x[-1])
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def cache_time_series_plot(dataset_name, feedback, injection, time_series,
        from_time, to_time):
    key = cache_key('time_series', dataset_name, feedback, injection, 
            from_time, to_time)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    if not os.path.exists(plot_filename):
        p = Process(target=render_time_series_plot, args=(time_series, 
            from_time, to_time, plot_filename))
        p.start()
        p.join()
    return plot_location

def render_phase_plot(from_time, to_time, time_series, time_series_selected, 
        delay, plot_filename):
    ts_y = time_series[((from_time // 50)+delay):(-(-to_time // 50)+delay)]
    ts_x = time_series[(from_time // 50):((from_time // 50) + len(ts_y))]
    fig = plt.figure()
    plt.plot(ts_x, ts_y, 'r.')
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def cache_phase_plot(dataset_name, feedback, injection, 
        from_time, to_time, time_series, time_series_selected, delay):
    key = cache_key('phase', dataset_name, feedback, injection, 
            from_time, to_time, delay)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    if not os.path.exists(plot_filename):
        p = Process(target=render_phase_plot, args=(from_time, to_time, time_series, 
            time_series_selected, delay, plot_filename))
        p.start()
        p.join()
    return plot_location


def render_fft_plot(from_time, to_time, time_series, time_series_selected, 
        plot_filename):
    data = np.array(time_series_selected)
    sp = np.fft.fft(data)
    freq = np.fft.fftfreq(data.shape[-1])
    freq = freq[0:-(-(data.shape[-1]) // 2)]
    fig = plt.figure()
    plt.plot(freq, sp.real[0:len(freq)])
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def cache_fft_plot(dataset_name, feedback, injection, 
        from_time, to_time, time_series, time_series_selected):
    key = cache_key('phase', dataset_name, feedback, injection, 
            from_time, to_time)
    cache_dirname = make_cache_dir(key)
    plot_location = os.path.join(cache_dirname, key + '.png')
    plot_filename = os.path.join(CACHE_ROOT, plot_location)
    if not os.path.exists(plot_filename):
        p = Process(target=render_fft_plot, args=(from_time, to_time, time_series, 
            time_series_selected, plot_filename))
        p.start()
        p.join()
    return plot_location

def open_dataset(f):
    """
    Wrapper for routes using 'dataset_name' and 'map_name', to provide a dataset.

    Uses the 'dataset_name' kwarg to open and provide a kwarg called 'dataset'.  
    If the dataset is not found, aborts with 404.

    Furthermore, if a map_name kwarg is provided this is checked for existence in the 
    dataset.  If it does not exist, 404 is returned.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'dataset_name' in kwargs:
            dataset = Dataset.open(REPOSITORY, kwargs['dataset_name'])
            if not dataset:
                abort(404)
            kwargs['dataset'] = dataset
            if 'map_name' in kwargs:
                if not kwargs['map_name'] in dataset.get_map_names():
                    abort(404)
            return f(*args, **kwargs)
    return wrapper


def open_dataset_and_time_series(f):
    """
    Wrapper for loading time series data.  Provides 'feedback', 'injection' and 
    'time_series' to the kwargs.

    Uses the @open_dataset decorator to ensure a valid dataset first.  Then it 
    relies on 'feedback' and 'injection' to be provided in the request args 
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
        if not 'feedback' in request.args or not 'injection' in request.args:
            abort(400)
        feedback = int(request.args.get('feedback', 0))
        injection = int(request.args.get('injection', 0))
        time_series = dataset.get_time_series(feedback, injection)
        if time_series == None or len(time_series) == 0:
            abort(404)
        from_time = int(request.args.get('from', 0))
        to_time = int(request.args.get('to', (len(time_series) - 1) * 50))
        from_idx = (from_time // 50)
        to_idx = -(-to_time // 50)
        kwargs['feedback'] = feedback
        kwargs['injection'] = injection
        kwargs['time_series'] = time_series
        kwargs['time_series_selected'] = time_series[from_idx:to_idx]
        kwargs['from_time'] = from_idx * 50
        kwargs['to_time'] = to_idx * 50
        return f(*args, **kwargs)
    return wrapper


@app.route("/map_names/<path:dataset_name>")
@open_dataset
def get_map_names(dataset_name, dataset):
    map_names = dataset.get_map_names()
    for map in (FBT_MAP, INJ_MAP):
        if map in map_names:
            map_names.remove(map)
    return json.dumps(map_names)


@app.route("/feedback/<path:dataset_name>")
@open_dataset
def get_feedback(dataset_name, dataset):
    fbt = dataset.get_map_data(FBT_MAP)
    if fbt != None:
        return json.dumps(fbt[0,:].tolist())
    else:
        abort(404)


@app.route("/injection/<path:dataset_name>")
@open_dataset
def get_injection(dataset_name, dataset):
    inj = dataset.get_map_data(INJ_MAP)
    if inj != None:
        return json.dumps(inj[:,0].tolist())
    else:
        abort(404)


@app.route("/map_plots/<path:dataset_name>/<map_name>")
@open_dataset
def get_map_plot(dataset_name, dataset, map_name):
    is_large = ('size' in request.args and request.args.get('size') == 'large')
    cache_path = cache_map_plot(dataset, map_name, large=is_large)
    return redirect(cache_path, code=302)
    

@app.route("/map_data/<path:dataset_name>/<map_name>")
@open_dataset
def get_map_data(dataset_name, dataset, map_name):
    map_data = dataset.get_map_data(map_name)
    output = StringIO.StringIO()
    writer = csv.writer(output)
    for row in map_data:
        writer.writerow(row)
    output.seek(0)
    return send_file(output, attachment_filename=map_name, 
            mimetype='text/csv', as_attachment=True)


@app.route("/time_series_plots/<path:dataset_name>")
@open_dataset_and_time_series
def get_time_series_plot(dataset_name, dataset, feedback, injection,
        from_time, to_time, time_series, time_series_selected):
    cache_path = cache_time_series_plot(dataset_name, feedback, injection, time_series_selected,
            from_time, to_time)
    return redirect(cache_path, code=302)


@app.route("/time_series_data/<path:dataset_name>")
@open_dataset_and_time_series
def get_time_series_data(dataset_name, dataset, feedback, injection,
        from_time, to_time, time_series, time_series_selected):
    output = StringIO.StringIO()
    output.writelines(["{0}\n".format(str(x)) for x in time_series_selected])
    output.seek(0)
    return send_file(output, 
            attachment_filename="FB_{0:03d}_INJ_{1:03d}_{2}_{3}.csv".format(
                feedback, injection, from_time, to_time), mimetype='text/csv',
            as_attachment=True)


@app.route("/phase_plots/<path:dataset_name>")
@open_dataset_and_time_series
def get_phase_plot(dataset_name, dataset, feedback, injection,
        from_time, to_time, time_series, time_series_selected):
    delay = int(request.args.get('delay', 1))
    cache_path = cache_phase_plot(dataset_name, feedback, injection, 
            from_time, to_time, time_series, time_series_selected, delay)
    return redirect(cache_path, code=302)


@app.route("/fft_plots/<path:dataset_name>")
@open_dataset_and_time_series
def get_fft_plot(dataset_name, dataset, feedback, injection,
        from_time, to_time, time_series, time_series_selected):
    delay = int(request.args.get('delay', 1))
    cache_path = cache_fft_plot(dataset_name, feedback, injection, 
            from_time, to_time, time_series, time_series_selected)
    return redirect(cache_path, code=302)


@app.route("/")
def index():
    return render_template('index.html',
            datasets=[ DEFAULT_DATASET ], 
            param2="other") 


if __name__=="__main__":
    # Dev mode: allow Flask to serve the cache from the static directory.
    CACHE_ROOT='./'
    app.run(host='0.0.0.0', debug = True)
