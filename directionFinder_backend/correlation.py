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
        self.snapshot = Snapshot(fpga,
                                 snap_name,
                                 dtype='>i4',
                                 cvalue=True,
                                 logger=self.logger.getChild(snap_name))
        self.f_start = np.uint64(f_start)
        self.f_stop = np.uint64(f_stop)

    def arm(self):
        self.snapshot.arm()

    def fetch_signal(self, force=False):
        self.snapshot.fetch_signal(force)

    def strongest_frequency(self):
        """ Returns the frequency in Hz which has the strongest signal.
        Frequency will be the centre of the bin.
        Excludes DC bin
        """
        # add 1 because we're excluding the initial bin
        bin_number = np.argmax(np.abs(self.snapshot.signal[1:-1])) + 1
        print("index of max: {i}".format(i = bin_number))
        bin_width = (self.f_stop - self.f_start) / len(self.snapshot.signal)
        # start of bin is bin_number * width. Centre is half a bin further
        return bin_width * (bin_number + 0.5) 

    def phase_at_freq(self, f):
        """ Note: this formula may need fixing!! Check against actual data
        """
        fft_bin_number = f-self.f_start * (self.f_stop - self.f_start) / (len(self.snapshot.signal))
        print("bin accessed: {i}".format(i = fft_bin_number))
        fft_bin_number = int(round(fft_bin_number))
        fft_bin = self.snapshot.signal[fft_bin_number]
        return np.phase(fft_bin)


