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










# create Basemap instance.
m = Basemap(projection='merc', llcrnrlat=24., urcrnrlat=50., \
            llcrnrlon=-123., urcrnrlon=-67., resolution='c', \
            rsphere=gb.R_EARTH, lat_0=40., lon_0=-98., lat_ts=20.)

# draw boundary, fill continents, draw costlines, draw parrallels, draw meridians
m.drawmapboundary()
m.drawcoastlines(linewidth=1.25)
m.drawparallels(np.arange(10, 60, 10), labels=[1, 0, 0, 0])
m.drawmeridians(np.arange(-160, -50, 10), labels=[0, 0, 0, 1])

# plot 00 UTC today.
# date = datetime.now().strftime('%Y%m%d')+'00'

# Open, plot, and downsample each flight-track CSV
os.chdir('data/IFF_Track_Points')
selected_files = [x for x in os.listdir() if x.__contains__('_trk.txt')]
for file in selected_files:
    data = np.loadtxt(file, delimiter=',', usecols=(1, 2, 3, 4))
    print(data[0:10])

    # read lats,lons,alts.
    lats = data[:, 1]
    lons = data[:, 2]
    alts = data[:, 3]
    times = data[:, 0]
    print('Latitude:', lats[0:10])
    print('Longitude:', lons[0:10])
    print('Altitude:', alts[0:10])
    print('Times:', times[0:10])

    # the window parameter controls the number of highs and lows detected.
    # (higher value, fewer highs and lows)
    #local_min, local_max = extrema(alts, mode='wrap', window=50)

    # adjust time
    # time units: seconds since 1970-01-01T00:00:00Z
    # time calendar: gregorian
    unit = "seconds since 1970-01-01T00:00:00"
    calendar1 = "gregorian"
    timestamps = num2date(times, units="seconds since 1970-01-01T00:00:00", calendar="gregorian")
    print('Timestamps:', timestamps[0])

    # generate meshgrid to plot contour-map
    lonsm, latsm = np.meshgrid(lons, lats)
    altsm = np.zeros(np.shape(latsm))

    for i in range(0,len(lats)):
        altsm[i][i] = alts[i]

    m.contour(lonsm, latsm, altsm, latlon=True, cmap=cm.coolwarm)

    # Place Flight Track in Appropriate Date Folder
    PATH_TO_SORTED_TRACKPOINTS = gb.PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/'
    str_current_date = timestamps[0].isoformat()[:10]
    if(not (os.listdir(PATH_TO_SORTED_TRACKPOINTS).__contains__(str_current_date))):
        os.mkdir(PATH_TO_SORTED_TRACKPOINTS + str_current_date)
    PATH_START_DATE = PATH_TO_SORTED_TRACKPOINTS + str_current_date + '/' + file
    os.rename(file, PATH_START_DATE)

# Return to Project Directory
os.chdir(gb.PATH_PROJECT)



# plot show
plt.title('JFK-LAX Flights, Mercator Projection')
m.colorbar(mappable=None, location='right', size='5%', pad='1%')
plt.show(block=False)
plt.savefig("Output/IFF_Flight_Track.png", format='png')
plt.close()

