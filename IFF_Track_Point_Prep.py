import os

os.environ['PROJ_LIB'] = 'C:\\Users\\natha\\anaconda3\\envs\\WeatherPreProcessing\\Library\\share'
"""
Read Flight Track-Point Files and Plot in Basemap
"""


import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from mpl_toolkits.basemap import Basemap, addcyclic
from scipy.ndimage.filters import minimum_filter, maximum_filter
from matplotlib import dates, cm
from netCDF4 import Dataset, num2date
import Global_Tools as gb


# create Basemap instance
'''
m = Basemap(projection='merc', llcrnrlat=24., urcrnrlat=50., \
            llcrnrlon=-123., urcrnrlon=-67., resolution='c', \
            rsphere=gb.R_EARTH, lat_0=40., lon_0=-98., lat_ts=20.)

# draw boundary, fill continents, draw costlines, draw parrallels, draw meridians
m.drawmapboundary()
m.drawcoastlines(linewidth=1.25)
m.drawparallels(np.arange(10, 60, 10), labels=[1, 0, 0, 0])
m.drawmeridians(np.arange(-160, -50, 10), labels=[0, 0, 0, 1])
'''
PATH_TRACK_POINTS = gb.PATH_PROJECT + 'data/IFF_Track_Points/'

# Open, plot, and downsample each flight-track CSV
os.chdir(PATH_TRACK_POINTS)
track_files = [x for x in os.listdir() if x.__contains__('_trk.txt')]
for file in track_files:
    data = np.loadtxt(file, delimiter=',', usecols=(1, 2, 3, 4))
    data_slicing_incr = int(np.floor(len(data) / gb.TARGET_SAMPLE_SIZE))
    data_sliced = data[::data_slicing_incr]
    print(data_sliced[0:10])

    # read lats,lons,alts.
    times = data_sliced[:, 0]
    lats = data_sliced[:, 1]
    lons = data_sliced[:, 2]
    alts = data_sliced[:, 3]

    # generate meshgrid to plot contour-map
    '''
    lonsm, latsm = np.meshgrid(lons, lats)
    altsm = np.zeros(np.shape(latsm))
    for i in range(0,len(lats)):
        altsm[i][i] = alts[i]
    m.contour(lonsm, latsm, altsm, latlon=True, cmap=cm.coolwarm)
    '''

    # Sort and Save file by timestamp
    timestamp = num2date(times[0], units="seconds since 1970-01-01T00:00:00", calendar="gregorian")
    PATH_TO_SORTED_TRACKPOINTS = gb.PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/'
    gb.save_csv_by_date(PATH_TO_SORTED_TRACKPOINTS, timestamps[0], data_sliced, file)


# plot show
'''
plt.title('JFK-LAX Flights, Mercator Projection')
#m.colorbar(mappable=None, location='right', size='5%', pad='1%')
plt.show(block=False)
plt.savefig("Output/IFF_Flight_Track.png", format='png')
plt.close()
'''

os.chdir(gb.PATH_PROJECT)
print('done')