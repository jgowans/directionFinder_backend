"""
An interface to the snapshot blocks with some data analysis
functions on the data received
"""

import numpy as np
import logging
import time

class Snapshot:
    def __init__(self, fpga, name, dtype, cvalue, logger=logging.getLogger(__name__)):
        """
        fpga -- instance of corr.katcp_wrapper.FpgaClient
        name -- snap block name in the design
        dtype -- data type of each sample in the snapshot
        cvalue -- True if snapshot should be interpreted as packed array
            of complex values
        """
        self.logger = logger
        self.fpga = fpga
        self.name = name
        self.dtype = dtype
        self.cvalue = cvalue

    def unpack_signal(self, raw):
        components = np.frombuffer(raw, self.dtype)
        if self.cvalue == True:  # we need to convert to array of complex floats
            components = components.astype(np.float64)  # convert each element from int to floats
            components.dtype = np.complex128  # now view as complex pairs of 2x 64bit floats
        return components

    def arm(self):
        self.fpga.snapshot_arm(self.name)
        self.logger.debug("Armed snapshot: {n}".format(n = self.name))

    def fetch_signal(self, force=False):
        """ Returns an numpy array object containing the samples from the snap block
        interpreted as per #dtype and #cvalue
        'force' will get the whole snap if DRAM or will force capture on a BRAM snap
        """
        if self.name == 'dram_snapshot':
            if force == True:
                # maximum of 2**21 bytes or 2**19 per channel
                self.fpga.snapshot_arm(self.name, man_valid=True, man_trig=True)
                time.sleep(0.1)
                raw = self.fpga.read_dram(2**21)
            else:
                pre_delay = 256 * 4
                impulse_len = self.fpga.read_uint('impulse_len') * 4
                # equal delay on either side of signal
                to_fetch = predelay + impulse_len + pre_delay
                # maximum of 2**21 bytes or 2**19 per channel
                to_fetch = min(2**21, to_fetch)
                raw = self.fpga.read_dram(to_fetch)
        else:
            raw = self.fpga.snapshot_get(self.name, man_valid=force, man_trig=force, wait_period=12, arm=force)['data']
        self.signal = self.unpack_signal(raw)
        self.logger.debug("A signal of length {l} was read".format(
            n = self.name, l = len(self.signal)))
