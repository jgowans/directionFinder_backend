import logging
import numpy as np

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
        self.manifolds = {}
        self.set_frequency(frequency)

    def set_frequency(self, frequency):
        # assert that frequency is valid as per correlator specs here
        self.frequency = frequency
        self.generate_manifold()
        self.manifold = self.manifolds[self.frequency]

    def generate_manifold(self):
        if self.frequency not in self.manifolds:
            manifold = {}
            for angle in self.sampled_angles:
                manifold[angle] = self.array.each_pair_phase_difference_at_angle(angle, self.frequency)
            self.manifolds[self.frequency] = manifold
        # TODO: later, run this through a Calibration class which applies offsets
        # to the phase values such that the simulated phase mirrors the actual phase
        # differences. 

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

    def df_strongest_signal(self, f_start, f_stop):
        self.correlator.fetch_crosses()
        f = self.correlator.frequency_correlations[(0,1)].strongest_freq_in_range(f_start, f_stop)
        self.set_frequency(f)

    def df_frequency(self):
        pass
