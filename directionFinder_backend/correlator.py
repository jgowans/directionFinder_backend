#!/usr/bin/env python

'''
Interface to the ROACH.
'''
import logging
import corr
from correlation import Correlation
from snapshot import Snapshot
from control_register import ControlRegister
import itertools
import numpy as np
import scipy.signal
import time


class Correlator:
    def __init__(self, ip_addr='localhost', num_channels=4, fs=800e6, logger=logging.getLogger(__name__)):
        """The interface to a ROACH cross correlator

        Keyword arguments:
        ip_addr -- IP address (or hostname) of the ROACH. (default: localhost)
        num_channels -- antennas in the correlator. (default: 4)
        fs -- sample frequency of antennas. (default 800e6; 800 MHz)
        logger -- logger to use. (default: new default logger)
        """
        self.logger = logger
        self.fpga = corr.katcp_wrapper.FpgaClient(ip_addr)
        time.sleep(0.1)
        self.num_channels = num_channels
        self.fs = np.float64(fs)
        self.cross_combinations = list(itertools.combinations(range(num_channels), 2))  # [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        # only 0x0 has been implemented
        #self.auto_combinations = [(x, x) for x in range(num_channels)] # [(0, 0), (1, 1), (2, 2), (3, 3)]
        self.auto_combinations = [(0, 0)]
        self.frequency_correlations = {}
        for comb in (self.cross_combinations + self.auto_combinations):
            self.frequency_correlations[comb] = Correlation(fpga = self.fpga,
                                                  comb = comb,
                                                  f_start = 0,
                                                  f_stop = fs/2,
                                                  logger = self.logger.getChild(str(comb)) )
            #self.correlations[comb].fetch_signal(force=True)  # ensure populated with some data
        self.time_domain_snap = Snapshot(fpga = self.fpga, 
                                         name = 'dram',
                                         dtype = np.int8,
                                         cvalue = False,
                                         logger = self.logger.getChild('time_domain_snap'))
        self.control_register = ControlRegister(self.fpga, self.logger.getChild('control_reg'))

    def fetch_time_domain_snapshot(self, force=False):
        # TODO: some arming perhaps here?
        # Idea: arm it at start, then come and periodically check if it fired.
        # if it did, fetch, do DF and re-arm
        self.time_domain_snap.fetch_signal(force)
        sig = self.time_domain_snap.signal
        self.time_domain_signals = [[], [], [], []]
        for start in range(len(sig)/(4*4)):
            for chan in range(self.num_channels):
                self.time_domain_signals[chan].append(sig[(4*(chan+(4*start)))+0])
                self.time_domain_signals[chan].append(sig[(4*(chan+(4*start)))+1])
                self.time_domain_signals[chan].append(sig[(4*(chan+(4*start)))+2])
                self.time_domain_signals[chan].append(sig[(4*(chan+(4*start)))+3])


    def fetch_crosses(self):
        """ Updates the snapshot blocks for all cross correlations
        """
        self.crosses = self.fetch_combinations(self.cross_combinations)

    def fetch_autos(self):
        """ Reads the snapshot blocks for all auto correlations and populates Correlation objects"""
        self.fetch_combinations(self.auto_combinations)

    def fetch_all(self):
        """ Popules both cross correlations and auto correlations.
        Returns Correlation objects for crosses and autos
        """
        self.fetch_combinations(self.cross_combinations + self.auto_combinations)

    def fetch_combinations(self, combinations):
        """ Takes an array of X correlations and returns the Correlation objects
        """
        self.control_register.block_trigger()
        for comb in combinations:
            self.arm_combination(comb)
        self.control_register.allow_trigger()
        for comb in combinations:
            self.frequency_correlations[comb].fetch_signal()
        if self.get_fft_overflow_state() == True:
            self.logger.critical("FFT has overflowed")
        self.control_register.pulse_overflow_rst()

    def do_time_domain_cross_correlation(self):
        # TODO: initiaise factor at initialisation from config.
        # TODO: min(length max, actual) should be used. Init from config.
        self.upsample_factor = 100
        self.subsignal_length_max = 2**17
        self.time_domain_padding = 10
        self.do_time_domain_cross_correlation_cross_first()

    def do_time_domain_cross_correlation_cross_first(self):
        self.time_domain_correlations = {}
        for (a_idx, b_idx) in self.cross_combinations:
            a = np.concatenate(
                (np.zeros(self.time_domain_padding),
                 self.time_domain_signals[a_idx][0:self.subsignal_length_max],
                 np.zeros(self.time_domain_padding)))
            a_time = np.linspace(-(self.time_domain_padding/self.fs), 
                                 (len(a)-self.time_domain_padding)/self.fs, 
                                 len(a),
                                 endpoint=False)
            b = self.time_domain_signals[b_idx][0:self.subsignal_length_max]
            b_time = np.linspace(0,
                                 len(b)/self.fs,
                                 len(b),
                                 endpoint=False)
            correlation = np.correlate(a, b, mode='valid')
            correlation_time = np.linspace(a_time[0] - b_time[0],
                                            a_time[-1] - b_time[-1],
                                            len(correlation),
                                            endpoint=True)
            correlation_upped, correlation_time_upped = scipy.signal.resample(
                correlation,
                len(correlation)*self.upsample_factor,
                t = correlation_time)
            self.time_domain_correlations[(a_idx, b_idx)] = correlation_upped
            self.time_domain_correlations_sample_times = correlation_time_upped
        # how much extra time we're appending each side
        #self.time_domain_correlation_time3 = np.linspace(-pt, pt, ((2*self.time_domain_padding)+1) * self.upsample_factor)
            # need to do something about the different length to compensate for
            # correct time stamp per sample. 
            # perhaps contact b with zeros and then remove them? While doing the same to
            # the 't' axis. Or just to 't'? 

    def do_time_domain_cross_correlation_resample_first(self):
        self.time_domain_correlations = []
        # fetch here maybe?
        for (a_idx, b_idx) in self.cross_combinations:
            a = np.concatenate(
                (np.zeros(self.time_domain_padding),
                 self.time_domain_signals[a_idx][0:self.subsignal_length_max],
                 np.zeros(self.time_domain_padding)))
            a_time = np.linspace(-(self.time_domain_padding/self.fs), 
                                 (len(a)-self.time_domain_padding)/self.fs, 
                                 len(a),
                                 endpoint=False)
            b = self.time_domain_signals[b_idx][0:self.subsignal_length_max]
            b_time = np.linspace(0,
                                 len(b)/self.fs,
                                 len(b),
                                 endpoint=False)
            assert(len(a) == ((len(b) + 2*self.time_domain_padding)))
            a_upped, a_time_upped = scipy.signal.resample(a, len(a)*self.upsample_factor, t = a_time)
            b_upped, b_time_upped = scipy.signal.resample(b, len(b)*self.upsample_factor, t = b_time)
            correlation = np.correlate(a_upped, b_upped, mode='valid')
            correlation_time = np.linspace(a_time_upped[0] - b_time_upped[0],
                                            a_time_upped[-1] - b_time_upped[-1],
                                            len(correlation),
                                            endpoint=True)
            print(len(correlation))
            return (correlation, correlation_time)

    def arm_combination(self, combination):
        """ Arms the snapshot block associated with the correlation combination
        """
        self.frequency_correlations[combination].arm()

    def set_accumulation_len(self, acc_len):
        """The number of vectors which should be accumulated before being snapped. 
        """
        self.fpga.write_int('acc_len', acc_len)
        self.logger.info("Accumulation length set to {l}".format(l = acc_len))
        self.re_sync()

    def set_shift_schedule(self, shift_schedule):
        """ Defines the FFT bit shift schedule
        """
        self.control_register.set_shift_schedule(shift_schedule)

    def re_sync(self):
        self.control_register.pulse_sync()

    def reset_accumulation_counter(self):
        self.control_register.reset_accumulation_counter()

    def get_fft_overflow_state(self):
        register = self.fpga.read_uint('fft_overflow')
        if register == 0:
            return False
        else:
            return True
