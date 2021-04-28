import numpy as np
import math
import os, re, zipfile
import pygrib
pygrib.set_definitions_path('C:\\Users\\User\\anaconda3\\envs\\pygrib\\Library\\share\\eccodes\\definitions')
#from line_profiler import LineProfiler

# Global Constants, specc'd by SHERLOC
LAT_ORIGIN = 38.
LON_ORIGIN = -98.
R_EARTH = 6370997
# TODO: control multiple lookahead values
LOOKAHEAD_SECONDS = [0.]
# Forecast refresh rate, in seconds
# Must be a multiple of 300
FORE_REFRESH_RATE = 3600

# Path / Project Vars
BLN_MULTIPROCESS = False
CUBE_SIZE = 20
TARGET_SAMPLE_SIZE = -500
PROCESS_MAX = 2
PATH_PROJECT = os.path.abspath('.')
FIGURE_FORMAT = 'png'


'''
Convert relative position to latitude/longitude coordinates for Basemap
xMeterFrom, yMeterFrom should be 1-D, lat,long returned 1-D
'''



'''def rel_to_latlong(xMeterFrom, yMeterFrom, lat_0=38., long_0=-98., rEarth=6370997.):
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

    return lat, long'''

 #TODO: REVISIT
def rel_to_latlong(xMeterFrom, yMeterFrom, lat_0=38., long_0=-98., rEarth=6370997.):
    lat_0, long_0 = lat_0*(np.pi/180), long_0*(np.pi/180)
    xMeterFrom,yMeterFrom = map(np.array, np.meshgrid(xMeterFrom,yMeterFrom))
    magnitudes, headings = np.sqrt(xMeterFrom**2 + yMeterFrom**2), np.arctan2(xMeterFrom,yMeterFrom)
    dist = (magnitudes/rEarth)
    lat_new = lat_0 + dist*np.cos(headings)
    #latnew_rad, lat0_rad = lat_new * (np.pi/180), lat_0 * (np.pi/180)

    d_psi = np.log(np.tan(np.pi/4 + lat_new/2)/np.tan(np.pi/4 + lat_0/2))

    q = np.array(d_psi)
    #q[q<=10e-12] = np.cos(q[q<=10e-12])
    #q[q > 10e-12] = (lat_new[q>10e-12] - lat_0)/q[q > 10e-12]
    q = (lat_new - lat_0)/q

    long_new = long_0 + dist*np.sin(headings)/q
    lat_new = lat_new*(180/np.pi); long_new = long_new*(180/np.pi);
    return lat_new, long_new

'''
Project heading based on lat/lon pairs a->b
alg reference: https://www.movable-type.co.uk/scripts/latlong.html
'''


def heading_a_to_b(a_lon, a_lat, b_lon, b_lat, spherical=True):
    if spherical:
        x = (math.cos(b_lat) * math.sin(a_lat)) - (math.sin(b_lat) * math.cos(a_lat) * math.cos(a_lon - b_lon))
        y = math.sin(a_lon - b_lon) * math.cos(a_lat)
        theta = math.atan2(y, x)
        heading = (theta * 180 / math.pi + 360) % 360
    else:
        delta_x = b_lon - a_lon
        delta_y = b_lat - a_lat
        theta = math.atan2(delta_y, delta_x)
        heading = (90 - theta * 180 / math.pi) % 360
    return heading


'''
Haversine formula calculates the as-the-crow-flies distance between two coordinates
return unit: kilometers
equation ref: https://www.movable-type.co.uk/scripts/latlong.html
'''


def haversine(lat2, lat1, delta_lons, rEarth):
    lat2_rad, lat1_rad, delta_lons_rad = np.radians([lat2, lat1, delta_lons])
    a = math.sin((lat2_rad - lat1_rad) / 2) ** 2 + (math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(delta_lons_rad / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return rEarth * c / 1000


'''
Parses an array of latitudes and longitudes
Returns an array of distances from the first lat/lon coordinate provided
calculates using the Haversine formula
'''


def km_between_coords(lats, lons):
    leng = min(len(lats), len(lons))
    dists = np.zeros(leng)
    for i in range(1, leng):
        dists[i] = haversine(lats[i], lats[0], lons[i] - lons[0], R_EARTH)
    return dists


"""
find the indices of local extrema (min and max)
in the input array.
"""

'''
def extrema(mat, mode='wrap', window=10):
    mn = minimum_filter(mat, size=window, mode=mode)
    mx = maximum_filter(mat, size=window, mode=mode)
    # (mat == mx) true if pixel is equal to the local max
    # (mat == mn) true if pixel is equal to the local in
    # Return the indices of the maxima, minima
    return np.nonzero(mat == mn), np.nonzero(mat == mx)
'''

'''
convert between Strings and their unicode-lists
'''


def str_to_unicode(string_in):
    string_temp = ''
    for char in string_in:
        str_dig = str(ord(char))
        str_temp = str_temp + str_dig.zfill(4 - len(str_dig))
    return str(string_temp)


def unicode_to_str(unicode_in):
    str_unicode = str(unicode_in)
    str_temp = ''
    for i in range(0, len(str_unicode) % 4):
        str_temp = str_temp + chr(str_unicode[i:i + 3])
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
            if (digit_start > 2 or digit_start <= 1):
                temp_waypoints[i] = temp_waypoints[i][:digit_start]
    temp_waypoints = [x for x in temp_waypoints if len(x) > 1]
    return temp_waypoints


'''
Returns an array of numbers parsed from a string
any length of non-numeric characters ('.' excluded) is a delimiter
'''


def parse_coords_from_str(str_in):
    arr_coords = np.zeros((3,), dtype=np.float)
    str_in_split = str_in.split(' ')
    char_sign = str_in_split[3]
    sign = 1
    if (char_sign == 'W' or char_sign == 'S'):
        sign = -1

    for item in range(len(str_in_split)):
        str_in_split[item] = str_in_split[item][:-1]
        if (item < 3):
            arr_coords[item] = sign * float(str_in_split[item])

    return arr_coords


'''
Converts an array [Degrees, Minutes, Seconds] into a single float degree
'''


def DegMinSec_to_Degree(arr_DegMinSec):
    degrees = float(arr_DegMinSec[0])
    degrees += arr_DegMinSec[1] / 60.
    degrees += arr_DegMinSec[2] / 3600.
    return degrees


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



def save_csv_by_date(PATH_TO_DATA_DIR, datetime_obj, data_to_save, save_filename, orig_filename='', bool_delete_original=False,
                     bool_append=False):
    if orig_filename=='': orig_filename = save_filename
    str_current_date = datetime_obj.isoformat()[:10]
    if not (os.listdir(PATH_TO_DATA_DIR).__contains__(str_current_date)):
        os.mkdir(PATH_TO_DATA_DIR + str_current_date)
    PATH_START_DATE = PATH_TO_DATA_DIR + str_current_date + '/' + save_filename
    np.savetxt(PATH_START_DATE, data_to_save, delimiter=',', fmt='%s')
    if bool_delete_original:
        os.remove(orig_filename)

'''
EXCLUDED LINEPROFILER
# Decorate (@profile) to generate a function profile
def profile(fnc):
    def inner(*args, **kwargs):
        lp = LineProfiler()
        lp_wrapper = lp(fnc)
        retval = lp_wrapper(*args, **kwargs)
        lp.print_stats()
        return retval

    return inner
'''