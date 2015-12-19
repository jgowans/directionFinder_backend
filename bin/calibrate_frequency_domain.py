#!/usr/bin/env python

from directionFinder_backend.correlator import Correlator
import numpy as np
import matplotlib.pyplot as plt
import logging
from colorlog import ColoredFormatter
import json
import datetime
import time

def plot_offsets(offsets, correlator):
    fig = plt.figure()
    ax = plt.gca()
    for a, b in correlator.cross_combinations:
       ax.plot([f/1e6 for f in offsets['axis']], 
               offsets["{a}{b}".format(a = a, b = b)],
               label = "{a}x{b}".format(a = a, b = b),
               linewidth = 2)
    ax.set_title("Phase difference between all six baselines \nfor broadband input arriving at ADC through full RF chain")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Phase difference (radians)")
    ax.legend(loc=2)
    plt.show()


if __name__ == '__main__':
    # logging infrastructure
    logger = logging.getLogger('main')
    handler = logging.StreamHandler()
    colored_formatter = ColoredFormatter("%(log_color)s%(asctime)s%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(colored_formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    correlator = Correlator(logger = logger.getChild('correlator'))
    correlator.set_shift_schedule(0b00000000000)
    correlator.set_accumulation_len(400000)
    correlator.re_sync()
    time.sleep(1)
    correlator.fetch_all()
    offsets = {}
    offsets['axis'] = np.linspace(
        start = correlator.frequency_correlations[(0,1)].f_start,
        stop = correlator.frequency_correlations[(0,1)].f_stop,
        num = len(correlator.frequency_correlations[(0,1)].signal),
        endpoint = False).tolist()
    for a, b in correlator.cross_combinations:
        offsets["{a}{b}".format(a = a, b = b)] = np.angle(correlator.frequency_correlations[(a, b)].signal).tolist()
    plot_offsets(offsets, correlator)
    offsets["metadata"] = {}
    offsets["metadata"]["created"] = datetime.datetime.utcnow().isoformat("T")
    offsets_json = json.dumps(offsets, indent = 2)
    with open('frequency_domain_calibration.json', 'w') as f:
        f.write(offsets_json)
     

