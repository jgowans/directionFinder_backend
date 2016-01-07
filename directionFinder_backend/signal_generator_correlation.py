import logging
import numpy as np

class SignalGeneratorCorrelation:
    def __init__(self, comb, f_start, f_stop, logger = logging.getLogger(__name__)):
        self.comb = comb
        self.f_start = f_start
        self.f_stop = f_stop
        self.logger = logger

    def update(self, signal):
        self.signal = signal

    def bin_at_freq(self, f):
        frequency_bins = np.linspace(
            start = self.f_start,
            stop = self.f_stop,
            num = len(self.signal),
            endpoint = True)  # this is different to the real ROACH FFT: it provides the endpoint
        bin_width = frequency_bins[1] - frequency_bins[0]
        bin_number = int(round((f - self.f_start) / bin_width))
        bin_contents = self.signal[bin_number]
        return bin_contents
