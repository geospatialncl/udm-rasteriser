#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fishnet creation class

Created on Wed Jun  5 14:41:41 2019

@author: ndh114
"""

from os import path, makedirs, remove
import traceback, logging
import uuid
from osgeo import osr
import gdal, ogr
from math import ceil
from io import BytesIO
import requests
import geopandas
from geojson import loads
from cerberus import Validator
from classes import Config

class FishNet:

    __ARG_SCHEMA = {
        'outfile': {
            'type': 'string',
            'required': False,
            'nullable': True
        },
        'outformat': {
            'type': 'string',
            'allowed': ['ESRI Shapefile', 'GeoJSON']
        },
        'lad': {
            'type': 'list',
            'required': False,
            'nullable': True,
            'schema': {
                'type': 'string',
                'regex': '^[A-Z][0-9]{8}$'
            }
        },
        'bbox': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'float',
                'min': -100000.0,
                'max': 1250000.0
            }
        },          
        'netsize': {
            'type': 'float',
            'min': 10.0,
            'max': 10000.0
        }
    }    
    
    def __init__(self, 
                 outfile=None, 
                 outformat='GeoJSON', 
                 lad=None,
                 bbox=[90000.0, 10000.0, 400000.0, 660000.0], 
                 netsize=100.0):
        """
        |  Constructor
        |  
        |  Keyword arguments:
        |  outfile    -- filename to write the fishnet output to (default None, indicating return the data as GeoJSON string)
        |  outformat  -- ESRI Shapefile|GeoJSON, (default 'GeoJSON')
        |  lad        -- Local Authority District code(s) to deduce bounds from ('all' to use all) 
        |                (default None, will be used preferentially to bbox if supplied)
        |  bbox       -- Bounding box of interest (default to bounding box of England and Wales)
        |  netsize    -- Resolution of the grid in metres (default 100.0)
        |   
        |  Returns:
        |  full file path (outfile supplied), or GeoJSON string (outfile not supplied)
        """
        
        self.logger = logging.getLogger('Fishnet generation') 
        
        if not outfile and outformat == 'ESRI Shapefile':
            raise ValueError('Output filename should be supplied for writing to Shapefile')
        
        args = {
            'outfile': outfile,
            'outformat': outformat,
            'lad': lad,
            'bbox': bbox,
            'netsize': netsize
        }
        v = Validator()
        args_ok = v.validate(args, self.__ARG_SCHEMA)            
        if args_ok:
            # Validated arguments ok
            self.logger.info('Argument validation passed')                              
            self.logger.info(', '.join('%s: %s' % arg for arg in args.items()))
            self.outfile   = outfile
            self.outformat = outformat
            self.lad       = lad
            self.bbox      = bbox
            self.netsize   = netsize
        else:
            # Failed validation
            self.logger.warning('Argument validation failed, errors follow:')
            for name, errmsg in v.errors:
                self.logger.warning('--- {} returned "{}"'.format(name, errmsg))
        
    def create(self):
        """
        |  Generate the fishnet dataset, based on the code at
        |  https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-fishnet-grid        
        """
        gdal.UseExceptions();
        try:
            # Get bounding values
            aoi = self.bbox
            if self.lad:
                # Get the bounds from a (list of) Local Authority District boundary(s)/all
                self.logger.info('Get boundary from list of LAD codes...')
                try:
                    kvp = {
                        'lad_codes': ','.join(self.lad),
                        'export_format': 'geojson',
                        'year': 2016
                    }
                    api = '{}/{}/{}'.format(Config.get('NISMOD_DB_API_URL'), 'boundaries', 'lads')
                    auth_username = Config.get('NISMOD_DB_USERNAME')
                    auth_password = Config.get('NISMOD_DB_PASSWORD')
                    r = requests.get(api, params=kvp, auth=(auth_username, auth_password))
                    # Note: should be able to simply read r.json() into a GeoDataFrame, however it throws a ValueError
                    # 'Mixing dicts with non-Series may lead to ambiguous ordering' which makes very little sense to me!
                    # So we do it a roundabout way via the recipe at
                    # https://gis.stackexchange.com/questions/225586/reading-raw-data-into-geopandas
                    self.logger.info('NISMOD API call completed')
                    gdf = geopandas.read_file(BytesIO(r.content))
                    aoi = gdf.total_bounds
                except ValueError:
                    raise                    
            
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
            
            out_driver = ogr.GetDriverByName(self.outformat)
        
            output_file = self.outfile
            if output_file is None:
                # Stream the data to memory
                output_file = '/vsimem/{}.geojson'.format(uuid.uuid4().hex)
            else:
                # Create output file                
                if not path.isabs(output_file):
                    # Relative path => so prepend data directory (does NOT handle making subdirectories here)
                    data_dir = Config.get('DATA_DIRECTORY')
                    self.logger.info('Relative path supplied, assume relative to data directory {}'.format(data_dir))
                    output_file = path.join(data_dir, output_file)
                else:
                    # Absolute path => ensure all directories are present before writing
                    try:
                        makedirs(path.dirname(output_file), exist_ok=True)
                    except OSError:
                        self.logger.warning('Failed to create subdirectory for output file')
                        raise
                # Delete any pre-existing version of output file        
                if path.exists(output_file):
                    remove(output_file)
                
            out_data_source = out_driver.CreateDataSource(output_file)
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(27700)
            out_layer = out_data_source.CreateLayer(output_file, srs=srs, geom_type=ogr.wkbPolygon)
            
            # Add a FID field
            id_field = ogr.FieldDefn('FID', ogr.OFTInteger)
            out_layer.CreateField(id_field)            
            feature_defn = out_layer.GetLayerDefn()
    
            # Create grid cells
            fid = 1
            countcols = 0
            while countcols < cols:
                countcols += 1
                #self.logger.info('Generating column {}...'.format(countcols))
                # Reset envelope for rows
                ring_y_top = ring_y_top_origin
                ring_y_bottom = ring_y_bottom_origin
                countrows = 0
        
                while countrows < rows:
                    countrows += 1
                    #self.logger.info('Row {}'.format(countrows))
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
                    out_feature.SetField('FID', fid)
                    out_layer.CreateFeature(out_feature)
                    out_feature = None
                    fid += 1
        
                    # New envelope for next poly
                    ring_y_top = ring_y_top - grid_height
                    ring_y_bottom = ring_y_bottom - grid_height
        
                # New envelope for next poly
                ring_x_left_origin = ring_x_left_origin + grid_width
                ring_x_right_origin = ring_x_right_origin + grid_width
        
            # Save and close data sources
            out_data_source = None
            fishnet_output = None
            if self.outfile is None:
                # Read the memory buffer GeoJSON into Python dict structure
                memfile_json = self.read_file(output_file).decode('utf-8')                
                fishnet_output = loads(memfile_json)               
            else:
                fishnet_output = output_file                        
            self.logger.info('Finished writing fishnet output')
            return fishnet_output
        except:
            self.logger.warning(traceback.format_exc())
            return None
        
    def read_file(self, filename):
        """
        Read an in-memory file
        https://gis.stackexchange.com/questions/255153/gdal-vectortranslate-returns-an-empty-file
        also see:
        https://gis.stackexchange.com/questions/318916/getting-png-binary-data-from-gdaldataset
        """
        vsifile = gdal.VSIFOpenL(filename,'r')
        gdal.VSIFSeekL(vsifile, 0, 2)
        vsileng = gdal.VSIFTellL(vsifile)
        gdal.VSIFSeekL(vsifile, 0, 0)
        return gdal.VSIFReadL(1, vsileng, vsifile)
            
            
            
            
