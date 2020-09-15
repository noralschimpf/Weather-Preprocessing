import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from mpl_toolkits.basemap import Basemap, addcyclic
from scipy.ndimage.filters import minimum_filter, maximum_filter
from matplotlib import dates, cm
from netCDF4 import Dataset, num2date
import Global_Tools as gb

# Shift Flight Track-Point to a New Start-Time
PATH_FILES_TO_SHIFT = gb.PATH_PROJECT + '/Data/IFF_Track_Points/'
TIME_START_TARGET = datetime(year=2018, month=11, day=4, hour=18, minute=00)

os.chdir(PATH_FILES_TO_SHIFT)

files = [x for x in os.listdir() if x.__contains__('.txt')]

for file in files:
    data = np.loadtxt(file, delimiter=',')

    times = data[:, 0]
    lats = data[:, 1]
    lons = data[:, 2]
    alts = data[:, 3]

    start_time = num2date(times[0], units='Seconds Since 1970-01-01T00:00:00', calendar='gregorian')
    end_time = num2date(times[-1], units='Seconds Since 1970-01-01T00:00:00', calendar='gregorian')
    print('ORIGINAL:\t' + start_time.isoformat() + "\t" + end_time.isoformat())

    time_diff = start_time - TIME_START_TARGET
    times = times - time_diff.total_seconds()

    start_time = num2date(times[0], units='Seconds Since 1970-01-01T00:00:00', calendar='gregorian')
    end_time = num2date(times[-1], units='Seconds Since 1970-01-01T00:00:00', calendar='gregorian')
    print('SHIFTED:\t' + start_time.isoformat() + '\t' + end_time.isoformat())

    new_data = np.vstack((times, lats, lons, alts)).T

    gb.save_csv_by_date(PATH_FILES_TO_SHIFT + '/Shifted/', start_time, new_data, file)