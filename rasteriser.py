# -*- coding: utf-8 -*-
"""
Create an input raster for UDM from Master Map data
Procedure:
    (1) Read in MM data as shapefile (eventually done by conversion from API output)
    (2) Read in a fishnet that covers the area of the above (need to auto-generate this)
    (3) Do an overlay intersection of the two
    (4) Calculate the area of each bounded polygon and write to an "area" attribute
    (5) Aggregate the area based on ID 
    (6) Convert to GeoJSON
    (7) Use as input to gdal_rasterize()
"""

import geopandas
from osgeo import ogr
from osgeo import osr
from osgeo import gdal

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