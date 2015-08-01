import logging

'''
#TODO: write doc string
'''

import numpy as np
from snapshot import Snapshot

class Correlation:
    def __init__(self, fpga, comb, f_start, f_stop, logger=logging.getLogger(__name__)):
        self.logger = logger
        snap_name = "snap_{a}x{b}".format(a=comb[0], b=comb[1])
        self.snapshot = Snapshot(fpga,
                                 snap_name,
                                 dtype='>i4',
                                 cvalue=True,
                                 logger=self.logger.getChild(snap_name))
        self.f_start = f_start
        self.f_stop = f_stop

    def arm(self):
        self.snapshot.arm()

    def fetch_signal(self, force=False):
        self.snapshot.fetch_signal(force)

    def phase_at_freq(self, f):
        """ Note: this formula may need fixing!! Check against actual data
        """
        fft_bin_number = int(round(
            f-self.f_start * (self.f_stop - self.f_start) / (len(self.signal))
        ))
        fft_bin = self.snapshot.signal[fft_bin_number]
        return np.phase(fft_bin)


