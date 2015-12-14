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

