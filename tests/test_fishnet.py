#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test bed for fishnet generator

Created on Thu Jun  6 12:17:17 2019

@author: ndh114
"""

import logging
import sys
sys.path.append('..')

from classes import Config, FishNet

logging.basicConfig(
    level=Config.get('LOG_LEVEL'),
    format=Config.get('LOG_FORMAT'),
    datefmt=Config.get('LOG_DATE_FORMAT'),
    filename=Config.get('LOG_FILE'),
    filemode='w')

FishNet(outfile='test_fishnet.json', outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()

# Then check in QGIS that we have something like what we want...