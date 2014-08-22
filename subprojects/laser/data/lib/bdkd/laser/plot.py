import matplotlib
# matplotlib.use('Agg')  # belongs elsewhere
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
    fig = plt.figure()
    plt.plot(ts_x, np.array(time_series))
    plt.axes().set_xlim(ts_x[0], ts_x[-1])
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
    fig = plt.figure()
    plt.plot(ts_x, ts_y, 'r.')
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
    fig = plt.figure()
    plt.plot(freq, dBm)
    return fig


def render_fft_plot(time_series_selected, z_interval, z_peak_voltage,
        plot_filename):
    fig = fft_plot(time_series_selected, z_interval, z_peak_voltage)
    with open(plot_filename, 'w') as fh:
        fig.canvas.print_png(fh)
    plt.close(fig)
