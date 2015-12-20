import logging

'''
#TODO: write doc string
'''

import numpy as np
from snapshot import Snapshot

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
        self.fetch_signal()
        self.frequency_bins = np.linspace(
            start = self.f_start,
            stop = self.f_stop,
            num = len(self.signal),
            endpoint = False)

    def arm(self):
        self.snapshot0.arm()
        self.snapshot1.arm()

    def fetch_signal(self):
        self.snapshot0.fetch_signal()
        self.snapshot1.fetch_signal()
        # F:  index the elements in column-major order, with the first index changing fastest
        self.signal = np.ravel( (self.snapshot0.signal, self.snapshot1.signal), order='F')

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
        return np.angle(bin_contents)


