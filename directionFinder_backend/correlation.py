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
        print("index of max: {i} / {l}".format(i = bin_number, l = len(self.signal)))
        #print("phase of max: {ph}".format(ph = np.angle(self.signal[bin_number])))
        bin_width = (self.f_stop - self.f_start) / len(self.signal)
        return self.f_start + (bin_width * bin_number)

    def phase_at_freq(self, f):
        """ Note: this formula may need fixing!! Check against actual data
        """
        bin_width = (self.f_stop - self.f_start) / len(self.signal)
        bin_number = int(round((f - self.f_start) / bin_width))
        print("bin accessed: {i}".format(i = bin_number))
        value = self.signal[bin_number]
        return np.angle(value)


