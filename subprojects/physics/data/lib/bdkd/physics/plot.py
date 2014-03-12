import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from PIL import Image


FBT_MAP='FBT_map.csv'
INJ_MAP='INJ_map.csv'
PEAK_VOLTAGE=0.316


def map_plot(dataset, map_name):
    mapX = np.array(dataset.get_map_data(INJ_MAP))
    mapY = np.array(dataset.get_map_data(FBT_MAP))
    mapZ = np.array(dataset.get_map_data(map_name))
    fig = plt.figure(figsize=(4.07, 4.40), dpi=100)
    plt.pcolor(mapX,mapY,mapZ)
    plt.axes().set_xlim(np.min(mapX), np.max(mapX))
    plt.axes().set_ylim(np.min(mapY), np.max(mapY))
    plt.colorbar()
    return fig


def render_map_plot(dataset, map_name, plot_filename, plot_large_filename):
    fig = map_plot(dataset, map_name)
    # Regular sized plot
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)
    # Large plot
    img = Image.open(plot_filename)
    large_img = img.resize([x * 10 for x in img.size])
    large_img.save(plot_large_filename)


def time_series_plot(time_series, from_time, to_time):
    ts_x = range(from_time, to_time, 50)
    fig = plt.figure()
    plt.plot(ts_x, np.array(time_series))
    plt.axes().set_xlim(ts_x[0], ts_x[-1])
    return fig


def render_time_series_plot(time_series, from_time, to_time, plot_filename):
    fig = time_series_plot(time_series, from_time, to_time)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def phase_plot(from_time, to_time, time_series, time_series_selected, delay):
    ts_y = time_series[((from_time // 50)+delay):(-(-to_time // 50)+delay)]
    ts_x = time_series[(from_time // 50):((from_time // 50) + len(ts_y))]
    fig = plt.figure()
    plt.plot(ts_x, ts_y, 'r.')
    return fig


def render_phase_plot(from_time, to_time, time_series, time_series_selected, 
        delay, plot_filename):
    fig = phase_plot(from_time, to_time, time_series, time_series_selected, 
        delay)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)


def time_series_fft(time_series_selected, timestep=50e-12):
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
    freq = np.fft.fftfreq(data.shape[-1], d=timestep)
    freq = freq[0:xs_half]
    sp = np.fft.fft(data)
    spp = np.sqrt(np.multiply(sp[0:xs_half], 
        np.ma.conjugate(sp[0:xs_half]))) / xs_half
    dBm = 20 * np.log10(spp / PEAK_VOLTAGE)
    return ( freq, dBm )


def fft_plot(from_time, to_time, time_series, time_series_selected):
    (freq, dBm) = time_series_fft(time_series_selected)
    fig = plt.figure()
    plt.plot(freq, dBm)
    return fig


def render_fft_plot(from_time, to_time, time_series, time_series_selected, 
        plot_filename):
    fig = fft_plot(from_time, to_time, time_series, time_series_selected)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)
