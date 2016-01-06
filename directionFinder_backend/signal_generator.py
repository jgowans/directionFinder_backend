""" Attempts to simulate a system consisting of a tone being received by
multiple phase-shifted and amplitude scaled sensors with uncorrelated noise
at each
"""

import numpy as np
import logging
import itertools
from directionFinder_backend.signal_generator_correlation import SignalGeneratorCorrelation

class SignalGenerator:
    def __init__(self, num_channels=4, tone_freq=0.2, snr=0.1,
                 phase_shifts=np.zeros(4), amplitude_scales=np.ones(4),
                 adc_bits=8, samples=2048,
                 fft_bits = 18,
                 impulse_length = 1000, impulse_snr = 1,
                 impulse_offsets = np.zeros(4),
                 logger = logging.getLogger(__name__)):
        """ Creates a signal generator instance
        
        Parameters:
        num_channels -- how many independant sensors should be simulated.
        tone_freq -- the frequency of the signal as a fraction of sample frequency.
                0.5 = nyquist. 1 = alias for 0
        SNR -- signal to noise ratio in linear power terms. Must be <= 1.
        phase_shifts -- array of phase shifts to apply to each channel in radians
        amplitude_scales -- array of amplitude scalings to apply to each channel
            #TODO: Is this a voltage or power scale???
        bits -- when quantising time domain signal, how many bits to quantise to.
        samples -- when generating vectors, how many samples per channel.
        fft_bits -- when quantising output of FFT, how many bits to quantise to.
        """
        self.logger = logger
        self.num_channels = num_channels
        self.tone_freq = tone_freq
        self.snr = snr
        self.phase_shifts = phase_shifts
        self.amplitude_scales = amplitude_scales
        self.adc_bits = adc_bits
        self.samples = samples
        self.fft_bits = fft_bits
        self.impulse_length = impulse_length
        self.impulse_snr = impulse_snr
        assert(snr <= 1)
        assert(phase_shifts.size == num_channels)
        assert(amplitude_scales.size == num_channels)
        self.noise_stddev = 1.0/3

        self.cross_combinations = list(itertools.combinations(range(num_channels), 2))  # [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        self.auto_combinations = [(0, 0)]
        self.frequency_correlations = {}
        for comb in self.cross_combinations:
            self.frequency_correlations[comb] = SignalGeneratorCorrelation(
                comb,
                0,
                0.5,
                self.logger.getChild("{a}x{b}".format(a = comb[0], b = comb[1])))

    def fetch_crosses(self):
        spectrums = self.generate_quantised_spectrums()
        for a, b in self.cross_combinations:
            cross = spectrums[a] * np.conj(spectrums[b])
            self.frequency_correlations[(a, b)].update(cross)

    def set_impulse_len(self, length):
        self.impulse_length = length

    def set_impulse_snr(self, snr):
        self.impulse_snr = snr

    def impulse_arm(self):
        pass
    def impulse_fetch(self):
        pre_delay = 256 * 4
        impulse = np.concatenate((
            np.zeros(pre_delay),
            np.random.normal(loc = 0,
                             scale = self.noise_stddev * 127 * self.impulse_snr,
                             size = self.impulse_length),
            np.zeros(pre_delay)
        ))
        impulse.clip(-128, 127)
        impulse = impulse.astype(np.int8)
        self.time_domain_signals = np.ndarray((self.num_channels, 
                                               len(impulse)),
                                               dtype = np.int8)
        for chan in range(self.num_channels):
            noise = np.random.normal(loc = 0, 
                                     scale = self.noise_stddev * 127,
                                     size = len(impulse))
            noise = noise.clip(-128, 127)
            noise = noise.astype(np.int8)
            self.time_domain_signals[chan] = noise
            self.time_domain_signals[chan] += impulse



    def generate(self):
        signals = np.ndarray((self.num_channels, self.samples))
        for channel in range(self.num_channels):
            signals[channel] = self.generate_tone(channel)
            signals[channel] += self.generate_noise()
        return signals

    def generate_tone(self, channel):
        x = np.linspace(start = self.phase_shifts[channel],
                        stop = self.phase_shifts[channel] + (2*np.pi * self.tone_freq * self.samples),
                        num = self.samples,
                        endpoint=False)
        # For a sine wave: P = A^2 / 2. This must be divided by N as the FFT acts
        # to multiply the power of a bin by N. 
        # We want the power in the FFT bin to be P.
        power = ((self.noise_stddev**2) * self.snr) / self.samples
        amplitude = np.sqrt(2*power)
        return (self.amplitude_scales[channel] * amplitude) * np.sin(x)

    def generate_noise(self):
        return np.random.normal(0, self.noise_stddev, self.samples)

    def quantise(self, signal):
        """ Quantising process is:
        - we assume the input signal is [-1 ; +1]
        - scale up to the number of bits we have.
        - round. 
        - clip
        - scale back down to be [-1 ; +1]
        """
        scale_factor = float(1 << (self.adc_bits-1)) # -1 because positive and negative half
        clip_min = -scale_factor
        clip_max = scale_factor
        signal *= scale_factor
        signal = signal.round()
        signal /= scale_factor
        signal = signal.clip(-1, 1)
        return signal

    def generate_quantised(self):
        signals = self.generate()
        signals = self.quantise(signals)
        return signals

    def quantise_spectrum(self, signal):
        # explanation:
        # assuming power distributed evently over spectrum, the amplitude of 
        # a bin is sqrt(variance * N). We want to normalise this to 1.
        # However, power is not evenly distributed, so we give a factor of 4
        # hear room
        normalise_factor = (np.sqrt(self.samples * (self.noise_stddev**2))) * 3
        signal /= normalise_factor  # all bin's power should now be below 1
        upscale_factor = float(1 << (self.fft_bits-1))
        signal *= upscale_factor
        signal = signal.round()
        signal /= upscale_factor
        # would like to clip here, but clipping complex will screw with zero the imaginary part if real is out of range
        #signal = signal.clip(-1, 1)
        return signal

    def generate_quantised_spectrums(self):
        signals = self.generate_quantised()
        spectrums = np.fft.rfft(signals)
        #spectrums = self.quantise_spectrum(spectrums)
        return spectrums
