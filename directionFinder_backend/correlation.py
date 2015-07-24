import logging

'''
#TODO: write doc string
'''

import numpy as np
from snapshot import Snapshot

class Correlation:
    def __init__(self, f_start, f_stop, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.correlations = {}
        self.f_start = f_start
        self.f_stop = f_stop

    def update(self, comb, signal):
        self.correlations[comb] = signal

    def phase_difference_at_freq(self, to_compare, f):
        total = 0
        for corr0_comb, corr0_sig in corr0.items():


