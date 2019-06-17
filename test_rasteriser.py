#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test bed for rasteriser and fishnet generator functionality

Created on Thu Jun  6 12:17:17 2019

@author: ndh114
"""

from os import remove, path
import uuid
import unittest
import logging
import geopandas

from classes import Config, FishNet, Rasteriser

class TestFishNet(unittest.TestCase):    

    def setUp(self):
        logging.basicConfig(
            level=Config.get('LOG_LEVEL'),
            format=Config.get('LOG_FORMAT'),
            datefmt=Config.get('LOG_DATE_FORMAT'),
            filename=Config.get('LOG_FILE'),
            filemode='w')

        self.logger = logging.getLogger('TestFishNet')
    
    def test_fishnet_bbox(self):
        """
        Tests fishnet generation with a bounding box
        """
        self.logger.info('Fishnet with bounding box...')
        output_file = '{}.json'.format(uuid.uuid4().hex)
        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
        FishNet(outfile=output_file, outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()
        self.assertTrue(path.exists(output_path))
        self.assertTrue(path.getsize(output_path) > 0)
        remove(output_path)
        self.logger.info('Completed')
        
    def test_fishnet_area_codes(self):
        """
        Tests fishnet generation with a list of area codes
        """
        self.logger.info('Fishnet with list of area codes...')
        output_file = '{}.json'.format(uuid.uuid4().hex)
        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
        FishNet(outfile=output_file, outformat='GeoJSON', lad=['E07000004']).create()
        self.assertTrue(path.exists(output_path))
        self.assertTrue(path.getsize(output_path) > 0)
        remove(output_path)
        self.logger.info('Completed')
        
    def test_fishnet_geojson_string_return(self):
        """
        Tests fishnet generation with a GeoJSON string return
        """
        self.logger.info('Fishnet with GeoJSON string return...')
        geojson = FishNet(outfile=None, outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()
        self.assertFalse(geojson is None)
        try:
            geopandas.GeoDataFrame(geojson)
        except ValueError:
            self.fail('Returned GeoJSON could not be read into a GeoDataFrame')
        self.logger.info('Completed')

    def test_fishnet_shapefile(self):
        """
        Tests fishnet generation with a shapefile output
        """
        self.logger.info('Fishnet with ESRI shapefile output...')
        output_file = '{}.shp'.format(uuid.uuid4().hex)
        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
        FishNet(outfile=output_file, outformat='ESRI Shapefile', lad=['E07000004']).create()
        self.assertTrue(path.exists(output_path))
        self.assertTrue(path.getsize(output_path) > 0)
        remove(output_path)
        self.logger.info('Completed')



if __name__ == '__main__':
    unittest.main()