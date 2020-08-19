import numpy as np
import os, re

# Global Constants, specc'd by SHERLOC
LAT_ORIGIN = 38.
LONG_ORIGIN = -90.
R_EARTH = 6370997

# Path / Project Vars
PATH_PROJECT = os.path.abspath('.')
SAMPLE_INTV = 1  # seconds between samples



'''
Convert relative position to latitude/longitude coordinates for Basemap
xMeterFrom, yMeterFrom should be 1-D, lat,long returned 1-D
'''


def rel_to_latlong(xMeterFrom, yMeterFrom, lat_0=38., long_0=-90., rEarth=6370997.):
    lat, long = yMeterFrom, xMeterFrom
    for i in range(0, len(xMeterFrom)):
        long[i] = long_0 + (xMeterFrom[i] / rEarth) * (180 / np.pi)
    for j in range(0, len(yMeterFrom)):
        lat[j] = lat_0 + (yMeterFrom[j] / rEarth) * (180 / np.pi)
    return lat, long


"""
find the indices of local extrema (min and max)
in the input array.
"""


def extrema(mat, mode='wrap', window=10):
    mn = minimum_filter(mat, size=window, mode=mode)
    mx = maximum_filter(mat, size=window, mode=mode)
    # (mat == mx) true if pixel is equal to the local max
    # (mat == mn) true if pixel is equal to the local in
    # Return the indices of the maxima, minima
    return np.nonzero(mat == mn), np.nonzero(mat == mx)


'''
converts each character to its unicode-equivalent
returns as string
'''


def to_unicode(string_in):
    string_temp = ''
    for char in string_in:
        string_temp = string_temp + str(ord(char))
    return str(string_temp)


'''
Returns searchable NavAid and Waypoint callsigns for OpenNav
DELETES headings
'''


def clean_waypoints(split_waypoints):
    temp_waypoints = split_waypoints
    for i in range(0, len(temp_waypoints)):
        '''if(i == 0 or i == len(split_waypoints)-1):
            split_waypoints[i] = split_waypoints[i][:3]
        else:'''
        digit_substr = re.findall('[^a-zA-Z]+', temp_waypoints[i])
        if (len(digit_substr) != 0):
            digit_start = temp_waypoints[i].find(digit_substr[0])
            temp_waypoints[i] = temp_waypoints[i][:digit_start]
    temp_waypoints = [x for x in temp_waypoints if len(x) > 1]
    return temp_waypoints

# TODO: Downsample track points
# def downsample(arr, size=2000):
