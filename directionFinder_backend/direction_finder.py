import logging
import numpy as np
import time

class DirectionFinder:
    def __init__(self, correlator, array, frequency, logger=logging.getLogger(__name__)):
        """ Takes data from a correlator and compares it to the expected output
        of the antenna array to figure out where the signal at the correlator 
        is coming from

        frequency -- the frequency bin to DF in Hz
        correlator -- instance of Correlator, or a fake correlator: Signal Generator.
        array -- instance of AntennaArray

        """
        self.logger = logger
        self.correlator = correlator
        self.array = array
        self.sampled_angles = np.linspace(-np.pi, np.pi, 1000)
        self.last_angle = self.sampled_angles[0]
        self.frequency_manifolds = {}
        self.set_frequency(frequency)

    def set_frequency(self, frequency):
        # assert that frequency is valid as per correlator specs here
        self.frequency = frequency
        if self.frequency not in self.frequency_manifolds:
            manifold = {}
            for angle in self.sampled_angles:
                manifold[angle] = self.array.each_pair_phase_difference_at_angle(angle, self.frequency)
            self.frequency_manifolds[self.frequency] = manifold
        self.manifold = self.frequency_manifolds[self.frequency]

    def set_time(self):
        """ Goes into time mode
        """
        self.manifold = {}
        for angle in self.sampled_angles:
            self.manifold[angle] = self.array.each_pair_time_difference_at_angle(angle)

    def find_closest_point(self, input_vector):
        closest_angle = self.last_angle - np.pi/6 # go back a bit from last time
        if closest_angle < self.sampled_angles[0]:
            closest_angle = self.sampled_angles[-int((self.sampled_angles[0] - closest_angle) / (self.sampled_angles[1] - self.sampled_angles[0]))]
        last_idx = np.searchsorted(self.sampled_angles, closest_angle)
        closest_angle = self.sampled_angles[last_idx]
        #closest_angle = self.manifold.keys()[0]
        closest_distance = self.distance_between_vectors(input_vector, self.manifold[closest_angle])  
        for angle_idx in range(last_idx,
                               last_idx + len(self.sampled_angles)):
            angle_idx = angle_idx % len(self.sampled_angles)
            angle = self.sampled_angles[angle_idx]
            manifold_vector = self.manifold[angle]
            new_distance = self.distance_between_vectors(input_vector, manifold_vector) 
            if new_distance < closest_distance:
                closest_distance = new_distance
                closest_angle = angle
        self.last_angle = closest_angle
        return closest_angle

    def distance_between_vectors(self, vec0, vec1):
        phase_differences = np.arctan2(
            np.sin(vec0 - vec1),
            np.cos(vec0 - vec1)
        )
        return np.linalg.norm(phase_differences)

    def fetch_frequency_crosses(self):
        self.correlator.fetch_crosses()

    def df_strongest_signal(self, f_start, f_stop, log_dir, t = time.time()):
        freq = self.correlator.frequency_correlations[(0,1)].strongest_frequency_in_range(f_start, f_stop)
        self.logger.info("Strongest signal in 0x1 correlation: {f} MHz.".format(f = freq/1e6))
        self.set_frequency(freq)
        visibilities = self.correlator.visibilities_at_frequency(freq)
        aoa = self.find_closest_point(visibilities)
        self.logger.info("AoA: {aoa}".format(aoa = aoa))
        with open('{d}/results.txt'.format(d = log_dir), 'a') as f:
            f.write("{t},{f},{aoa}\n".format(t = t, f = freq, aoa = aoa))

    def df_frequency(self):
        pass

    def fetch_impulse(self):
        return self.correlator.impulse_fetch()

    def df_impulse(self, log_dir, t = time.time()):
        self.correlator.do_time_domain_cross_correlation()
        visibilities = self.correlator.visibilities_from_time()
        aoa = self.find_closest_point(visibilities)
        self.logger.info("AoA: {aoa}".format(aoa = aoa))
        with open('{d}/results.txt'.format(d = log_dir), 'a') as f:
            f.write("{t},{aoa}\n".format(t = t, aoa = aoa))
