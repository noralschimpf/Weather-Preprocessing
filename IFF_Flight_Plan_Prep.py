from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import Global_Tools as gb
import os, requests, shutil
from netCDF4 import num2date
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import datetime
import logging
from mpl_toolkits.basemap import Basemap
from matplotlib import pyplot as plt


def process_file(PATH_PROJECT, PATH_FLIGHT_PLANS, LINK_NAVAID, LINK_WAYPOINT,
                 LINK_AIRPORT, LEN_NAVAID, LEN_WAYPOINT, LEN_AIRPORT, file):
    data_frame = pd.read_csv(file)
    data = data_frame.values

    # filter for FP entries containing a Waypoint AND Timestamp
    filter_slice1 = np.where((data[:, 0] == 'Unknown'))
    filter_slice2 = np.where(data[:, 2] == 'Unknown')
    filter_slice3 = np.where(pd.isnull(data[:, 0]))
    filter_slice4 = np.where(pd.isnull(data[:, 2]))
    filter = np.np.hstack((filter_slice1, filter_slice2, filter_slice3, filter_slice4))
    filtered_data = np.delete(data, filter, axis=0)

    # Select the last Complete FP entry
    index_last_filed = np.where(filtered_data[:, 0] == np.max(filtered_data[:, 0]))
    index_first_filed = np.where(filtered_data[:, 0] == np.min(filtered_data[:, 0]))
    first_filed_entry = filtered_data[index_first_filed][0]
    last_filed_entry = filtered_data[index_last_filed][0]

    # Search for track-point file
    trk_time, trk_lat, trk_lon = None, None, None
    bln_trk_found = False
    first_filed_time = np.float64(first_filed_entry[0])
    last_filed_time = np.float64(last_filed_entry[0])
    first_filed_date = num2date(first_filed_time, units='Seconds since 1970-01-01T00:00:00Z', calendar='gregorian')
    last_filed_date = num2date(last_filed_time, units='Seconds since 1970-01-01T00:00:00Z', calendar='gregorian')

    modified_filename = file.split('_')
    if not (modified_filename[0] == 'Flight'): modified_filename.pop(0)
    modified_filename = '_'.join(modified_filename)
    PATH_TRACK_POINT = PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/' + first_filed_date.isoformat()[:10] + \
                       '/' + modified_filename.replace('Flight_Plan', 'Flight_Track')
    if not (os.path.isfile(PATH_TRACK_POINT)):
    #    PATH_TRACK_POINT = PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/' + first_filed_date.isoformat()[:10] + \
    #                       '/' + modified_filename.replace('Flight_Plan', 'Flight_Track')
    #    if not (os.path.isfile(PATH_TRACK_POINT)):
        print("WARNING: ", PATH_TRACK_POINT.split('/')[-1], "not found on ", last_filed_date.isoformat()[:10], "; cannot associate timestamps")
        return -1
    if os.path.isfile(PATH_TRACK_POINT):
        bln_trk_found = True
        trk_data = np.loadtxt(PATH_TRACK_POINT, delimiter=',', usecols=(0, 1, 2))
        trk_time = trk_data[:, 0]
        trk_lat = trk_data[:, 1]
        trk_lon = trk_data[:, 2]

    str_waypoints = first_filed_entry[2]
    str_final_waypoints = last_filed_entry[2]
    waypoints = gb.clean_waypoints(str_waypoints.split('.', 100))
    '''
    # Concatenate and Parse Airport, Waypoint, NavAid codes
    str_all_waypoints = filtered_data[:,3]
    for entry in range(len(str_all_waypoints)):
        unique_entry = False
        entry_waypoints = str_all_waypoints[entry].split('.', 100)
        entry_waypoints = gb.clean_waypoints(entry_waypoints)
        for wpt in range(len(entry_waypoints)):
            if(not waypoints.__contains__(entry_waypoints[wpt])):
                waypoints.append(entry_waypoints[wpt])
                unique_entry = True
        if(unique_entry):
            print(entry_waypoints)
    '''
    #print(waypoints)

    lat_waypoints = np.zeros((len(waypoints),), np.float64)
    lon_waypoints = np.zeros((len(waypoints),), np.float64)
    alt_waypoints = np.zeros((len(waypoints),), np.float64)
    time_waypoints = np.zeros((len(waypoints),), np.float64)

    # Parse lat/lon/alt? with openNav
    for i in range(len(waypoints)):
        # Open HTTP request to access waypoint page
        if len(waypoints[i]) == LEN_AIRPORT:
            r = requests.get(LINK_AIRPORT + waypoints[i])
        elif len(waypoints[i]) == LEN_WAYPOINT:
            r = requests.get(LINK_WAYPOINT + waypoints[i])
        elif len(waypoints[i]) == LEN_NAVAID:
            r = requests.get(LINK_NAVAID + waypoints[i])
        else:
            print("ERR: UNKNOWN ENTRY", waypoints[i])
            exit(13)

        # Open and search HTML page in BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        results_data_rows = soup.find_all('tr')

        str_lat = ''
        str_lon = ''
        str_alt = ''
        lat, lon, alt = 0., 0., 0.

        # Find and Convert Coordinates
        for tag_result in results_data_rows:
            str_result = tag_result.text
            if str_result.__contains__('Latitude'):
                str_lat = str_result[len('Latitude'):]
                DegMinSec_lat = gb.parse_coords_from_str(str_lat)
                lat = gb.DegMinSec_to_Degree(DegMinSec_lat)
            elif str_result.__contains__('Longitude'):
                str_lon = str_result[len('Longitude'):]
                DegMinSec_lon = gb.parse_coords_from_str(str_lon)
                lon = gb.DegMinSec_to_Degree(DegMinSec_lon)
            elif str_result.__contains__('Elevation'):
                str_alt = str_result[len('Elevation'):]
                alt = float(str_alt.split(' ')[0])

        lat_waypoints[i] = lat
        lon_waypoints[i] = lon

        # Assign approx. Flight Altitude
        if (alt == 0.):
            alt_waypoints[i] = 35000.
        else:
            alt_waypoints[i] = alt

        # print(waypoints[i], '\t', "{:10.5f}".format(lat_waypoints[i]), '\t', "{:10.5f}".format(lon_waypoints[i]),
        #      '\t', str(alt_waypoints[i]))

    # time assignment
    knowntimes = np.array((trk_time[0], trk_time[-1]))
    interp_dists = gb.km_between_coords(lat_waypoints, lon_waypoints)
    dists = np.array((interp_dists[0], interp_dists[-1]))
    time_waypoints = np.interp(interp_dists, dists, knowntimes)

    # Waypoint Linear Interpolation
    slice_size = int(np.ceil(gb.TARGET_SAMPLE_SIZE / (len(waypoints) - 1)))
    sample_size = slice_size * (len(waypoints) - 1)

    lat_coord = np.zeros((sample_size,), dtype=np.float)
    lon_coord = np.zeros((sample_size,), dtype=np.float)
    alt_coord = np.zeros((sample_size,), dtype=np.float)
    time_coord = np.zeros((sample_size,), dtype=np.float)

    for i in range(1, len(waypoints)):
        if i < len(waypoints) - 1:
            lon_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(lon_waypoints[i - 1], lon_waypoints[i],
                                                                         slice_size, endpoint=False)
            lat_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(lat_waypoints[i - 1], lat_waypoints[i],
                                                                         slice_size, endpoint=False)
            alt_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(alt_waypoints[i - 1], alt_waypoints[i],
                                                                         slice_size, endpoint=False)
            time_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(time_waypoints[i - 1], time_waypoints[i],
                                                                          slice_size, endpoint=False)
        else:
            lon_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(lon_waypoints[i - 1], lon_waypoints[i],
                                                                         slice_size, endpoint=True)
            lat_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(lat_waypoints[i - 1], lat_waypoints[i],
                                                                         slice_size, endpoint=True)
            alt_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(alt_waypoints[i - 1], alt_waypoints[i],
                                                                         slice_size, endpoint=True)
            time_coord[(i - 1) * slice_size:i * slice_size] = np.linspace(time_waypoints[i - 1], time_waypoints[i],
                                                                          slice_size, endpoint=True)

    data = np.vstack((time_coord, lat_coord, lon_coord, alt_coord)).T
    gb.save_csv_by_date(PATH_FLIGHT_PLANS + 'Sorted/', first_filed_date, data, modified_filename, orig_filename=file,
                        bool_delete_original=False)

    '''
    # Plot Flight Plan to Verify using Basemap
    m = Basemap(width=12000000, height=9000000, rsphere=gb.R_EARTH,
                resolution='l', area_thresh=1000., projection='lcc',
                lat_0=gb.LAT_ORIGIN, lon_0=gb.LONG_ORIGIN)
    m.drawcoastlines()
    Parallels = np.arange(0., 80., 10.)
    Meridians = np.arange(10., 351., 20.)

    # Labels = [left,right,top,bottom]
    m.drawparallels(Parallels, labels=[False, True, True, False])
    m.drawmeridians(Meridians, labels=[True, False, False, True])
    fig = plt.gca()

    m.scatter(lon_coord, lat_coord, marker='.', color='red', latlon=True, )
    #lbl_x, lbl_y  = m(lon_waypoints, lat_waypoints)
    #for i in range(len(waypoints)):
    #    plt.annotate(waypoints[i], (lbl_x[i], lbl_y[i]))
    m.plot(lon_waypoints, lat_waypoints, marker='.', color='blue', latlon=True)
    plt.show(block=False)
    PATH_FLIGHT_PLAN_FIGS = gb.PATH_PROJECT + '/Output/Flight Plans/Plots/' + file[:-3] + gb.FIGURE_FORMAT
    plt.savefig(PATH_FLIGHT_PLAN_FIGS, dpi=300)
    plt.close()
    '''

    #print(file, ' read')


