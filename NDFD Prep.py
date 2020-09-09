from netCDF4 import Dataset, num2date, date2num, MFDataset
import numpy as np
import os
from shutil import copyfile
from mpl_toolkits.basemap import Basemap
from matplotlib import cm, pyplot as plt
import Global_Tools as gb
from mpl_toolkits.mplot3d import axes3d
from datetime import datetime


PATH_NDFD_ROOT = gb.PATH_PROJECT + '/Data/NDFD/'
os.chdir(PATH_NDFD_ROOT)
nc_files = [x for x in os.listdir() if x.__contains__('.nc')]
default_vars = ['MapProjection', 'YCells', 'XCells', 'longitude', 'latitude', 'ProjectionHr']

# Sort and Rename NC files
for file in nc_files:
    rootgrp_tmp = Dataset(file, 'r', type="netCDF3")
    Data_type = np.setdiff1d(list(rootgrp_tmp.variables.keys()), default_vars)
    Active_times = rootgrp_tmp.variables['ProjectionHr']
    Active_time = num2date(Active_times[0], units=Active_times.units, calendar='gregorian')
    rootgrp_tmp.close()
    unique_ctr = 0
    PATH_NDFD_Sorted_File = PATH_NDFD_ROOT + Active_time.isoformat()[:10]
    PATH_NDFD_Sorted_File = PATH_NDFD_Sorted_File + '/' + Data_type[0] + '__' + \
                            Active_time.isoformat().replace(':', '')[:-2] + '_' + str(unique_ctr) + '.nc'
    while os.path.isfile(PATH_NDFD_Sorted_File):
        unique_ctr += 1
    os.renames(file, PATH_NDFD_Sorted_File)
