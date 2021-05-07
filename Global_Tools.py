import numpy as np
import pandas as pd
import math
import os, re, zipfile
import pygrib
pygrib.set_definitions_path('C:\\Users\\User\\anaconda3\\envs\\pygrib\\Library\\share\\eccodes\\definitions')
#from line_profiler import LineProfiler
import utm
from numba import jit

# Global Constants, specc'd by SHERLOC
LAT_ORIGIN = 38.
LON_ORIGIN = -98.
R_EARTH = 6370997
LOOKAHEAD_SECONDS = [0.]
# Forecast refresh rate, in seconds
# Must be a multiple of 300
FORE_REFRESH_RATE = 3600

# Path / Project Vars
BLN_MULTIPROCESS = False
CUBE_SIZE = 20
TARGET_SAMPLE_SIZE = -500
PROCESS_MAX = 12
PATH_PROJECT = os.path.abspath('.')
FIGURE_FORMAT = 'png'


def rel_to_latlong(xMeterFrom, yMeterFrom, lat_0=38., long_0=-98., rEarth=R_EARTH):
    '''
    Convert relative position to latitude/longitude coordinates for Basemap
    xMeterFrom, yMeterFrom should be 1-D, lat,long returned 1-D
    '''
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

def longrange_latlon_to_utm(lats: np.array, lons: np.array):
    '''
    Generates a UTM Mapping of the Gridded Data
    :param lats: 2D Array of Gridded Data Latitudes
    :param lons: 2D Array of Gridded Data Longitudes
    :return dict_utmcoords: Dictionary sorted by UTM zone, each containing the relevant lats/lons as Northings/Eastings
    :return dict_latlon_traceback: Dictionary by UTM zone, containing the corresponding lat/lon idxs for each N/E pair
    :return df_verification: DataFrame containing Each UTM zone and their latitude and longitude range
    '''
    LATS_MIN, LATS_MAX = -72., 72.
    assert lats.min() > LATS_MIN, 'smallest lattitude {:.3f} exceeds UTM boundaries (-72 N\N{Degree Sign})'.format(lats.min())
    assert lats.max() < LATS_MAX, 'largest lattitude {:.3f} exceeds UTM boundaries (72 N\N{Degree Sign})'.format(lats.max())

    # sort coords by lon
    lons_idxs = np.indices(lons.shape)

    # lat[x,y], lons[x,y] == coords[:, x*lats.shape[1]+y]
    coords= np.array([lons.flatten(), lats.flatten()])
    #[lon/lat, axis0/1, flattened_2darr]
    coords_idxs = lons_idxs.reshape(2,-1)

    idxsort = np.argsort(coords, axis=1)
    coordsort = np.stack([coords[:,idxsort[0,idx]] for idx in range(coords.shape[1])]).T
    coords_idxs_sort = np.stack([coords_idxs[:,idxsort[0,idx]] for idx in range(coords_idxs.shape[1])]).T

    # split (lats, lons) into 6 degree longitude groupings
    cutoffs = np.arange(-180,186,6)
    cutoff_idxs = []
    for x in cutoffs:
        if x >= coordsort[0].min() and x <= coordsort[0].max():
            posarr = (coordsort[0] - x)[coordsort[0] - x >= 0]

            cutoff_idxs.append(np.where(coordsort[0]-x == posarr.min())[0][-1])
    list_longrps = np.split(coordsort, cutoff_idxs, axis=1)
    # list_longrps[grp][x,y] == coords[0,list_longrps_idxs[grp][0,x]*lats.shape[1] + list_longrps_idxs[grp][1,y]]
    list_longrps_idxs = np.split(coords_idxs_sort, cutoff_idxs,axis=1)

    #Split groupings into 8 degree latitude grouping
    subgroupings = []
    subgroupings_idxs = []

    for grp_idx in range(len(list_longrps)):
        idxsort = np.argsort(list_longrps[grp_idx], axis=1)
        grpsort = np.stack([list_longrps[grp_idx][:,idxsort[1,idx]] for idx in range(list_longrps[grp_idx].shape[1])]).T
        grpsort_idxs = np.stack([list_longrps_idxs[grp_idx][:,idxsort[1,idx]] for idx in range(list_longrps_idxs[grp_idx].shape[1])]).T

        cutoffs = np.arange(-72,80,8)
        cutoff_idxs = []
        for x in cutoffs:
            if x >= grpsort[1].min() and x <= grpsort[1].max():
                posarr = (grpsort[1] - x)[grpsort[1] - x >= 0]
                cutoff_idxs.append(np.where(grpsort[1]-x == posarr.min())[0][-1])
        subgroupings.extend(np.split(grpsort, cutoff_idxs, axis=1))
        subgroupings_idxs.extend(np.split(grpsort_idxs, cutoff_idxs, axis=1))

    # convert each group to array and append to dict, key 'zonechar-zonenum'
    dict_utmcoords = {}
    dict_latlon_traceback = {}
    df_verification = pd.DataFrame()

    for grp_idx in range(len(subgroupings)):
        if not len(subgroupings[grp_idx]) == 0:
            eastings, northings, zonenum, zonechar = utm.from_latlon(subgroupings[grp_idx][1],subgroupings[grp_idx][0])
            assert len(eastings) == subgroupings_idxs[grp_idx].shape[1], "UTM  and latlon grouping coordinates mismatch"
            grpkey = '{}-{}'.format(zonechar,zonenum)
            dict_utmcoords[grpkey] = (eastings, northings)
            dict_latlon_traceback[grpkey] = subgroupings_idxs[grp_idx]
            print('{}-{}\t{:.6f}-{:.6f}\t{:.6f}-{:.6f}'.format(zonechar, zonenum,subgroupings[grp_idx][0].min(),
                       subgroupings[grp_idx][0].max(),subgroupings[grp_idx][1].min(), subgroupings[grp_idx][1].max()))
            d = {'UTM Zone': grpkey, 'Lat Min': subgroupings[grp_idx][1].min(), 'Lat Max': subgroupings[grp_idx][1].max(),
                 'Lon Min': subgroupings[grp_idx][0].min(), 'Lon Max': subgroupings[grp_idx][0].max()}
            df_verification = df_verification.append(d, ignore_index=True)
    return dict_utmcoords, dict_latlon_traceback, df_verification


