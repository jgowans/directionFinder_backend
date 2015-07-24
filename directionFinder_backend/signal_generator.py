""" Attempts to simulate a system consisting of a tone being received by
multiple phase-shifted and amplitude scaled sensors with uncorrelated noise
at each
"""

import numpy as np

class SignalGenerator:
    def __init__(self, num_channels=4, tone_freq=0.2, snr=0.1,
                 phase_shift=np.zeros(4), amplitude_scale=np.ones(4),
                 bits=8, samples=2048,
                 fft_bits = 18):
        """ Creates a signal generator instance
        
        Parameters:
        num_channels -- how many independant sensors should be simulated.
        tone_freq -- the frequency of the signal as a fraction of sample frequency.
                0.5 = nyquist. 1 = alias for 0
        SNR -- signal to noise ratio in linear power terms. Must be <= 1.
        phase_shift -- array of phase shifts to apply to each channel in radians
        amplitude_scale -- array of amplitude scalings to apply to each channel
            #TODO: Is this a voltage or power scale???
        bits -- when quantising time domain signal, how many bits to quantise to.
        samples -- when generating vectors, how many samples per channel.
        fft_bits -- when quantising output of FFT, how many bits to quantise to.
        """
        self.num_channels = num_channels
        self.tone_freq = tone_freq
        self.snr = float(snr)
        self.phase_shift = phase_shift
        self.amplitude_scale = amplitude_scale
        self.bits = int(bits)
        self.samples = int(samples)
        self.fft_bits = int(fft_bits)
        assert(snr <= 1)
        assert(phase_shift.size == num_channels)
        assert(amplitude_scale.size == num_channels)
        self.noise_stddev = 1.0/3

    def generate(self):
        signals = np.ndarray((self.num_channels, self.samples))
        for channel in range(self.num_channels):
            signals[channel] = self.generate_tone(channel)
            signals[channel] += self.generate_noise()
        return signals

    def generate_tone(self, channel):
        x = np.linspace(start = self.phase_shift[channel],
                        stop = self.phase_shift[channel] + (2*np.pi * self.tone_freq * self.samples),
                        num = self.samples,
                        endpoint=False)
        # For a sine wave: P = A^2 / 2. This must be divided by N as the FFT acts
        # to multiply the power of a bin by N. 
        # We want the power in the FFT bin to be P.
        power = ((self.noise_stddev**2) * self.snr) / self.samples
        amplitude = np.sqrt(2*power)
        return (self.amplitude_scale[channel] * amplitude) * np.sin(x)

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
        scale_factor = float(1 << (self.bits-1)) # -1 because positive and negative half
        clip_min = -scale_factor
        clip_max = scale_factor
        signal *= scale_factor
        signal = signal.round()
        signal /= scale_factor
        signal = signal.clip(-1, 1)
        return signal

    def generate_quantised(self):
        signal = self.generate()
        signal = self.quantise(signal)
        return signal

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
        signal = signal.clip(-1, 1)
        return signal

    def generate_quantised_spectrum(self):
        signal = self.generate_quantised()
        spectrum = np.fft.rfft(signal)
        spectrum = self.quantise_spectrum(spectrum)
        return spectrum
