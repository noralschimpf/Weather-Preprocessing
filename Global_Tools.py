import numpy as np
import math
import os, re

# Global Constants, specc'd by SHERLOC
LAT_ORIGIN = 38.
LONG_ORIGIN = -98.
R_EARTH = 6370997

# Path / Project Vars
TARGET_SAMPLE_SIZE = 500
PATH_PROJECT = os.path.abspath('.')
SAMPLE_INTV = 1  # seconds between samples
FIGURE_FORMAT = 'png'

'''
Convert relative position to latitude/longitude coordinates for Basemap
xMeterFrom, yMeterFrom should be 1-D, lat,long returned 1-D
'''


def rel_to_latlong(xMeterFrom, yMeterFrom, lat_0=38., long_0=-90., rEarth=6370997.):
    lat, long = yMeterFrom, xMeterFrom
    if isinstance(xMeterFrom, list):
        for i in range(0, len(xMeterFrom)):
            long[i] = long_0 + (xMeterFrom[i] / rEarth) * (180 / np.pi)
    else:
        long = long_0 + (xMeterFrom / rEarth) * (180 / np.pi)
    if isinstance(yMeterFrom, list):
        for j in range(0, len(yMeterFrom)):
            lat[j] = lat_0 + (yMeterFrom[j] / rEarth) * (180 / np.pi)
    else:
        lat = lat_0 + (yMeterFrom / rEarth) * (180 / np.pi)

    return lat, long


'''
Project heading based on lat/lon pairs a->b
alg reference: https://www.movable-type.co.uk/scripts/latlong.html
'''


def heading_a_to_b(a_lon, a_lat, b_lon, b_lat, spherical=True):
    if spherical:
        x = (math.cos(b_lat) * math.sin(a_lat)) - (math.sin(b_lat) * math.cos(a_lat) * math.cos(a_lon - b_lon))
        y = math.sin(a_lon - b_lon) * math.cos(a_lat)
        theta = math.atan2(y,x)
        heading = (theta * 180 / math.pi + 360) % 360
    else:
        delta_x = b_lon - a_lon
        delta_y = b_lat - a_lat
        theta = math.atan2(delta_y, delta_x)
        heading = (90 - theta*180/math.pi) % 360
    return heading


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
convert between Strings and their unicode-lists
'''


def str_to_unicode(string_in):
    string_temp = ''
    for char in string_in:
        str_dig = str(ord(char))
        str_temp = str_temp + str_dig.zfill(4-len(str_dig))
    return str(string_temp)

def unicode_to_str(unicode_in):
    str_unicode = str(unicode_in)
    str_temp = ''
    for i in range(0,len(str_unicode)%4):
        str_temp = str_temp + chr(str_unicode[i:i+3])
    return str(str_temp)
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


'''
Sorts data into subdirectories by date
Call from within iterator (for file in os.listdir():)
   PATH_TO_DATA_DIR: Path to unsorted data ('$PROJECT_PATH/Data/IFF_Track_Points')
   datetime_obj: datetime object used to find day's directory
   data_to_save: ndarray of data to save
                 MUST BE NUMERIC
   filename: string should include file extension
                 MUST MATCH ORIGINAL FILENAME IF DELETING
   bool_delete: remove original file after saving
'''


# TODO: Append/replace file if existing
def save_csv_by_date(PATH_TO_DATA_DIR, datetime_obj, data_to_save, filename, bool_delete_original=False, bool_append=False):
    str_current_date = datetime_obj.isoformat()[:10]
    if not (os.listdir(PATH_TO_DATA_DIR).__contains__(str_current_date)):
        os.mkdir(PATH_TO_DATA_DIR + str_current_date)
    PATH_START_DATE = PATH_TO_DATA_DIR + str_current_date + '/' + filename
    np.savetxt(PATH_START_DATE, data_to_save, delimiter=',', fmt='%s')
    if bool_delete_original:
        os.remove(filename)



# TODO: Downsample track points
# def downsample(arr, size=2000):
