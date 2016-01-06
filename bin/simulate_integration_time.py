#!/usr/bin/env python

from directionFinder_backend.correlator import Correlator
import numpy as np
import matplotlib.pyplot as plt
import logging
import time
from colorlog import ColoredFormatter
from directionFinder_backend.signal_generator import SignalGenerator




def run_single_sim(siggen):
    accumulated_phase = np.ndarray((INTEGRATIONS))
    vacc = 0
    for integration_num in range(INTEGRATIONS):
        if integration_num % 1000 == 0:
            logger.info(integration_num)
        siggen.fetch_crosses()
        vacc += siggen.frequency_correlations[(0,1)].bin_at_freq(0.2)
        accumulated_phase[integration_num] = np.angle(vacc)
    return accumulated_phase

if __name__ == '__main__':
    INTEGRATIONS = 40000
    FREQUENCY = 234e6

    # setup root logger. Shouldn't be used much but will catch unexpected messages
    colored_formatter = ColoredFormatter("%(log_color)s%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(colored_formatter)
    handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logger = logging.getLogger('main')
    logger.propagate = False
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    root.debug("Root debug")
    root.info("Root info")
    root.warn("Root warning")

    logger.debug("Logger debug")
    logger.info("Logger info")
    logger.warn("Logger warning")

    siggen = SignalGenerator(num_channels = 2, snr = 0.1, phase_shifts=np.zeros(2), amplitude_scales=np.ones(2))

    for _ in range(1):
        phases = run_single_sim(siggen)
        plt.plot(phases)
    plt.show()
