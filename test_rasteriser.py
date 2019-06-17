#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test bed for rasteriser and fishnet generator functionality

Created on Thu Jun  6 12:17:17 2019

@author: ndh114
"""

import unittest
import logging
import sys
sys.path.append('..')

from classes import Config, FishNet, Rasteriser

logging.basicConfig(
    level=Config.get('LOG_LEVEL'),
    format=Config.get('LOG_FORMAT'),
    datefmt=Config.get('LOG_DATE_FORMAT'),
    filename=Config.get('LOG_FILE'),
    filemode='w')

LOGGER = logging.getLogger('test_rasteriser.py')

FishNet(outfile='test_fishnet.json', outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()

if __name__ == '__main__':
    unittest.main()