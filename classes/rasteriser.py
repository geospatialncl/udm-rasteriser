#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rasteriser class

Created on Mon Jun 17 14:30:23 2019

@author: ndh114
"""

from geopandas import GeoDataFrame, overlay
import uuid
from cerberus import Validator
from osgeo import ogr
from osgeo import osr
from osgeo import gdal

import traceback, logging
from geojson import loads, dumps
from pathlib import Path
from os import path, remove
from classes import Config, FishNet

class Rasteriser:
    
    __ARG_SCHEMA = {
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
            'nullable': True,
            'schema': {
                'type': 'float',
                'min': -100000.0,
                'max': 1250000.0
            }
        },
        'scale': {
            'type': 'string',
            'allowed': ['oa', 'lad', 'gor']
        },
        'output_filename': {
            'type': 'string',
            'required': True
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
        },
        'nodata': {
            'type': 'integer',
            'allowed': [0, 1]
        }
    }
        
    def __init__(self, 
                  geojson_data,                           # Extracted GeoJSON data
                  area_codes = [],                        # Boundary specified either by area codes OR
                  bounding_box = None,                    # As a bounding box [xmin, ymin, xmax, ymax] OR
                  fishnet = None,                         # An existing FishNet GeoJSON output
                  scale = 'lad',                          # Scale to look at (oa|lad|gor) 
                  output_filename = 'output_raster.tif',  # Output filename
                  output_format = 'GeoTIFF',              # Raster output file format (GeoTIFF|ASCII)
                  resolution = 100.0,                     # Fishnet sampling resolution in metres
                  area_threshold = 50.0,                  # Minimum data area within a cell to trigger raster inclusion
                  invert = True,                          # True if output raster gets a '0' for areas > threshold
                  nodata = 1                              # Value for nodata pixels
                  ):
        """
        |  Constructor
        |
        |  Keyword arguments:
        |  geojson_data       -- extracted GeoJSON data
        |  area_codes         -- boundary specified by area code list OR 
        |  bounding_box       -- as a bounding box as a list [xmin, ymin, xmax, ymax] OR
        |  fishnet            -- as existing fishnet GeoJSON output from the FishNet class
        |  scale              -- scale to look at (oa|lad|gor) 
        |  output_filename    -- output filename
        |  output_format      -- raster output file format (GeoTIFF|ASCII)
        |  resolution         -- fishnet sampling resolution in metres
        |  area_threshold     -- minimum data area within a cell to trigger raster inclusion
        |  invert             -- True if output raster gets a '0' for areas > threshold
        |  nodata             -- Value for nodata pixels (doesn't take account of 'invert' above!)
        |  
        |  Returns:
        |  full file path (output_filename supplied)
        """
        
        self.logger = logging.getLogger('Raster generation') 
        
        args = {
            'area_codes': area_codes,
            'bounding_box': bounding_box,
            'scale': scale,
            'output_filename': output_filename,
            'output_format': output_format,
            'resolution': resolution,
            'area_threshold': area_threshold,
            'nodata': nodata
        }        
        self.logger.info(', '.join('%s: %s' % arg for arg in args.items()))
            
        # Validate arguments against the schema
        v = Validator()
        args_ok = v.validate(args, self.__ARG_SCHEMA)
        if (args_ok):
            # Validated successfully
            self.logger.info('Argument validation passed')
            self.geojson_data    = geojson_data
            self.area_codes      = area_codes
            self.bounding_box    = bounding_box
            self.fishnet         = fishnet
            self.scale           = scale
            self.output_filename = output_filename
            self.output_format   = output_format
            self.resolution      = resolution
            self.area_threshold  = area_threshold
            self.invert          = invert
            self.nodata          = nodata
        else:
            # Validation fails, log errors
            self.logger.warning('Argument validation failed, errors follow:')
            for name, errmsg in v.errors:
                self.logger.warning('--- {} returned "{}"'.format(name, errmsg))
        
    def create(self):
        """
        |  Generate the output raster dataset
        """
        gdal.UseExceptions();
        temp_shp = '{}/{}.shp'.format(Config.get('DATA_DIRECTORY'), uuid.uuid4().hex)
        try:
            # Read the supplied GeoJSON data into a DataFrame
            self.logger.info('Creating GeoDataFrame from input...')
            
            #self.logger.debug('GeoJSON follows:')
            #elf.logger.debug(self.geojson_data)
            #self.logger.debug('GeoJSON end')
            
            if isinstance(self.geojson_data, str):
                self.logger.info('Input GeoJSON is a string, not a dict => converting...')
                self.geojson_data = loads(self.geojson_data)
            #self.debug_dump_geojson_to_file('rasteriser_input_data_dump.json', self.geojson_data)
            input_data = GeoDataFrame.from_features(self.geojson_data)
            self.logger.debug(input_data.head(10))
            self.logger.info('Done')
            
            # Create the fishnet if necessary
            if self.bounding_box is not None:
                # Use the supplied British National Grid bounding box
                self.logger.info('Generate fishnet GeoDataFrame from supplied bounding box...')
                fishnet_geojson = FishNet(bbox=self.bounding_box, netsize=self.resolution).create()
            elif self.fishnet is not None:
                # Use a supplied fishnet output
                self.logger.info('Generate fishnet GeoDataFrame from supplied GeoJSON...')
                if isinstance(self.fishnet, str):
                    self.logger.info('Input fishnet GeoJSON is a string, not a dict => converting...')
                    self.fishnet = loads(self.fishnet)
                fishnet_geojson = self.fishnet
            elif len(self.area_codes) > 0:
                # Use the LAD codes
                self.logger.info('Generate fishnet GeoDataFrame from supplied LAD codes...')
                fishnet_geojson = FishNet(lad=self.area_codes, netsize=self.resolution).create()
            else:
                raise ValueError('No boundary information supplied - please supply fishnet GeoJSON, bounding box, or list of LAD codes')
            #self.debug_dump_geojson_to_file('rasteriser_fishnet_data_dump.json', fishnet_geojson)
            fishnet = GeoDataFrame.from_features(fishnet_geojson)
            x_min, y_min, x_max, y_max = fishnet.total_bounds
            self.logger.debug(fishnet.head(10))            
            self.logger.info('Done')
            
            # Overlay intersection
            self.logger.info('Overlay data on fishnet using intersection...')
            intersection = overlay(fishnet, input_data, how='intersection')
            self.logger.info('Done')
        
            # Write area attribute into frame
            self.logger.info('Computing areas...')
            intersection['area'] = intersection.geometry.area
            self.logger.info('Done')
            
            # Create grid to rasterize via merge and assign an 'include' field based on the threshold
            self.logger.info('Doing merge...')
            self.logger.debug(intersection.head(10))
            int_merge = fishnet.merge(intersection.groupby(['FID']).area.sum()/100.0, on='FID')
            
            for i, row in int_merge.iterrows():
                self.logger.debug('{} has area {}'.format(i, row['area']))
                if row['area'] > self.area_threshold:
                    int_merge.at[i, 'include_me'] = int(0) if self.invert else int(1)
                else:
                    int_merge.at[i, 'include_me'] = int(1) if self.invert else int(0)            
            self.logger.info('Done')        
            
            self.logger.info('Compute bounds of dataset...')
            #x_min, y_min, x_max, y_max = int_merge.total_bounds
            xdim = int((x_max - x_min) / self.resolution)
            ydim = int((y_max - y_min) / self.resolution)
            self.logger.info('xmin = {}, ymin = {}, xmax = {}, ymax = {}'.format(x_min, y_min, x_max, y_max))
            
            # Save as temporary shapefile (TO DO - understand what information is gained by doing this that is not present in GeoJSON)
            self.logger.info('Write out temporary shapefile...')            
            int_merge.to_file(temp_shp)
            self.logger.info('Written to {}'.format(temp_shp))
            
            # Open OGR dataset
            ogr_source = ogr.Open(temp_shp)
            output_file = '{}/{}'.format(Config.get('DATA_DIRECTORY'),self. output_filename)
            self.logger.info('Will write output raster to {}'.format(output_file))
            
            # Create raster dataset and set projection
            driver = gdal.GetDriverByName('GTiff')
            rasterised = driver.Create(output_file, xdim, ydim, 1, gdal.GDT_Byte)
            rasterised.SetGeoTransform((x_min, self.resolution, 0, y_max, 0, -self.resolution))
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(27700)
            rasterised.SetProjection(srs.ExportToWkt())
            
            # Set nodata values 
            band = rasterised.GetRasterBand(1)
            #band.SetNoDataValue(self.nodata)
            band.Fill(self.nodata)
            
            # Do rasterisation
            self.logger.info('Set transform and projection, about to rasterise layer...')            
            gdal.RasterizeLayer(rasterised, [1], ogr_source.GetLayer(0), options=["ATTRIBUTE=include_me"])
            self.logger.info('Done')
            rasterised.FlushCache()
            rasterised = None
            ogr_source = None
        except:
            self.logger.warning(traceback.format_exc())
        finally:
            self.logger.info('Removing temporary files...')
            filestem = Path(temp_shp).stem
            for shpf in Path(Config.get('DATA_DIRECTORY')).glob('{}.*'.format(filestem)):
                self.logger.info('Cleaning up {}'.format(shpf))
                shpf.unlink()
                
    def debug_dump_geojson_to_file(self, filename, json_data):
        """
        Dump the given JSON data to a file for examination 
        """
        filepath = '{}/{}'.format(Config.get('DATA_DIRECTORY'), filename)
        if path.exists(filepath):
            remove(filepath)
        with open(filepath, 'w') as file_out:
            file_out.write(dumps(json_data))