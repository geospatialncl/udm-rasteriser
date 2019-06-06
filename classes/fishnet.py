#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fishnet creation class

Created on Wed Jun  5 14:41:41 2019

@author: ndh114
"""

import os, traceback, logging
import ogr
from math import ceil
import requests
from geopandas import GeoDataFrame
from classes import Config

class FishNet:    
    
    def __init__(self, outfile, outformat='ESRI Shapefile', lad=None, bbox=[90000.0, 10000.0, 400000.0, 660000.0], netsize=100.0):
        """
        Constructor
        
        Keyword arguments:
        outfile    -- filename to write the fishnet output to (required)
        outformat  -- Shapefile|GeoJSON (default 'ESRI Shapefile')        
        lad        -- Local Authority District code(s) to deduce bounds from ('all' to use all) 
                      (default None, will be used preferentially to bbox if supplied)
        bbox       -- Bounding box of interest (default to bounding box of England and Wales)
        netsize    -- Resolution of the grid in metres (default 100.0)
        """
        if not outfile:
            raise ValueError('Output filename should be supplied')
        
        if outformat != 'ESRI Shapefile' and outformat != 'GeoJSON':
            raise ValueError('Output formats allowed are ESRI Shapefile and GeoJSON, not {}'.format(outformat))
            
        self.outfile   = outfile
        self.outformat = outformat
        self.lad       = lad
        self.bbox      = bbox
        self.netsize   = netsize
        
        args = vars(self)
        
        self.logger    = logging.getLogger('Fishnet generation')                
        self.logger.info(', '.join('%s: %s' % arg for arg in args.items()))
        
    def create(self):
        """
        Generate the fishnet dataset, based on the code at
        https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-fishnet-grid
        
        """
        try:
            # Get bounding values
            aoi = self.bbox
            if self.lad:
                # Get the bounds from a (list of) Local Authority District boundary(s)/all
                try:
                    kvp = {
                        'lad_codes': self.lad,
                        'export_format': 'geojson',
                        'year': 2016
                    }
                    api = '{}/{}/{}'.format(Config.get('NISMOD_DB_API_URL'), 'boundaries', 'lads')                    
                    r = requests.get(api, params=kvp, auth=(Config.get('NISMOD_DB_USERNAME'), Config.get('NISMOD_DB_PASSWORD')))
                    gdf = GeoDataFrame(r.json())
                    aoi = gdf.total_bounds
                except ValueError as api_err:
                    self.logger.warning(api_err)                    
            
            xmin, ymin, xmax, ymax = [float(value) for value in aoi]
            self.logger.info('Fishnet bounds : xmin {}, ymin {}, xmax {}, ymax {}'.format(xmin, ymin, xmax, ymax))
            grid_width = grid_height = float(self.netsize)
        
            # Number of rows x columns
            rows = ceil((ymax-ymin)/grid_height)
            cols = ceil((xmax-xmin)/grid_width)
            self.logger.info('Fishnet has {} rows and {} columns'.format(rows, cols))
        
            # Start grid cell envelope
            ring_x_left_origin = xmin
            ring_x_right_origin = xmin + grid_width
            ring_y_top_origin = ymax
            ring_y_bottom_origin = ymax - grid_height
        
            # Create output file
            out_driver = ogr.GetDriverByName(self.outformat)
            if not os.path.isabs(self.outfile):
                # Relative path => so prepend data directory (does NOT handle making subdirectories here)
                data_dir = Config.get('DATA_DIRECTORY')
                self.logger.info('Relative path supplied, assume relative to data directory {}'.format(data_dir))
                self.outfile = os.path.join(data_dir, self.outfile)
            else:
                # Absolute path => ensure all directories are present before writing
                try:
                    os.makedirs(os.path.dirname(self.outfile), exist_ok=True)
                except OSError as ose:
                    self.logger.warning('Failed to create subdirectory for output file')
                    raise
            # Delete any pre-existing version of output file        
            if os.path.exists(self.outfile):
                os.remove(self.outfile)
                
            out_data_source = out_driver.CreateDataSource(self.outfile)
            out_layer = out_data_source.CreateLayer(self.outfile, geom_type=ogr.wkbPolygon)
            feature_defn = out_layer.GetLayerDefn()
    
            # Create grid cells
            countcols = 0
            while countcols < cols:
                countcols += 1
                self.logger.info('Generating column {}...'.format(countcols))
                # Reset envelope for rows
                ring_y_top = ring_y_top_origin
                ring_y_bottom = ring_y_bottom_origin
                countrows = 0
        
                while countrows < rows:
                    countrows += 1
                    self.logger.info('Row {}'.format(countrows))
                    ring = ogr.Geometry(ogr.wkbLinearRing)
                    ring.AddPoint(ring_x_left_origin, ring_y_top)
                    ring.AddPoint(ring_x_right_origin, ring_y_top)
                    ring.AddPoint(ring_x_right_origin, ring_y_bottom)
                    ring.AddPoint(ring_x_left_origin, ring_y_bottom)
                    ring.AddPoint(ring_x_left_origin, ring_y_top)
                    poly = ogr.Geometry(ogr.wkbPolygon)
                    poly.AddGeometry(ring)
        
                    # Add new geom to layer
                    out_feature = ogr.Feature(feature_defn)
                    out_feature.SetGeometry(poly)
                    out_layer.CreateFeature(out_feature)
                    out_feature = None
        
                    # New envelope for next poly
                    ring_y_top = ring_y_top - grid_height
                    ring_y_bottom = ring_y_bottom - grid_height
        
                # New envelope for next poly
                ring_x_left_origin = ring_x_left_origin + grid_width
                ring_x_right_origin = ring_x_right_origin + grid_width
        
            # Save and close data sources
            out_data_source = None
            self.logger.info('Finished writing fishnet output')
        except:
            self.logger.warning(traceback.format_exc())
            
            
            
            
