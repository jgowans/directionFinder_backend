
'''
#TODO: write doc string
'''

import numpy as np
from snapshot import Snapshot
import scipy.constants
import logging

class Correlation:
    def __init__(self, fpga, comb, f_start, f_stop, logger=logging.getLogger(__name__)):
        """ f_start and f_stop must be in Hz
        """
        self.logger = logger
        snap_name = "snap_{a}x{b}".format(a=comb[0], b=comb[1])
        self.snapshot0 = Snapshot(fpga,
                                 "{name}_0".format(name = snap_name),
                                 dtype='>i8',
                                 cvalue=True,
                                 logger=self.logger.getChild("{name}_0".format(name = snap_name)))
        self.snapshot1 = Snapshot(fpga,
                                 "{name}_1".format(name = snap_name),
                                 dtype='>i8',
                                 cvalue=True,
                                 logger=self.logger.getChild("{name}_1".format(name = snap_name)))
        self.f_start = np.uint64(f_start)
        self.f_stop = np.uint64(f_stop)
        # this will change from None to an array of phase offsets for each frequency bin 
        # if calibration gets applied at a later stage.
        # this is an array of phases introduced by the system. So if a value is positive, 
        # it means that the system is introducing a phase shift between comb[0] and comb[1]
        # in other words comb1 is artificially delayed. 
        self.calibration_phase_offsets = None
        self.calibration_cable_length_offsets = None
        self.fetch_signal()
        self.frequency_bins = np.linspace(
            start = self.f_start,
            stop = self.f_stop,
            num = len(self.signal),
            endpoint = False)

    def apply_frequency_bin_calibration(self, frequencies, phases):
        assert(len(frequencies) == len(phases))
        self.calibration_phase_offsets = np.ndarray(len(self.frequency_bins))
        for idx, f in enumerate(self.frequency_bins):
            # find index in of the frequency in frequencies which is losest to f
            frequencies_idx = np.argmin(np.abs(frequencies - f))
            print(frequencies_idx)
            self.calibration_phase_offsets[idx] = phases[frequencies_idx]
        self.logger.info("Applied calibration factors based on each frequency bin")

    def apply_cable_length_calibration(self, length_a, velocity_factor_a, length_b, velocity_factor_b):
        """ 'a' values are for comb[0]. 'b' values are for comb[1]
        TODO: remove what follows in docstring
        A positive number will produce a positive phase correlation factor. 
        This means that that a positive number implies that comb[1] is artificially delayed
        with respect to comb[0]. 
        This will happen if comb[1]s cable is longer than comb[0]s.
        Hence this should be len(cable1) - len(cable0)
        """
        self.calibration_cable_length_offsets = np.ndarray(len(self.frequency_bins))
        # calculate total time delay.
        t_a = length_a / (scipy.constants.c * velocity_factor_a)
        t_b = length_b / (scipy.constants.c * velocity_factor_b)
        # for each frequency bin, calculate corresponding 
        for idx, f in enumerate(self.frequency_bins):
            # this will produce a positive number if Bs length is longer than As
            # a positive phase means that A is ahead of B. Which is what would happen. 
            phase = 2*np.pi * (t_b - t_a) * f
            self.calibration_cable_length_offsets[idx] = phase
        self.logger.info("Applied calibration factors base on cable length")

    def arm(self):
        self.snapshot0.arm()
        self.snapshot1.arm()

    def apply_calibrations(self):
        self.logger.info("Before offsets: {s}".format( s = self.signal))
        if self.calibration_phase_offsets != None:
            offsets = np.exp(1j*self.calibration_phase_offsets)
            self.signal = self.signal * np.conj(offsets)
            self.logger.warn("Applied: {offsets}".format(offsets = offsets))
        if self.calibration_cable_length_offsets != None:
            offsets = np.exp(1j*self.calibration_cable_length_offsets)
            self.signal = self.signal * np.conj(offsets)
        self.logger.info("after offsets: {s}".format( s = self.signal))

    def fetch_signal(self):
        self.snapshot0.fetch_signal()
        self.snapshot1.fetch_signal()
        # F:  index the elements in column-major order, with the first index changing fastest
        self.signal = np.ravel( (self.snapshot0.signal, self.snapshot1.signal), order='F')
        self.apply_calibrations()

    def strongest_frequency(self):
        """ Returns the frequency in Hz which has the strongest signal.
        Frequency will be the centre of the bin.
        Excludes DC bin
        """
        # add 1 because we're excluding the initial bin
        bin_number = np.argmax(np.abs(self.signal[1:])) + 1
        return self.frequency_bins[bin_number]

    def phase_at_freq(self, f):
        """ Note: this formula may need fixing!! Check against actual data
        """
        bin_width = self.frequency_bins[1] - self.frequency_bins[0]
        bin_number = int(round((f - self.f_start) / bin_width))
        bin_contents = self.signal[bin_number]
        phase = np.angle(bin_contents)
        return phase
