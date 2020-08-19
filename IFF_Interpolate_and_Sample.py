import Global_Tools as gb
import numpy as np
import pandas as pd
import os, csv, time


PATH_SORTED_TRACK = gb.PATH_PROJECT + '/Data/IFF_Track_Points/Sorted'
PATH_SORTED_PLAN = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/Sorted'

os.chdir(gb.PATH_PROJECT + '/Data')




# Reformat callsign (to Unicode) and reduce dimension
#TODO: Refactor into prep.py's
for dir in ['IFF_Track_Points']: #'IFF_Flight_Plans'
    os.chdir(dir + '/Sorted')
    for date in os.listdir():
        os.chdir(date)
        for file in os.listdir():
            data_frame = pd.read_csv(file)
            data = data_frame.values[:]
            for i in range(0, len(data[:,0])):
                data[i][0] = gb.to_unicode(data[i][0])
            data = np.delete(data,[5,6],1)
            np.savetxt(file + '.modified', data, delimiter=',', fmt='%s')

            #data.tofile(file + ".modified", sep=',')
            print(file + "Scrubbed!\t" + str(time.time()))






#TODO Interpolate Flightplan / Trackpoint coordinates



#TODO: Strip Extraneous Data


