#!/usr/bin/env python

from directionFinder_backend.correlator import Correlator
from directionFinder_backend.scpi import SCPI
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
    ax.set_title("Phase difference between all six baselines for broadband input arriving at ADC through full RF chain AFTER CALIBRATION")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Phase difference (radians)")
    ax.set_ylim(top=3, bottom=-3)
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
    #correlator.apply_cable_length_calibrations('/home/jgowans/workspace/directionFinder_backend/config/cable_length_calibration.json')
    #correlator.apply_frequency_bin_calibrations('/home/jgowans/workspace/directionFinder_backend/config/frequency_domain_calibration_through_chain.json')
    #correlator.add_frequency_bin_calibrations('/home/jgowans/workspace/directionFinder_backend/config/frequency_domain_calibration_direct_in_phase.json')
    time.sleep(1)
    correlator.re_sync()
    
    offsets = {}
    offsets['axis'] = []
    for a, b in correlator.cross_combinations:
        offsets["{a}{b}".format(a = a, b = b)] = []

    correlator.fetch_crosses()
    #correlator.apply_frequency_domain_calibrations()
    for f in correlator.frequency_correlations[(0, 1)].frequency_bins:
        for a, b in correlator.cross_combinations:
            offsets["{a}{b}".format(a = a, b = b)].append(
                correlator.frequency_correlations[(a, b)].phase_at_freq(f))
        offsets['axis'].append(f)
        
    plot_offsets(offsets, correlator)
    offsets["metadata"] = {}
    offsets["metadata"]["created"] = datetime.datetime.utcnow().isoformat("T")
    offsets_json = json.dumps(offsets, indent = 2)
    with open('frequency_domain_plots.json', 'w') as f:
        f.write(offsets_json)
     