if __name__ == '__main__':
    PATH_FLIGHT_PLANS = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/'
    LINK_NAVAID = 'https://opennav.com/navaid/us/'
    LINK_WAYPOINT = 'https://opennav.com/waypoint/US/'
    LINK_AIRPORT = 'https://opennav.com/airport/'
    LEN_AIRPORT = 4
    LEN_NAVAID = 3
    LEN_WAYPOINT = 5

    logging.basicConfig(filename=gb.PATH_PROJECT + '/Output/Flight Plans/FP_Prep.log', level=logging.INFO)
    sttime = datetime.datetime.now()
    logging.info('Started:\t' + sttime.isoformat())
    os.chdir(PATH_FLIGHT_PLANS)
    data_dirs = [x for x in os.listdir() if not (x == 'Shifted' or x == 'Sorted')]
    for directory in data_dirs:
        os.chdir(directory)
        Flight_Plan_Files = [x for x in os.listdir() if (x.__contains__('Flight_Plan') and x.__contains__('.txt'))]

        files = os.listdir()
        # files = [os.path.abspath('.') + '/' + file for file in files]

        for file in Flight_Plan_Files:
             process_file(gb.PATH_PROJECT, PATH_FLIGHT_PLANS, LINK_NAVAID, LINK_WAYPOINT, LINK_AIRPORT, LEN_NAVAID ,
                          LEN_WAYPOINT, LEN_AIRPORT, file)
        func_process_file = partial(process_file, gb.PATH_PROJECT, PATH_FLIGHT_PLANS, LINK_NAVAID, LINK_WAYPOINT,
                                    LINK_AIRPORT, LEN_NAVAID, LEN_WAYPOINT, LEN_AIRPORT)
        #with ProcessPoolExecutor(max_workers=6) as ex:
        #    exit_code = ex.map(func_process_file, files)

        os.chdir('..')
    os.chdir(PATH_FLIGHT_PLANS)
    print('Deleting empty Folders')
    dirs = [x for x in os.listdir() if os.path.isdir(x)]
    for dr in dirs:
        files = os.listdir(dr)
        if len(files) == 0 or (len(files) == 1 and files[0].__contains__('Summary')):
            shutil.rmtree(dr)
        else:
            logging.warning('WARNING: ' + str(dr) + ' may contain unresolved flight plans')
    edtime = datetime.datetime.now()
    delta = edtime - sttime
    logging.info('done: ' + edtime.isoformat())
    logging.info('execution time: ' + delta.total_seconds() + ' s')