@jit(nopython=True)
def latlon_unitsteps(lat, lon, heading_degrees, dist_m=1500, rEarth = R_EARTH):
    dist = dist_m/rEarth
    heading = np.radians(heading_degrees)
    lat_step = dist*np.cos(heading)
    lat_new = lat + lat_step
    d_psi = np.log(np.tan(np.pi/4 + lat_new/2)/np.tan(np.pi/4 + lat/2))
    q = np.array(d_psi)
    q = (lat_new - lat)/q
    lon_step = dist*np.sin(heading)/q
    return np.degrees(np.abs(lat_step)), np.degrees(np.abs(lon_step))

@jit(nopython=True)
def heading_a_to_b(a_lon, a_lat, b_lon, b_lat, spherical=True):
    '''
    Project heading based on lat/lon pairs a->b
    alg reference: https://www.movable-type.co.uk/scripts/latlong.html
    '''
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


@jit(nopython=True, parallel=True, nogil=True)
def haversine(lat2: float, lat1: np.array, delta_lons: np.array, rEarth: int = R_EARTH):
    '''
    Haversine formula calculates the as-the-crow-flies distance between two coordinates
    return unit: kilometers
    equation ref: https://www.movable-type.co.uk/scripts/latlong.html
    '''
    lat2_rad = np.radians(lat2)
    lat1_rad = np.radians(lat1)
    delta_lons_rad = np.radians(delta_lons)
    a = np.sin((lat2_rad - lat1_rad) / 2) ** 2 + (np.cos(lat1_rad) * np.cos(lat2_rad) * (np.sin(delta_lons_rad / 2) ** 2))
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return rEarth * c / 1000


def utm_dist(target_N, target_E, nda_N, nda_E):
    '''
    Calculates the distance between mercator points, where nda_N and nda_E can be broadcasted as arrays
    distance is simplified as pythagorean
    :return:
    dists: ndarray of mercator distances to reach (target_N, target_E)
    '''
    dists = np.sqrt(np.square(nda_N - target_N) + np.square(nda_E - target_E))
    return dists


def km_between_coords(lats, lons):
    '''
    Parses an array of latitudes and longitudes
    Returns an array of distances from the first lat/lon coordinate provided
    calculates using the Haversine formula
    '''
    leng = min(len(lats), len(lons))
    dists = np.zeros(leng)
    for i in range(1, leng):
        dists[i] = haversine(lats[i], lats[0], lons[i] - lons[0], R_EARTH)
    return dists




'''
def extrema(mat, mode='wrap', window=10):
    """
    find the indices of local extrema (min and max)
    in the input array.
    """
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


def clean_waypoints(split_waypoints):
    '''
    Returns searchable NavAid and Waypoint callsigns for OpenNav
    DELETES headings
    '''
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


def parse_coords_from_str(str_in):
    '''
    Returns an array of numbers parsed from a string
    any length of non-numeric characters ('.' excluded) is a delimiter
    '''
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


def DegMinSec_to_Degree(arr_DegMinSec):
    '''
    Converts an array [Degrees, Minutes, Seconds] into a single float degree
    '''
    degrees = float(arr_DegMinSec[0])
    degrees += arr_DegMinSec[1] / 60.
    degrees += arr_DegMinSec[2] / 3600.
    return degrees


def save_csv_by_date(PATH_TO_DATA_DIR, datetime_obj, data_to_save, save_filename, orig_filename='', bool_delete_original=False,
                     bool_append=False):
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
    if orig_filename=='': orig_filename = save_filename
    str_current_date = datetime_obj.isoformat()[:10]
    if not (os.listdir(PATH_TO_DATA_DIR).__contains__(str_current_date)):
        os.mkdir(PATH_TO_DATA_DIR + str_current_date)
    PATH_START_DATE = PATH_TO_DATA_DIR + str_current_date + '/' + save_filename
    np.savetxt(PATH_START_DATE, data_to_save, delimiter=',', fmt='%s')
    if bool_delete_original:
        os.remove(orig_filename)


'''# EXCLUDED LINEPROFILER
# Decorate (@profile) to generate a function profile
def profile(fnc):
    def inner(*args, **kwargs):
        lp = LineProfiler()
        lp_wrapper = lp(fnc)
        retval = lp_wrapper(*args, **kwargs)
        lp.print_stats()
        return retval

    return inner'''