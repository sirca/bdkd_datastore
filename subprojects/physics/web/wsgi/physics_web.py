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

CACHE_ROOT='static/cache'
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
    cache_dirname = os.path.join(CACHE_ROOT, key[0:3])
    try:
        os.makedirs(cache_dirname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return cache_dirname


def render_map_plot(dataset, map_name, plot_filename, plot_large_filename):
    mapX = np.array(dataset.get_map_data(INJ_MAP))
    mapY = np.array(dataset.get_map_data(FBT_MAP))
    mapZ = np.array(dataset.get_map_data(map_name))
    fig = plt.figure(frameon=False, figsize=(351,251), dpi=1)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.autoscale_view('tight')
    plt.pcolor(mapX,mapY,mapZ)
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
    plot_filename = plot_name + '.png'
    plot_large_filename = plot_name + '-large.png'
    if not os.path.exists(plot_filename):
        p = Process(target=render_map_plot, args=(dataset, map_name, 
            plot_filename, plot_large_filename))
        p.start()
        p.join()
    if large:
        return plot_large_filename
    return plot_filename


def render_time_series_plot(time_series, plot_filename):
    ts_x = range(0, len(time_series)*50, 50)
    fig = plt.figure()
    plt.plot(ts_x, np.array(time_series))
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def cache_time_series_plot(dataset_name, feedback, injection, time_series):
    key = cache_key('time_series', dataset_name, feedback, injection)
    cache_dirname = make_cache_dir(key)
    plot_filename = os.path.join(cache_dirname, key + '.png')
    if not os.path.exists(plot_filename):
        p = Process(target=render_time_series_plot, args=(time_series, plot_filename))
        p.start()
        p.join()
    return plot_filename


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
        kwargs['feedback'] = feedback
        kwargs['injection'] = injection
        kwargs['time_series'] = time_series
        return f(*args, **kwargs)
    return wrapper


@app.route("/map_names/<path:dataset_name>")
@open_dataset
def get_map_names(dataset_name, dataset):
    map_names = dataset.get_map_names()
    for map in (FBT_MAP, INJ_MAP):
        print map
        if map in map_names:
            map_names.remove(map)
    return json.dumps(map_names)


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


@app.route("/time_series_plot/<path:dataset_name>")
@open_dataset_and_time_series
def get_time_series_plot(dataset_name, dataset, feedback, injection, time_series):
    cache_path = cache_time_series_plot(dataset_name, feedback, injection, time_series)
    return redirect(cache_path, code=302)


@app.route("/time_series_data/<path:dataset_name>")
@open_dataset_and_time_series
def get_time_series_data(dataset_name, dataset, feedback, injection, time_series):
    output = StringIO.StringIO()
    output.writelines(["{0}\n".format(str(x)) for x in time_series])
    output.seek(0)
    return send_file(output, 
            attachment_filename="FB_{0:03d}_INJ_{1:03d}.csv".format(
                feedback, injection), 
            as_attachment=True)


@app.route("/")
def index():
    return render_template('index.html',
            datasets=[ DEFAULT_DATASET ], 
            param2="other") 


if __name__=="__main__":
    app.run(host='0.0.0.0', debug = True)
