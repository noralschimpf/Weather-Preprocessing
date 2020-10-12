import os, shutil, logging, datetime
from concurrent.futures import ProcessPoolExecutor
from functools import partial

os.environ['PROJ_LIB'] = 'C:\\Users\\natha\\anaconda3\\envs\\WeatherPreProcessing\\Library\\share'
"""
Read Flight Track-Point Files and Plot in Basemap
"""


import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from mpl_toolkits.basemap import Basemap, addcyclic
from matplotlib import dates, cm
from netCDF4 import Dataset, num2date
import Global_Tools as gb


# create Basemap instance
'''
m = Basemap(projection='merc', llcrnrlat=24., urcrnrlat=50., \
            llcrnrlon=-123., urcrnrlon=-67., resolution='c', \
            rsphere=gb.R_EARTH, lat_0=40., lon_0=-98., lat_ts=20.)

# draw boundary, fill continents, draw costlines, draw parrallels, draw meridians
m.drawmapboundary()
m.drawcoastlines(linewidth=1.25)
m.drawparallels(np.arange(10, 60, 10), labels=[1, 0, 0, 0])
m.drawmeridians(np.arange(-160, -50, 10), labels=[0, 0, 0, 1])
'''

#file is local reference, program must enter containing directory
def process_file(PATH_PROJECT : str, TARGET_SAMPLE_SIZE : int, file : str):
    data = np.loadtxt(file, delimiter=',', usecols=(1, 2, 3, 4))
    data_slicing_incr = int(np.floor(len(data) / gb.TARGET_SAMPLE_SIZE))
    #data_slicing_incr = 0

    times, lats, lons, alts = None, None, None, None
    if (data_slicing_incr <= 0):
        logging.warning('WARNING: ' + str(file) + ' length (' + str(len(data)) + ') is too short for target size ' + str(TARGET_SAMPLE_SIZE))
        times = data[:, 0]
        lats = data[:, 1]
        lons = data[:, 2]
        alts = data[:, 3]

    else:
        data_sliced = data[::data_slicing_incr]
        times = data_sliced[:, 0]
        lats = data_sliced[:, 1]
        lons = data_sliced[:, 2]
        alts = data_sliced[:, 3]

        # generate meshgrid to plot contour-map
        '''
        lonsm, latsm = np.meshgrid(lons, lats)
        altsm = np.zeros(np.shape(latsm))
        for i in range(0,len(lats)):
            altsm[i][i] = alts[i]
        m.contour(lonsm, latsm, altsm, latlon=True, cmap=cm.coolwarm)
        '''

    # Sort and Save file by timestamp
    save_data = np.vstack((times, lats, lons, alts)).T
    timestamp = num2date(times[0], units="seconds since 1970-01-01T00:00:00", calendar="gregorian")
    PATH_TO_SORTED_TRACKPOINTS = PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/'
    modified_filename = file.split('_')
    if not (modified_filename[0] == 'Flight'):
        modified_filename.pop(0)
    modified_filename = '_'.join(modified_filename)
    gb.save_csv_by_date(PATH_TO_SORTED_TRACKPOINTS, timestamp, save_data, modified_filename, orig_filename=file,
                        bool_delete_original=True)
    print('processed ' + str(file))
    return 0


if __name__ == '__main__':
    PATH_TRACK_POINTS = gb.PATH_PROJECT + '/data/IFF_Track_Points/'
    logging.basicConfig(filename=gb.PATH_PROJECT + '/Output/Flight Tracks/FT_Prep.log', level=logging.INFO)

    # Open, plot, and downsample each flight-track CSV
    os.chdir(PATH_TRACK_POINTS)

    sttime = datetime.datetime.now()
    logging.info('Starting: ' + sttime.isoformat())

    track_objs = [x for x in os.listdir() if not (x == 'Shifted' or x == 'Sorted')]
    func_process_file = partial(process_file, gb.PATH_PROJECT, gb.TARGET_SAMPLE_SIZE)

    for obj in track_objs:
        if os.path.isdir(obj):
            os.chdir(obj)
            track_files = [x for x in os.listdir() if (x.__contains__('Flight_Track') and x.__contains__('.txt'))]
            #with ProcessPoolExecutor(max_workers=6) as ex:
            #    return_code = ex.map(func_process_file, track_files)
            for file in track_files:
                func_process_file(file)
            os.chdir('..')
        elif os.path.isfile(obj) and obj.__contains__('Flight_Track') and obj.__contains__('.txt'):
            process_file(obj)

        # plot show
        '''
        plt.title('JFK-LAX Flights, Mercator Projection')
        #m.colorbar(mappable=None, location='right', size='5%', pad='1%')
        plt.show(block=False)
        plt.savefig("Output/IFF_Flight_Track.png", format='png')
        plt.close()
        '''

    os.chdir(PATH_TRACK_POINTS)
    print('done. deleting empty folders')
    dirs = [x for x in os.listdir() if os.path.isdir(x)]
    for dr in dirs:
        files = os.listdir(dr)
        if (len(files) == 0 or (len(files) == 1 and files[0].__contains__('Summary'))):
            shutil.rmtree(dr)
        else:
            logging.warning('WARNING: ' + str(dr) + ' may contain unresolved flight tracks')

    edtime = datetime.datetime.now()
    delta = edtime - sttime
    logging.info('Done: ' + edtime.isoformat())
    logging.info('Execution Time: ' + delta.total_seconds())