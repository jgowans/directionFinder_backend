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
import scipy.signal, scipy.constants
import time
import json
import os


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
        self.control_register = ControlRegister(self.fpga, self.logger.getChild('control_reg'))
        self.set_accumulation_len(100)
        self.re_sync()
        self.control_register.allow_trigger() # necessary as Correlations auto fetch signal
        # only 0x0 has been implemented
        #self.auto_combinations = [(x, x) for x in range(num_channels)] # [(0, 0), (1, 1), (2, 2), (3, 3)]
        self.auto_combinations = [(0, 0)]
        self.frequency_correlations = {}
        for comb in (self.cross_combinations + self.auto_combinations):
            self.frequency_correlations[comb] = Correlation(fpga = self.fpga,
                                                  comb = comb,
                                                  f_start = 0,
                                                  f_stop = fs/2,
                                                  logger = self.logger.getChild("{a}x{b}".format(a = comb[0], b = comb[1])) )
        self.time_domain_snap = Snapshot(fpga = self.fpga, 
                                         name = 'dram_snapshot',
                                         dtype = np.int8,
                                         cvalue = False,
                                         logger = self.logger.getChild('time_domain_snap'))
        self.upsample_factor = 100
        self.subsignal_length_max = 2**17
        self.time_domain_padding = 100
        self.time_domain_calibration_values = None
        self.time_domain_calibration_cable_values = None
        self.control_register.block_trigger()

    def impulse_arm(self):
        self.control_register.pulse_impulse_arm()
        self.time_domain_snap.arm()

    def impulse_fetch(self):
        """ Will fetch and re-arm if an impulse has occurred.
        Will do nothing if no impulse. 
        Return True if fetched (ie: an impulse happened) or
        False if not
        """
        pre_delay = 256 * 4
        impulse_len = self.fpga.read_uint('impulse_length')
        if impulse_len != 0:
            self.logger.info("Got an impulse of length: {}".format(impulse_len))
            time.sleep(0.1)
            if self.fpga.read_uint('impulse_length') != impulse_len:
                self.logger.warning('Impulse has gone on for too long. Adjust setpoint?')
            self.fetch_time_domain_snapshot()
            self.impulse_arm()
            return True
        return False

    def set_impulse_setpoint(self, level):
        self.fpga.write_int('setppoint', level)
        self.logger.info("Impulse detection setpoint changed to: {}".format(level))

    def get_current_impulse_level(self):
        level = self.fpga.read_uint('current_impulse_level')
        self.logger.debug("Current impulse level: {}".format(level))
        return level

    def set_impulse_filter_len(self, length):
        assert(length > 5)
        assert(length < 1000)
        self.fpga.write_int('impulse_filter_len', length)
        self.logger.info("Impulse filter length set to: {}".format(length))

    def fetch_time_domain_snapshot(self, force=False):
        self.time_domain_snap.fetch_signal(force)
        sig = self.time_domain_snap.signal
        # shorten to fit exactly 
        new_length = (4 * self.num_channels) * np.floor(len(sig) / (4 * self.num_channels))
        sig = sig[0:new_length]
        self.time_domain_signals = np.ndarray((self.num_channels, len(sig)/self.num_channels), 
                                              dtype = np.float64)
        sig = sig.reshape(len(sig)/self.num_channels, self.num_channels)
        for chan in range(self.num_channels):
            self.time_domain_signals[chan] = sig[chan::self.num_channels].flatten().astype(np.float64)
            # remove DC offset
            mean = np.mean(self.time_domain_signals[chan])
            self.time_domain_signals[chan] -= mean
            self.logger.info("After: DC offset for {chan} = {offset}".format(
                chan = chan, 
                offset = np.mean(self.time_domain_signals[chan])))


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
        self.get_overflow_state()

    def visibilities_at_frequency(self, f):
        visibilities = np.ndarray(len(self.cross_combinations))
        for idx, comb in enumerate(self.cross_combinations):
            visibilities[idx] = self.frequency_correlations[comb].phase_at_freq(f)
        return visibilities

    def save_frequency_correlations(self, path):
        full_dir = "{base}/{sub}/".format(base = path, sub = time.time())
        os.mkdir(full_dir)
        for comb in self.cross_combinations:
            filename = "{path}/{a}x{b}".format(path = full_dir, a = comb[0], b = comb[1])
            np.save(filename, self.frequency_correlations[comb].signal)
        self.logger.debug("Saved frequency combinations to {d}".format(d = full_dir))

    def save_time_raw(self, path):
        full_dir = "{base}/{sub}/".format(base = path, sub = time.time())
        os.mkdir(full_dir)
        for chan in range(self.num_channels):
            filename = "{path}/{a}x{b}".format(path = full_dir, a = comb[0], b = comb[1])
            sig = self.time_domain_signals[chan]
            np.save(filename, sig)
        self.logger.debug("Saved time domain raw to {d}".format(d = full_dir))

    def do_time_domain_cross_correlation(self):
        # TODO: initiaise factor at initialisation from config.
        # TODO: min(length max, actual) should be used. Init from config.
        self.do_time_domain_cross_correlations_cross_first()
        self.time_domain_cross_correlations_peaks = {}
        for baseline in self.cross_combinations:
            self.time_domain_cross_correlations_peaks[baseline] = \
                self.time_domain_correlations_times[baseline][np.argmax(self.time_domain_correlations_values[baseline])]

    def visibilities_from_time(self):
        visibilities = np.ndarray(len(self.cross_combinations))
        for idx, baseline in enumerate(self.cross_combinations):
            visibilities[idx] = self.time_domain_cross_correlations_peaks[baseline]
        return visibilities

    def do_time_domain_cross_correlations_cross_first(self):
        self.time_domain_correlations_values = {}
        self.time_domain_correlations_times = {}
        for (a_idx, b_idx) in self.cross_combinations:
            # NOTE: The only reason this works is that the dtype of the zeros is 
            # float64 hence 'a' and 'b' are also float64. The signals get cast 
            # to float64.
            # if they stayed as int8 the correlation would fail miserably.
            # investivate time impact of converting to float64 vs int32 vs int64
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
            self.time_domain_correlations_values[(a_idx, b_idx)] = correlation_upped
            if self.time_domain_calibration_values != None:
                correlation_time_upped -= self.time_domain_calibration_values[(a_idx, b_idx)]
            if self.time_domain_calibration_cable_values != None:
                #TODO : Should it be add or subtract??
                correlation_time_upped -= self.time_domain_calibration_cable_values[(a_idx, b_idx)]
            self.time_domain_correlations_times[(a_idx, b_idx)] = correlation_time_upped
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

    # change this to 'get overflow states'
    # which reads and clears all overflow flags and returns a
    # hash of whether or not the various flags have been set.
    def get_overflow_state(self):
        status = self.fpga.read_uint('status')
        overflows = {
            'adc': False,
            'acc': False,
            'fft': False,
        }
        if (status & 1 << 0) != 0:
            overflows['adc'] = True
            self.logger.critical("An ADC has clipped")
        if (status & 1 << 1) != 0:
            overflows['acc'] = True
            self.logger.critical("The accumulator has overflowed")
        if (status & 1 << 2) != 0:
            overflows['fft'] = True
            self.logger.critical("The FFT has overflowed")
        self.control_register.pulse_overflow_rst()
        return overflows


    def apply_time_domain_calibration(self, filename):
        self.time_domain_calibration_values = {}
        with open(filename) as f:
            offsets = json.load(f)
        for a, b in self.cross_combinations:
            comb_str = "{a}x{b}".format(a = a, b = b)
            self.time_domain_calibration_values[(a, b)] = offsets[comb_str]

    def apply_frequency_bin_calibrations(self, filename):
        with open(filename) as f:
            offsets = json.load(f)
        frequencies = offsets['axis']
        for a, b in self.cross_combinations:
            self.frequency_correlations[(a, b)].apply_frequency_bin_calibration(
                frequencies = frequencies,
                phases = offsets["{a}{b}".format(a = a, b = b)])

    def apply_cable_length_calibrations(self, filename):
        """ Filename should be a json file with cable lengths
        for each antenna and velocity factors
        {
          "0": {
              "length": 0.5,
              "velocity factor": 0.66
          },
        """
        with open(filename) as f:
            cables = json.load(f)
        self.time_domain_calibration_cable_values = {}
        for a, b in self.cross_combinations:
            length_a = cables[str(a)]['length']
            velocity_factor_a = cables[str(a)]['velocity factor']
            length_b = cables[str(b)]['length']
            velocity_factor_b = cables[str(b)]['velocity factor']
            # For the frequency domain:
            self.frequency_correlations[(a, b)].apply_cable_length_calibration(
                length_a = length_a,
                velocity_factor_a = velocity_factor_a,
                length_b = length_b,
                velocity_factor_b = velocity_factor_b)
            # For the time domain:
            t_a = length_a / (scipy.constants.c * velocity_factor_a)
            t_b = length_b / (scipy.constants.c * velocity_factor_b)
            # this is how much a is delayed from b by as a result of the cable.
            # a delayed from b by a positive amount will mean that the correlation
            # peak will be positive. Subtract this to compensate.
            self.time_domain_calibration_cable_values[(a, b)] = t_a - t_b
