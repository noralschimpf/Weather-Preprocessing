from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import Global_Tools as gb
import os
#TODO: flight plan column constants


PATH_FLIGHT_PLANS = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/'
LINK_NAVAID = 'https://opennav.com/navaid/us/'
LINK_WAYPOINT = 'https://opennav.com/waypoint/US/'

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
    # TODO: Is this actually the last-filed flight plan, or a misunderstanding?
    index_last_filed = np.where(filtered_data[:, 2] == np.max(filtered_data[:, 2]))
    last_filed_entry = filtered_data[index_last_filed]

    #TODO: Parse lat/lon with openNav
    waypoints = last_filed_entry[0][3].split('.', 100)
    waypoints = gb.clean_waypoints(waypoints)
    print(waypoints)



    #TODO: Parse Trackpoint Timestamps for time column of Flightplan




