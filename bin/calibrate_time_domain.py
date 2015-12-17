#!/usr/bin/env python

from directionFinder_backend.correlator import Correlator
import scipy.signal as signal
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
import logging
import time
import timeit

def test_cross_first_vs_resample_first():
    c.upsample_factor = 100
    c.subsignal_length_max = 2**19
    c.time_domain_padding = 100
    sig_lengths = [np.int(x) for x in np.linspace(12000, 16000, 20)]
    x_first_times = []
    resample_first_times = []
    for sig_len in sig_lengths:
        c.subsignal_length_max = sig_len
        x_first_times.append(
            timeit.timeit(
                stmt = "c.do_time_domain_cross_correlation_cross_first()",
                setup = "from __main__ import c",
                number = 1))
        resample_first_times.append(
            timeit.timeit(
                stmt = "c.do_time_domain_cross_correlation_resample_first()",
                setup = "from __main__ import c",
                number = 1))
        print("{l} -> {t}".format(l = sig_len, t = resample_first_times[-1]))
    fig = plt.figure()
    ax1 = fig.gca()
    ax1.plot(sig_lengths, x_first_times, 'b', label='x first')
    ax1.plot(sig_lengths, resample_first_times, 'r',  label="resample first")
    #ax2 = ax1.twinx()
    #ax2.plot(sig_lengths, resample_first_times, 'r',  label="resample first")
    ax1.legend()
    #ax2.legend()
    plt.show()

def plot_interpolated_vs_non_interpolated():
    """ This does not work anymore due to the interface in 
    Correlator being changed. Keeping for pyplot reference
    """
    (x_first, x_first_time), (x_first_upped, x_first_time_upped) = c.do_time_domain_cross_correlation_cross_first()
    # normalise:
    x_first_upped = x_first_upped/(max(x_first))
    x_first = x_first/max(x_first)
    x_first_time *= 1e6
    x_first_time_upped *= 1e6
    print(time.time() - t0)
    t0 = time.time()
    print(time.time() - t0)
    #print(np.argmax(c.time_domain_correlations[1]))
    #plt.plot(c.time_domain_correlation_time, c.time_domain_correlations[0], marker='.')
    ax1 = plt.gca()
    ax1.plot(up_first_time, up_first, marker='.', color='b')
    #ax.plot(x_first_time_upped, x_first_upped, color='b', linewidth=2, marker='.', markersize=10, label="upsampled")
    plt.plot(x_first_time_upped, x_first_upped, color='b', linewidth=2,label="upsampled")
    ax.plot(x_first_time, x_first, marker='.', color='r', linewidth=2, markersize=15, label="Raw")
    xy = (x_first_time[np.argmax(x_first)-1], x_first[np.argmax(x_first)-1])
    print(xy)
    ax.annotate('higher', xy=xy,
                xytext=(0.1, 0.4), textcoords='axes fraction',
                arrowprops=dict(facecolor='black', shrink=0.09, width=2),
                horizontalalignment='right', verticalalignment='top',)
    xy = (x_first_time[np.argmax(x_first)+1], x_first[np.argmax(x_first)+1])
    ax.annotate('lower', xy=xy,
                xytext=(0.5, 0.5), textcoords='axes fraction',
                arrowprops=dict(facecolor='black', shrink=0.09, width=2),
                horizontalalignment='right', verticalalignment='top',)
    ax.set_title("Comparison of raw time domain cross correlation with upsampled version")
    ax.set_xlabel("Time shift (us)")
    ax.set_ylabel("Cross correlation value (normalised)")
    ax.legend()
    plt.show()

def do_calibration(c):
    c.upsample_factor = 100
    c.subsignal_length_max = 2**19
    c.time_domain_padding = 100
    c.do_time_domain_cross_correlation_cross_first()
    offsets = {}
    for baseline, correlation in c.time_domain_correlations.items():
        argmax = np.argmax(correlation)
        offset = c.time_domain_correlations_sample_times

def plot_calibration(c):
    fig = plt.figure()
    ax = plt.gca()
    for baseline, correlation in c.time_domain_correlations.items():
        correlation_max_val = correlation[np.argmax(correlation)]
        correlation_max_time = c.time_domain_correlations_sample_times[np.argmax(correlation)]
        lines = ax.plot(
            c.time_domain_correlations_sample_times,
            correlation,
            label = baseline)
        ax.plot([correlation_max_time, correlation_max_time], [0, correlation_max_val], color = lines[0].get_color())
    axins = zoomed_inset_axes(ax, 6, loc=1)
    for baseline, correlation in c.time_domain_correlations.items():
        correlation_max_val = correlation[np.argmax(correlation)]
        correlation_max_time = c.time_domain_correlations_sample_times[np.argmax(correlation)]
        lines = ax.plot(
            c.time_domain_correlations_sample_times,
            correlation,
            label = baseline)
        axins.plot([correlation_max_time, correlation_max_time], [0, correlation_max_val], color = lines[0].get_color())
    ax.legend()
    plt.show()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    c = Correlator()
    logging.info("Created a Correlator")
    c.fetch_time_domain_snapshot(force=True)
    do_calibration(c)
    plot_calibration(c)


