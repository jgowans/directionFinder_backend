import numpy as np
import scipy.constants

class Antenna:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.location = np.array([
            [x],
            [y]
        ])

    def rotated(self, phi):
        rotation_matrix = np.array([
                [np.cos(phi), -np.sin(phi)],
                [np.sin(phi), np.cos(phi)]
        ])
        new_location = rotation_matrix.dot(self.location)
        return Antenna(new_location[0,0], new_location[1,0])

    def rotated_distance(self, phi):
        return self.rotated(phi).x

    def phase_at_angle(self, phi, f, c=scipy.constants.c):
        new_distance = self.rotated_distance(phi)
        new_phase = new_distance * (f/c) * 2*np.pi
        # force phase to range from -pi to pi. I sort of know how this works...
        normalised_phase = np.arctan2(np.sin(new_phase), np.cos(new_phase))
        return normalised_phase
