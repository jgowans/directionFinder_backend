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
        self.correlations = {}
        for comb in (self.cross_combinations + self.auto_combinations):
            self.correlations[comb] = Correlation(comb, self.fpga)
            self.correlations[comb].fetch_signal(force=True)  # ensure populated with some data
        self.control_register = ControlRegister(self.fpga, self.logger.getChild('control_reg'))

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
        self.control_reg.block_trigger()
        for comb in combinations:
            self.arm_combination(comb)
        self.control_reg.allow_trigger()
        for comb in combinations:
            self.correlations[comb].fetch_signal()

    def arm_combination(self, combination):
        """ Arms the snapshot block associated with the correlation combination
        """
        self.correlations[combination].arm()

    def set_accumulation_len(self, acc_len):
        """The number of vectors which should be accumulated before being snapped. 
        """
        self.fpga.write_int('acc_len', acc_len)
        self.logger.info("Accumulation length set to {l}".format(l = acc_len))
        self.re_sync()

    def set_shift_schedule(self, shift_schedule):
        """ Defines the FFT bit shift schedule
        """
        self.control_reg.set_shift_schedule(shift_schedule)

    def re_sync(self):
        self.control_reg.pulse_sync()

    def reset_accumulation_counter(self):
        self.control_reg.reset_accumulation_counter()

