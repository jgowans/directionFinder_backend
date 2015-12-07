#!/usr/bin/env python

import unittest
import numpy as np
import sys
sys.path.append('..')
import antenna_array

class AntennaArrayTester(unittest.TestCase):
    def setUp(self):
        self.ant_array = antenna_array.AntennaArray(5.6) # spacing of 5.6 wavelengths apart. 

    def test_antenna_count(self):
        self.assertEqual(len(self.ant_array), 4)

    def test_phase_no_rotation:
        pass
