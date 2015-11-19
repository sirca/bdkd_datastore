# Copyright 2015 Nicta
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import matplotlib
import matplotlib.pyplot as plt

import numpy as np


def map_plot(dataset, map_name):
    mapX = np.array(dataset.get_x_variables())
    mapY = np.array(dataset.get_y_variables())
    mapZ = np.array(dataset.get_map_data(map_name))
    fig = plt.figure(figsize=(4.07, 4.40), dpi=100)
    plt.pcolor(mapX,mapY,mapZ)
    plt.axes().set_xlim(np.min(mapX), np.max(mapX))
    plt.axes().set_ylim(np.min(mapY), np.max(mapY))
    plt.colorbar()
    return fig


def render_map_plot(dataset, map_name, plot_filename):
    fig = map_plot(dataset, map_name)
    # Regular sized plot
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def time_series_plot(time_series, from_time, to_time, z_interval_base):
    ts_x = range(from_time, to_time, z_interval_base)
    fig = plt.figure(figsize=(6.25, 4.6875), dpi=64)
    fig.set_facecolor('white')
    fig.subplots_adjust(bottom=0.20, top=0.95)
    plt.plot(ts_x, np.array(time_series))
    plt.axes().set_xlim(ts_x[0], ts_x[-1])
    plt.xticks(rotation=90)
    return fig


def render_time_series_plot(time_series, from_time, to_time, z_interval_base, 
        plot_filename):
    fig = time_series_plot(time_series, from_time, to_time, z_interval_base)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def phase_plot(time_series, from_time, to_time, 
        delay, z_interval_base):
    ts_y = time_series[((from_time // z_interval_base)+delay):
            (-(-to_time // z_interval_base)+delay)]
    ts_x = time_series[(from_time // z_interval_base):
            ((from_time // z_interval_base) + len(ts_y))]
    print "range {0}:{1}".format(((from_time // z_interval_base)+delay),
(-(-to_time // z_interval_base)+delay))
    print "ts_x: {0}, ts_y: {1}".format(len(ts_x), len(ts_y)) 
    fig = plt.figure(figsize=(5.0, 3.75), dpi=80)
    fig.set_facecolor('white')
    plt.plot(ts_x, ts_y, 'r.')
    plt.xticks(rotation=90)
    plt.tight_layout()
    return fig


def render_phase_plot(time_series, from_time, to_time, 
        delay, z_interval_base, plot_filename):
    fig = phase_plot(time_series, from_time, to_time, 
        delay, z_interval_base)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def time_series_fft(time_series_selected, z_interval, z_peak_voltage):
    """
    Get the frequency buckets and positive, real component of a FFT analysis of 
    the provided time series.

    Both FFT and FFT frequency buckets are calculated for the dataset.  Only 
    the first half (rounding up) of the results are returned: these correspond 
    with the positive values. (Negatives are not required: they are a mirror 
    image of the positive.)
    """
    data = np.array(time_series_selected)
    xs = len(data)
    xs_half = -(-xs // 2)
    freq = np.fft.fftfreq(data.shape[-1], d=z_interval)
    freq = freq[0:xs_half]
    sp = np.fft.fft(data)
    spp = np.sqrt(np.multiply(sp[0:xs_half], 
        np.ma.conjugate(sp[0:xs_half]))) / xs_half
    dBm = 20 * np.log10(spp / z_peak_voltage)
    return ( freq, dBm )


def fft_plot(time_series_selected, z_interval, z_peak_voltage):
    (freq, dBm) = time_series_fft(time_series_selected, z_interval, z_peak_voltage)
    fig = plt.figure(figsize=(5.0, 3.75), dpi=80)
    fig.set_facecolor('white')
    plt.plot(freq, dBm)
    plt.xticks(rotation=90)
    plt.tight_layout()
    return fig


def render_fft_plot(time_series_selected, z_interval, z_peak_voltage,
        plot_filename):
    fig = fft_plot(time_series_selected, z_interval, z_peak_voltage)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)
