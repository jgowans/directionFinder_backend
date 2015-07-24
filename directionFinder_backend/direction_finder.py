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
        self.set_frequency(frequency)
        self.generate_manifold()

    def set_frequency(self, frequency):
        # assert that frequency is valid as per correlator specs here
        self._frequency = frequency

    def generate_manifold(self):
        self.manifold = {}
        for angle in np.linspace(0, np.pi*2, 1000):
            manifold[angle] = self.array.each_pair_phase_difference_at_angle(angle, self.frequency)
        # TODO: later, run this through a Calibration class which applies offsets
        # to the phase values such that the simulated phase mirrors the actual phase
        # differences. 

    def find_closest_point(self, input_vector):
        closest_angle = self.manifold.keys()[0] # get a 'random' angle
        cosest_distance = self.distance_between_vectors(input_vector, self.manifold.[closest_angle])  
        for angle, manifold_vector in self.manifold.items():
            new_distance = self.distance_between_vectors(input_vector, manifold_vector) 
            if new_distane < closest_distance:
                closest_distance = new_distance
                closest_angle = angle
        return closest_angle

    def distance_between_vectors(self, vec0, vec1):
        phase_differences = np.arctan2(
            np.sin(vec0 - vec1),
            np.cos(vec0 - vec1)
        )
        return np.linalg.norm(phase_differences)

    def self.direction_find(self):
        self.correlator.fetch_crosses()
        input_vector = self.correlator.
        # get data from correlator (sit in loop until data available)
        # iterate through manifold and find nearest point
