import numpy as np

# Global Constants, specc'd by SHERLOC
LAT_ORIGIN = 38.
LONG_ORIGIN = -90.
R_EARTH = 6370997

#Convert relative position to latitude/longitude coordinates for Basemap
#xMeterFrom, yMeterFrom should be 1-D, lat,long returned 1-D
def relToLatLong(xMeterFrom,yMeterFrom, lat_0=38.,long_0=-90.,rEarth=6370997.):
    lat, long = yMeterFrom,xMeterFrom
    for i in range(0,len(xMeterFrom)):
        long[i] = long_0 + (xMeterFrom[i]/rEarth)*(180/np.pi)
    for j in range(0,len(yMeterFrom)):
        lat[j] = lat_0 + (yMeterFrom[j]/rEarth)*(180/np.pi)
    return lat,long