# udm-rasteriser

## Introduction

This repo contains the Python code for preparing cellular raster input data for UDM.  It is bundled as two utility classes:

`
classes/fishnet.py
classes/rasteriser.py
`

The first creates a rectangular grid of a chosen cell size to overlay a particular region defined either by a bounding box or a 
list of LAD codes.

The rasteriser itself utilises the fishnet generation as the first stage of a process of overlaying the input data (supplied) and
performing an intersection operation.  The area corresponding to data in each cell is summed and the cell itself kept in the 
eventual raster output if the area is greater than (or less than if an inverted raster is required) the chosen threshold value.

## Installation

Clone this repository in the usual way.  The dependencies, in terms of Python libraries, are contained in:

`
environment.yaml
`

This can be trivially imported into Anaconda using:

`
conda env create environment.yaml
`

## Testing

The unit tests are contained in test_rasteriser.py at the top level.  They are writting using the 'unittest' harness and can be
run from the command line using:

`
python test_rasteriser.py
`

The test methods give a few real-world examples of how to use the code.

All output is written to a logfile in:

`
logs/rasteriser.log
`

If anything appears to be going wrong, editing the line:

`
'LOG_LEVEL'          : logging.INFO,
`

in classes/config.py to use e.g. logging.DEBUG should result in some more informative output on what the rasteriser is doing.

## Documentation

[https://davidherbert2.github.io/udm-rasteriser/build/html/source/classes.html#module-classes.config](There is 
class documentation in Sphinx hosted via GitHub Pages)
