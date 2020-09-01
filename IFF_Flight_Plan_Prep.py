from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import Global_Tools as gb
import os, requests
from netCDF4 import num2date
from mpl_toolkits.basemap import Basemap
from matplotlib import pyplot as plt

PATH_FLIGHT_PLANS = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/'
LINK_NAVAID = 'https://opennav.com/navaid/us/'
LINK_WAYPOINT = 'https://opennav.com/waypoint/US/'
LINK_AIRPORT = 'https://opennav.com/airport/'
LEN_AIRPORT = 4
LEN_NAVAID = 3
LEN_WAYPOINT = 5

os.chdir(PATH_FLIGHT_PLANS)
Flight_Plan_Files = [x for x in os.listdir() if x.__contains__('_fp.txt')]

for file in Flight_Plan_Files:
    data_frame = pd.read_csv(file)
    data = data_frame.values


    # filter for FP entries containing a Waypoint AND Timestamp
    filter_slice1 = np.where((data[:,3] == 'Unknown'))
    filter_slice2 = np.where(data[:, 2] == 'Unknown')
    filtered_data = np.delete(data, np.append(filter_slice1, filter_slice2), axis=0)


    # Select the last Complete FP entry
    index_last_filed = np.where(filtered_data[:, 2] == np.max(filtered_data[:, 2]))
    last_filed_entry = filtered_data[index_last_filed][0]


    #Parse Airport, Waypoint, NavAid codes
    waypoints = last_filed_entry[3].split('.', 100)
    waypoints = gb.clean_waypoints(waypoints)
    print(waypoints)


    lat_waypoints = np.zeros((len(waypoints),), np.float64)
    lon_waypoints = np.zeros((len(waypoints),), np.float64)
    alt_waypoints = np.zeros((len(waypoints),), np.float64)
    time_waypoints = np.zeros((len(waypoints),), np.float64)

    #Parse lat/lon/alt? with openNav
    for i in range(len(waypoints)):
        #Open HTTP request to access waypoint page
        if (len(waypoints[i]) == LEN_AIRPORT):
            r = requests.get(LINK_AIRPORT + waypoints[i])
        elif (len(waypoints[i]) == LEN_WAYPOINT):
            r = requests.get(LINK_WAYPOINT + waypoints[i])
        elif (len(waypoints[i]) == LEN_NAVAID):
            r = requests.get(LINK_NAVAID + waypoints[i])
        else:
            print("ERR: UNKNOWN ENTRY", waypoints[i])
            exit(13)

        #Open and search HTML page in BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        results_data_rows = soup.find_all('tr')

        str_lat = ''
        str_lon = ''
        str_alt = ''
        lat, lon, alt = 0., 0., 0.

        #Find and Convert Coordinates
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

        #TODO: Ask Zhe/Li if there is altitude data in flight plans
        if(alt == 0.):
            alt_waypoints[i] = 35000.
        else:
            alt_waypoints[i] = 0.

        #TODO: Ask Zhe/Li if Arrival/Departure times are included in flightplan/summary


        print(waypoints[i], '\t', str(lat), '\t', str(lon), '\t', str(alt))

    # Waypoint Linear Interpolation
    slice_size = int(np.ceil(gb.TARGET_SAMPLE_SIZE / len(waypoints)))
    sample_size = slice_size*len(waypoints)

    lat_coord = np.zeros((sample_size,), dtype=np.float)
    lon_coord = np.zeros((sample_size,), dtype=np.float)
    alt_coord = np.zeros((sample_size,), dtype=np.float)
    time_coord = np.zeros((sample_size,), dtype=np.float)

    for i in range(0, len(waypoints)):
        lat_coord[slice_size*i:slice_size*(i+1)] = np.linspace(lat_waypoints[i-1], lat_waypoints[i], slice_size)
        lon_coord[slice_size*i:slice_size*(i+1)] = np.linspace(lon_waypoints[i-1], lon_waypoints[i], slice_size)
        alt_coord[slice_size*i:slice_size*(i+1)] = np.linspace(alt_waypoints[i-1], alt_waypoints[i], slice_size)
        time_coord[slice_size*i:slice_size*(i+1)] = np.linspace(time_waypoints[i-1], time_waypoints[i], slice_size)
    #TODO: Address redundant entries without deleting array (rework linspace calls)
    for i in range(1, len(waypoints)):
        lat_coord = np.delete(lat_coord, (slice_size-1)*i)
        lon_coord = np.delete(lon_coord, slice_size*i)
        alt_coord = np.delete(alt_coord, slice_size*i)
        time_coord = np.delete(time_coord, slice_size*i)

    # Get Datetime Object of last filed entry
    # TODO: Get Datetime for Departure
    filed_time = last_filed_entry[2]
    filed_date = num2date(filed_time, units='Seconds since 1970-01-01T00:00:00Z', calendar='gregorian')

    data = np.vstack((time_coord, lat_coord, lon_coord, alt_coord)).T
    gb.save_csv_by_date(PATH_FLIGHT_PLANS + 'Sorted/', filed_date, data, file)

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

    m.scatter(lon_coord, lat_coord, marker=',', color='red', latlon=True, )
    m.plot(lon_waypoints, lat_waypoints, marker='.', color='blue', latlon=True)
    plt.show(block=False)
    PATH_FLIGHT_PLAN_FIGS = gb.PATH_PROJECT + '/Output/Flight Plans/Plots/' + file[:-3] + gb.FIGURE_FORMAT
    plt.savefig(PATH_FLIGHT_PLAN_FIGS, dpi=200)
    plt.close()

    print(file, ' read')




