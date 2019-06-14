# -*- coding: utf-8 -*-
"""
Create an input raster for UDM from Master Map data
Procedure:
    (1) Read in appropriate MM data from NISMOD++ database API
    (2) Generate a fishnet that covers the area of the above
    (3) Do an overlay intersection of the two
    (4) Calculate the area of each bounded polygon and write to an "area" attribute
    (5) Aggregate the area based on ID 
    (6) Save as temporary shapefile (should work as GeoJSON but doesn't)
    (7) Use as input to gdal_rasterize() to create a final output
"""

import geopandas
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
        output_format = 'GeoTIFF',              # Raster output file format (GeoTIFF|ASCII)
        resolution = 100.0,                     # Fishnet sampling resolution in metres
        area_threshold = 50.0                   # Minimum data area within a cell to trigger raster inclusion
        ):
        
    # Validate arguments against the schema
    v = Validator()
    args_ok = v.validate({
        'area_codes': area_codes,
        'bounding_box': bounding_box,
        'scale': scale,
        'output_format': output_format,
        'resolution': resolution,
        'area_threshold': area_threshold
    }, ARG_SCHEMA)
    if (args_ok):
        # Validated successfully
        LOGGER.info('Argument validation passed')
        try:
            # Read the supplied GeoJSON data into a DataFrame
            input_data = geopandas.GeoDataFrame(geojson_data)
            # Create the fishnet
            if bounding_box is not None:
                # Use the supplied British National Grid bounding box
                fishnet_geojson = FishNet(bbox=bounding_box, netsize=resolution)   
            else:
                # Use the LAD codes
                fishnet_geojson = FishNet(lad=area_codes, netsize=resolution)
            fishnet = geopandas.GeoDataFrame(fishnet_geojson)
            
            # TO DO
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



x_pxsize = 100;
y_pxsize = 100;
threshold = 50.0

# Read fishnet
graticule = geopandas.GeoDataFrame.from_file(r'/home/campus.ncl.ac.uk/ndh114/Documents/udm/data/rectangle_graticule.shp')

# Read test MM data
inland_water = geopandas.GeoDataFrame.from_file(r'/home/campus.ncl.ac.uk/ndh114/Documents/udm/data/inland_water_e08000021.shp')

# Overlay intersection
intersection = geopandas.overlay(graticule, inland_water, how='intersection')

# Write area attribute
intersection['area'] = intersection.geometry.area

# Create grid to rasterize via merge and assign an 'include' field based on the threshold
int_merge = graticule.merge(intersection.groupby(['ID']).area.sum()/100.0, on='ID')
for i, row in int_merge.iterrows():
    if row['area'] > threshold:
        int_merge.at[i, 'include_me'] = int(1)
    else:
        int_merge.at[i, 'include_me'] = int(0)
        
x_min, y_min, x_max, y_max = int_merge.total_bounds
xdim = int((x_max - x_min) / x_pxsize)
ydim = int((y_max - y_min) / y_pxsize)

# Save as temporary shapefile
int_merge.to_file(r'/home/campus.ncl.ac.uk/ndh114/Documents/udm/data/grid_to_rasterise.shp')

# Open OGR dataset
ogr_source = ogr.Open(r'/home/campus.ncl.ac.uk/ndh114/Documents/udm/data/grid_to_rasterise.shp')

driver = gdal.GetDriverByName('GTiff')
rasterised = driver.Create(r'/home/campus.ncl.ac.uk/ndh114/Documents/udm/data/output_raster.tif', xdim, ydim, 1, gdal.GDT_Byte)
rasterised.SetGeoTransform((x_min, x_pxsize, 0, y_max, 0, -y_pxsize))
srs = osr.SpatialReference()
srs.ImportFromEPSG(27700)
rasterised.SetProjection(srs.ExportToWkt())
err = gdal.RasterizeLayer(rasterised, [1], ogr_source.GetLayer(0), options=["ATTRIBUTE=include_me"])
rasterised.FlushCache()
rasterised = None