#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rasteriser class

Created on Mon Jun 17 14:30:23 2019

@author: ndh114
"""

import geopandas
import uuid
from cerberus import Validator
from osgeo import ogr
from osgeo import osr
from osgeo import gdal

import traceback, logging
from classes import Config, FishNet

class Rasteriser:
    
    ARG_SCHEMA = {
        'area_codes': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'string',
                'regex': '^[A-Z][0-9]{8}$'
            }
        },
        'bounding_box': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'float',
                'min': -100000.0,
                'max': 1250000.0
            }
        },
        'scale': {
            'type': 'list',
            'allowed': ['oa', 'lad', 'gor']
        },
        'output_format': {
            'type': 'string',
            'allowed': ['GeoTIFF', 'ASCII']
        },
        'resolution': {
            'type': 'float',
            'min': 10.0,
            'max': 10000.0
        },
        'area_threshold': {
            'type': 'float',
            'min': 0.0,
            'max': 100.0
        }
    }
        
    def __init__(self, 
                  geojson_data,                           # Extracted GeoJSON data
                  area_codes = 'all',                     # Boundary specified either by area codes
                  bounding_box = None,                    # Bounding box as a list [xmin, ymin, xmax, ymax]
                  scale = 'lad',                          # Scale to look at (oa|lad|gor) 
                  output_filename = 'output_raster.tif',  # Output filename
                  output_format = 'GeoTIFF',              # Raster output file format (GeoTIFF|ASCII)
                  resolution = 100.0,                     # Fishnet sampling resolution in metres
                  area_threshold = 50.0,                  # Minimum data area within a cell to trigger raster inclusion
                  invert = True                           # True if output raster gets a '0' for areas > threshold
                  ):
        """
        Constructor
        
        Keyword arguments:
        geojson_data       -- extracted GeoJSON data
        area_codes         -- boundary specified by area code list
        bounding_box       -- boundary specified by bounding box as a list [xmin, ymin, xmax, ymax]
        scale              -- scale to look at (oa|lad|gor) 
        output_filename    -- output filename
        output_format      -- raster output file format (GeoTIFF|ASCII)
        resolution         -- fishnet sampling resolution in metres
        area_threshold     -- minimum data area within a cell to trigger raster inclusion
        invert             -- True if output raster gets a '0' for areas > threshold
        
        Returns:
        full file path (output_filename supplied)
        """
        
        self.logger = logging.getLogger('Raster generation') 
        
        args = {
            'area_codes': area_codes,
            'bounding_box': bounding_box,
            'scale': scale,
            'output_format': output_format,
            'resolution': resolution,
            'area_threshold': area_threshold
        }        
            
        # Validate arguments against the schema
        v = Validator()
        args_ok = v.validate(args, self.ARG_SCHEMA)
        if (args_ok):
            # Validated successfully
            self.logger.info('Argument validation passed')
            self.logger.info(', '.join('%s: %s' % arg for arg in args.items()))
            self.geojson_data    = geojson_data
            self.area_codes      = area_codes
            self.bounding_box    = bounding_box
            self.scale           = scale
            self.output_filename = output_filename
            self.output_format   = output_format
            self.resolution      = resolution
            self.area_threshold  = area_threshold
            self.invert          = invert
        else:
            # Validation fails, log errors
            self.logger.warning('Argument validation failed, errors follow:')
            for name, errmsg in v.errors:
                self.logger.warning('--- {} returned "{}"'.format(name, errmsg))
        
    def create(self):
        """
        Generate the output raster dataset
        """
        try:
            # Read the supplied GeoJSON data into a DataFrame
            self.logger.info('Creating GeoDataFrame from input...')
            input_data = geopandas.GeoDataFrame(self.geojson_data)
            self.logger.info('Done')
            
            # Create the fishnet
            if self.bounding_box is not None:
                # Use the supplied British National Grid bounding box
                self.logger.info('Generate fishnet GeoDataFrame from supplied bounding box...')
                fishnet_geojson = FishNet(bbox=self.bounding_box, netsize=self.resolution).create()   
            else:
                # Use the LAD codes
                self.logger.info('Generate fishnet GeoDataFrame from supplied bounding box...')
                fishnet_geojson = FishNet(lad=self.area_codes, netsize=self.resolution).create()
            fishnet = geopandas.GeoDataFrame(fishnet_geojson)
            self.logger.info('Done')
            
            # Overlay intersection
            self.logger.info('Overlay data on fishnet using intersection...')
            intersection = geopandas.overlay(fishnet, input_data, how='intersection')
            self.logger.info('Done')
        
            # Write area attribute into frame
            self.logger.info('Computing areas...')
            intersection['area'] = intersection.geometry.area
            self.logger.info('Done')
            
            # Create grid to rasterize via merge and assign an 'include' field based on the threshold
            self.logger.info('Doing merge...')
            int_merge = fishnet.merge(intersection.groupby(['ID']).area.sum()/100.0, on='ID')
            for i, row in int_merge.iterrows():
                if row['area'] > self.area_threshold:
                    int_merge.at[i, 'include_me'] = int(0) if self.invert else int(1)
                else:
                    int_merge.at[i, 'include_me'] = int(1) if self.invert else int(0)
            self.logger.info('Done')        
            
            self.logger.info('Compute bounds of dataset...')
            x_min, y_min, x_max, y_max = int_merge.total_bounds
            xdim = int((x_max - x_min) / self.resolution)
            ydim = int((y_max - y_min) / self.resolution)
            self.logger.info('xmin = {}, ymin = {}, xmax = {}, ymax = {}'.format(x_min, y_min, x_max, y_max))
            
            # Save as temporary shapefile (TO DO - understand what information is gained by doing this that is not present in GeoJSON)
            self.logger.info('Write out temporary shapefile...')
            temp_shp = '{}/{}.shp'.format(Config.get('DATA_DIRECTORY'), uuid.uuid4().hex)
            int_merge.to_file(temp_shp)
            self.logger.info('Written to {}'.format(int_merge))
            
            # Open OGR dataset
            ogr_source = ogr.Open(temp_shp)
            output_file = '{}/output_raster.tif'.format(Config.get('DATA_DIRECTORY'),self. output_filename)
            self.logger.info('Will write output raster to {}'.format(output_file))
            
            driver = gdal.GetDriverByName('GTiff')
            rasterised = driver.Create(output_file, xdim, ydim, 1, gdal.GDT_Byte)
            rasterised.SetGeoTransform((x_min, self.resolution, 0, y_max, 0, -self.resolution))
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(27700)
            rasterised.SetProjection(srs.ExportToWkt())
            self.logger.info('Set transform and projection, about to rasterise layer...')            
            gdal.RasterizeLayer(rasterised, [1], ogr_source.GetLayer(0), options=["ATTRIBUTE=include_me"])
            self.logger.info('Done')
            rasterised.FlushCache()
            rasterised = None

        except:
            self.logger.warning(traceback.format_exc())