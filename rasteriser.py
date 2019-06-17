# -*- coding: utf-8 -*-
"""
Create a 1-bit input raster for UDM from supplied Master Map data
Procedure:
    (1) MasterMap input data is supplied as GeoJSON
    (2) Generate a fishnet that covers the area of the above
    (3) Do an overlay intersection of the two
    (4) Calculate the area of each bounded polygon and write to an "area" attribute
    (5) Aggregate the area based on ID 
    (6) Save as temporary shapefile (should work as GeoJSON but produces an output raster of all zeros - need to understand this)
    (7) Use as input to gdal_rasterize() to create a final output
"""

import geopandas
import uuid
from cerberus import Validator
from osgeo import ogr
from osgeo import osr
from osgeo import gdal

import traceback, logging
from classes import Config, FishNet

logging.basicConfig(
    level=Config.get('LOG_LEVEL'),
    format=Config.get('LOG_FORMAT'),
    datefmt=Config.get('LOG_DATE_FORMAT'),
    filename=Config.get('LOG_FILE'),
    filemode='w')

LOGGER = logging.getLogger('Rasteriser main')      

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

def main(
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
    
    args = {
        'area_codes': area_codes,
        'bounding_box': bounding_box,
        'scale': scale,
        'output_format': output_format,
        'resolution': resolution,
        'area_threshold': area_threshold
    }
    LOGGER.info(', '.join('%s: %s' % arg for arg in args.items()))
        
    # Validate arguments against the schema
    v = Validator()
    args_ok = v.validate(args, ARG_SCHEMA)
    if (args_ok):
        # Validated successfully
        LOGGER.info('Argument validation passed')
        try:
            # Read the supplied GeoJSON data into a DataFrame
            LOGGER.info('Creating GeoDataFrame from input...')
            input_data = geopandas.GeoDataFrame(geojson_data)
            LOGGER.info('Done')
            
            # Create the fishnet
            if bounding_box is not None:
                # Use the supplied British National Grid bounding box
                LOGGER.info('Generate fishnet GeoDataFrame from supplied bounding box...')
                fishnet_geojson = FishNet(bbox=bounding_box, netsize=resolution).create()   
            else:
                # Use the LAD codes
                LOGGER.info('Generate fishnet GeoDataFrame from supplied bounding box...')
                fishnet_geojson = FishNet(lad=area_codes, netsize=resolution).create()
            fishnet = geopandas.GeoDataFrame(fishnet_geojson)
            LOGGER.info('Done')
            
            # Overlay intersection
            LOGGER.info('Overlay data on fishnet using intersection...')
            intersection = geopandas.overlay(fishnet, input_data, how='intersection')
            LOGGER.info('Done')
            
            # Write area attribute into frame
            LOGGER.info('Computing areas...')
            intersection['area'] = intersection.geometry.area
            LOGGER.info('Done')
            
            # Create grid to rasterize via merge and assign an 'include' field based on the threshold
            LOGGER.info('Doing merge...')
            int_merge = fishnet.merge(intersection.groupby(['ID']).area.sum()/100.0, on='ID')
            for i, row in int_merge.iterrows():
                if row['area'] > area_threshold:
                    int_merge.at[i, 'include_me'] = int(0) if invert else int(1)
                else:
                    int_merge.at[i, 'include_me'] = int(1) if invert else int(0)
            LOGGER.info('Done')        
            
            LOGGER.info('Compute bounds of dataset...')
            x_min, y_min, x_max, y_max = int_merge.total_bounds
            xdim = int((x_max - x_min) / resolution)
            ydim = int((y_max - y_min) / resolution)
            LOGGER.info('xmin = {}, ymin = {}, xmax = {}, ymax = {}'.format(x_min, y_min, x_max, y_max))
            
            # Save as temporary shapefile (TO DO - understand what information is gained by doing this that is not present in GeoJSON)
            LOGGER.info('Write out temporary shapefile...')
            temp_shp = '{}/{}.shp'.format(Config.get('DATA_DIRECTORY'), uuid.uuid4().hex)
            int_merge.to_file(temp_shp)
            LOGGER.info('Written to {}'.format(int_merge))
            
            # Open OGR dataset
            ogr_source = ogr.Open(temp_shp)
            output_file = '{}/output_raster.tif'.format(Config.get('DATA_DIRECTORY'), output_filename)
            LOGGER.info('Will write output raster to {}'.format(output_file))
            
            driver = gdal.GetDriverByName('GTiff')
            rasterised = driver.Create(output_file, xdim, ydim, 1, gdal.GDT_Byte)
            rasterised.SetGeoTransform((x_min, resolution, 0, y_max, 0, -resolution))
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(27700)
            rasterised.SetProjection(srs.ExportToWkt())
            LOGGER.info('Set transform and projection, about to rasterise layer...')            
            gdal.RasterizeLayer(rasterised, [1], ogr_source.GetLayer(0), options=["ATTRIBUTE=include_me"])
            LOGGER.info('Done')
            rasterised.FlushCache()
            rasterised = None

        except:
            LOGGER.warning(traceback.format_exc())
    else:
        # Validation fails, log errors
        LOGGER.warning('Argument validation failed, errors follow:')
        for name, errmsg in v.errors:
            LOGGER.warning('--- {} returned "{}"'.format(name, errmsg))
        

if __name__ == "__main__":
    LOGGER.info('Starting...')
    main()
    LOGGER.info('Finished')
