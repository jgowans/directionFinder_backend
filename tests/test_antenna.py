#!/usr/bin/env python

import unittest
import numpy as np
import sys
from directionFinder_backend import antenna

class AntennaTester(unittest.TestCase):
    def setUp(self):
        self.antenna = antenna.Antenna(12.34, 23.45) # x,y coordinates

    def test_coordinates(self):
        self.assertAlmostEqual(self.antenna.x, 12.34)
        self.assertAlmostEqual(self.antenna.y, 23.45)

    def test_rotated_pi(self):
        rotated = self.antenna.rotated(np.pi)
        self.assertAlmostEqual(rotated.x, -12.34)
        self.assertAlmostEqual(rotated.y, -23.45)

    def test_rotated_3_2_pi(self):
        rotated = self.antenna.rotated(3*np.pi/2)
        self.assertAlmostEqual(rotated.x, 23.45)
        self.assertAlmostEqual(rotated.y, -12.34)

    def test_phase_no_rotate(self):
        # http://www.wolframalpha.com/input/?i=angle%28e^%28i*12.34%29%29
        self.assertAlmostEqual(self.antenna.phase_at_angle(0), -0.22637061)

    def test_phase_rotated(self):
        """ Roatated by 2 radians. Rotation means counter clockwise, yes?
        http://www.wolframalpha.com/input/?i=arg%28e^%28i*Re%28%2812.34%2B23.45i%29*e^%282i%29%29%29%29
        """
        self.assertAlmostEqual(self.antenna.phase_at_angle(2), -1.32553539)

