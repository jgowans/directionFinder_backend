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
    vacc = np.complex(0)
    for integration_num in range(INTEGRATIONS):
        if integration_num % 100000 == 0:
            logger.info(integration_num)
        siggen.fetch_crosses()
        vacc += siggen.frequency_correlations[(0,1)].bin_at_freq(FREQUENCY)
        accumulated_phase[integration_num] = np.angle(vacc)
    return accumulated_phase

if __name__ == '__main__':
    INTEGRATIONS = 400000
    FREQUENCY = 0.2002

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

    siggen = SignalGenerator(tone_freq = FREQUENCY, 
                             num_channels = 2, 
                             snr = 1, 
                             phase_shifts=np.array((0, 1.234)),
                             amplitude_scales=np.ones(2))

    fig_rmserr, ax_rmserr = plt.subplots()
    for snr in [0.1, 0.03, 0.01, 0.003, 0.001]:
        siggen = SignalGenerator(tone_freq = FREQUENCY, 
                                 num_channels = 2, 
                                 snr = snr,
                                 phase_shifts=np.array((1.234, 0)),
                                 amplitude_scales=np.ones(2))
        logging.info("SNR: {}".format(snr))
        results = []
        for run in range(30):
            logging.info("Run: {}".format(run))
            result = run_single_sim(siggen)
            result = result[::-1]
            result = np.unwrap(result)
            result = result[::-1]
            results.append(result)
        fig, ax0 = plt.subplots()
        for result in results[0:5]:
            ax0.loglog(np.abs(result - 1.234))  # error rather than absolute
        ax0.set_ylabel("Phase output (radians)")
        ax0.set_title("Integrations vs correlator phase output for SNR = {snr}".format(snr = snr))
        ax0.set_xlabel("Integration number")
        plt.axhline(0)
        errors = [result - 1.234 for result in results]
        errors = [((e + np.pi) % (2*np.pi)) - np.pi for e in errors]
        errors_squared = [np.square(e) for e in errors]
        sum_squared = np.zeros(errors_squared[0].shape)
        for error_squared in errors_squared:
            sum_squared += error_squared
        sum_squared /= len(results)
        rms = np.sqrt(sum_squared)
        ax_rmserr.loglog(rms, label="{snr}".format(snr = snr))
    ax_rmserr.set_ylabel("RMS Error (radians)")
    ax_rmserr.set_title("Phase RMS error for various SNR")
    ax_rmserr.set_xlabel("Integration number")
    ax_rmserr.legend(loc='lower left')
    plt.show()
