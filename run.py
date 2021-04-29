import requests, json, os, sys, glob
sys.path.insert(0, "/udm-rasteriser")
from classes import Config, FishNet, Rasteriser
from geopandas import GeoDataFrame
import geopandas
from shutil import copyfile
from io import BytesIO


def check_fishnet_valid(gdf, uid):
    """
    This checks if there is a 'FID' field in the fishnet. The rasteriser code requires this.

    Returns updated fishnet if a lowercase 'fid' is found.

    Future update should allow user to pass a fid equivalent field name.

    """
    if 'FID' not in gdf.columns:
        # check if fid attribute is lower case
        if 'fid' in gdf.columns:
            gdf = gdf.rename(columns={'fid': 'FID'})
        else:
            print('ERROR! A FID attribute is required within the fishnet dataset.')
            exit(1)
    return gdf


def move_output(file_name, output_dir):
    """
    Move the file from the rasterise output dir to the model output dir
    """

    # copy output from rasteriser output dir to outputs dir
    if os.path.exists('/udm-rasteriser/data/%s.tif' % file_name):
        copyfile('/udm-rasteriser/data/%s.tif' % file_name, os.path.join(output_dir, '%s.tif' % 'output_raster'))
    else:
        print('ERROR! Output raster has not been generated or found at the expected location.')
    return


def rasterise(data, fishnet, output_filename='output_raster.tif', fishnet_uid='FID'):
    """
    Rasterise a set of data
    """
    if '.' not in output_filename:
        output_filename = output_filename+'.tif'
    print(output_filename)

    print('rasterising using existing fishnet')
    Rasteriser(
        data,  # Extracted GeoJSON data
        fishnet=fishnet,    # Fishnet grid GeoJSON
        output_filename=output_filename,  # Output filename
        output_format='GeoTIFF',  # Raster output file format (GeoTIFF|ASCII)
        resolution=100.0,  # Fishnet sampling resolution in metres
        area_threshold=50.0,  # Minimum data area within a cell to trigger raster inclusion
        invert=True,  # True if output raster gets a '0' for areas > threshold
        nodata=1,
        fishnet_uid=fishnet_uid
    ).create()

    return


def run(output_dir='/data', fishnet=None, fishnet_uid='FID'):
    """
    Inputs:
    - fishnet: file path to fishnet
    - files: a list of files to load in and rasterise
    """
    # set the fishnet file path
    fishnet_filepath = '/data/fishnet.geojson'

    # read in fishnet now so can be used in rasterise process do now so only done once if multiple layers
    # read fishnet in with geopandas (seems more stable than with json or geojson libraries)
    fnet = geopandas.read_file(fishnet_filepath, encoding='utf-8')

    # check the fishnet is valid
    fnet = check_fishnet_valid(fnet, fishnet_uid)

    file = '/data/data.gpkg'

    print('Rasterising file %s' % file)
    data_gdf = geopandas.read_file(file, encoding='utf-8')
    # name the output after the input file - get the name of the input file
    output_filename = file.split('/')[-1]
    output_filename = output_filename.split('.')[0]

    # run rasterise process
    rasterise(data=data_gdf.to_json(), fishnet=fnet.to_json(), output_filename=output_filename)

    move_output(output_filename, output_dir)

    return


if __name__ == '__main__':
    run()