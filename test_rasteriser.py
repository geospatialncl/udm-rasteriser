#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test bed for rasteriser and fishnet generator functionality

Created on Thu Jun  6 12:17:17 2019

@author: ndh114
"""

from os import remove, path
import uuid
import json
import unittest
import logging
import requests
import traceback
from geopandas import GeoDataFrame, overlay

from classes import Config, FishNet, Rasteriser

#class TestFishNet(unittest.TestCase):    
#
#    def setUp(self):
#        logging.basicConfig(
#            level=Config.get('LOG_LEVEL'),
#            format=Config.get('LOG_FORMAT'),
#            datefmt=Config.get('LOG_DATE_FORMAT'),
#            filename=Config.get('LOG_FILE'),
#            filemode='w')
#        self.logger = logging.getLogger('TestFishNet')
#    
#    def test_fishnet_bbox(self):
#        """
#        Tests fishnet generation with a bounding box
#        """
#        self.logger.info('Fishnet with bounding box...')
#        output_file = '{}.json'.format(uuid.uuid4().hex)
#        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
#        FishNet(outfile=output_file, outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()
#        self.assertTrue(path.exists(output_path))
#        self.assertTrue(path.getsize(output_path) > 0)
#        remove(output_path)
#        self.logger.info('Completed')
#        
#    def test_fishnet_area_codes(self):
#        """
#        Tests fishnet generation with a list of area codes
#        """
#        self.logger.info('Fishnet with list of area codes...')
#        output_file = '{}.json'.format(uuid.uuid4().hex)
#        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
#        FishNet(outfile=output_file, outformat='GeoJSON', lad=['E07000004']).create()
#        self.assertTrue(path.exists(output_path))
#        self.assertTrue(path.getsize(output_path) > 0)
#        remove(output_path)
#        self.logger.info('Completed')
#        
#    def test_fishnet_geojson_string_return(self):
#        """
#        Tests fishnet generation with a GeoJSON string return
#        """
#        self.logger.info('Fishnet with GeoJSON string return...')
#        geojson = FishNet(outfile=None, outformat='GeoJSON', bbox=[414650, 563500, 429600, 575875]).create()
#        self.assertFalse(geojson is None)
#        try:
#            gdf = GeoDataFrame.from_features(geojson)
#            self.logger.info(gdf.head(10))
#        except ValueError:
#            self.fail('Returned GeoJSON could not be read into a GeoDataFrame')
#        self.logger.info('Completed')
#
#    def test_fishnet_shapefile(self):
#        """
#        Tests fishnet generation with a shapefile output
#        """
#        self.logger.info('Fishnet with ESRI shapefile output...')
#        output_file = '{}.shp'.format(uuid.uuid4().hex)
#        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
#        FishNet(outfile=output_file, outformat='ESRI Shapefile', lad=['E07000004']).create()
#        self.assertTrue(path.exists(output_path))
#        self.assertTrue(path.getsize(output_path) > 0)
#        remove(output_path)
#        self.logger.info('Completed')

class TestRasteriser(unittest.TestCase):
    
    def setUp(self):
        logging.basicConfig(
            level=Config.get('LOG_LEVEL'),
            format=Config.get('LOG_FORMAT'),
            datefmt=Config.get('LOG_DATE_FORMAT'),
            filename=Config.get('LOG_FILE'),
            filemode='w')
        self.logger_r = logging.getLogger('TestRasteriser')
        
    def test_rasterise_from_shp(self):
        """
        Read inland water data from shapefile
        """
        self.logger_r.info('Rasteriser with Inland Water MasterMap data from shapefile...')
        output_file = 'test_water_output_raster.tif'
        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
        if path.exists(output_path):
            remove(output_path)
        try:
            # Get MasterMap data, requesting classification codes 'General Surface', 'Natural Environment'
            gdf = GeoDataFrame.from_file('{}/inland_water_e08000021.shp'.format(Config.get('DATA_DIRECTORY')))
            # Call rasteriser
            self.logger_r.info('Calling rasteriser...')
            Rasteriser(
                gdf.to_json(),
                area_codes=['E08000021'],
                output_filename=output_file,
                area_threshold=50.0                
            ).create()
            self.logger_r.info('Written output to {}/{}'.format(Config.get('DATA_DIRECTORY'), output_file))
            self.logger_r.info('Completed')
        except:
            self.logger_r.warning(traceback.format_exc())
            self.fail('Failing test due to unexpected exception')  
        
    
#    def test_rasterise_from_nismod(self):
#        """
#        Get MasterMap data from NISMOD API as input GeoJSON data
#        """
#        self.logger_r.info('Rasteriser with API MasterMap data...')
#        output_file = 'test_output_raster.tif'
#        output_path = '{}/{}'.format(Config.get('DATA_DIRECTORY'), output_file)
#        if path.exists(output_path):
#            remove(output_path)
#        try:
#            # Get MasterMap data, requesting classification codes 'General Surface', 'Natural Environment'
#            api_parms = {
#                'scale': 'lad',
#                'area_codes': ['E07000004','E07000008','E07000009','E07000011'],
#                'classification_codes': ['10056', '10111'],
#                'export_format': 'geojson'
#            }
#            api_url = '{}/mastermap/areas'.format(Config.get('NISMOD_DB_API_URL'))
#            auth_username = Config.get('NISMOD_DB_USERNAME')
#            auth_password = Config.get('NISMOD_DB_PASSWORD')
#            self.logger_r.info('Calling API to extract input GeoJSON data...')
#            r = requests.get(api_url, params=api_parms, auth=(auth_username, auth_password))
#            input_geojson = r.json()
#            # Call rasteriser
#            self.logger_r.info('Calling rasteriser...')
#            Rasteriser(
#                input_geojson,
#                area_codes=['E07000004','E07000008','E07000009','E07000011'],
#                output_filename=output_file                
#            ).create()
#            self.logger_r.info('Written output to {}/{}'.format(Config.get('DATA_DIRECTORY'), output_file))
#            self.logger_r.info('Completed')
#        except:
#            self.logger_r.warning(traceback.format_exc())
#            self.fail('Failing test due to unexpected exception')        

if __name__ == '__main__':
    unittest.main()