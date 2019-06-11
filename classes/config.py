#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System-wide configuration

Created on Wed Jun  5 16:22:55 2019

@author: ndh114
"""

import logging
from os.path import dirname, join

class Config:
    
    # Project top-level directory
    __project_root = dirname(dirname(__file__))
    
    __conf = {
            
        # NISMOD-DB++ API  
        'NISMOD_DB_USERNAME' : 'API_USERNAME_HERE',
        'NISMOD_DB_PASSWORD' : 'API_PASSWORD_HERE',
        'NISMOD_DB_API_URL'  : 'https://www.nismod.ac.uk/api/data',                
        
        # Logging
        'log_level'          : logging.DEBUG,
        'LOG_FILE'           : join(__project_root, 'logs', 'rasteriser.log'),
        'LOG_FORMAT'         : '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        'LOG_DATE_FORMAT'    : '%d-%m %H:%M',
        
        # Default data directory
        'DATA_DIRECTORY'     : join(__project_root, 'data')
    }
    
    __setters = ["log_level"]
    
    @staticmethod
    def get(name):
        return Config.__conf[name]
    
    @staticmethod
    def set(name, value):
        if name in Config.__setters:
            Config.__conf[name] = value
        else:
            raise NameError('Name not accepted in set() method')
