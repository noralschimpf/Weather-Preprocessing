import os, shutil, logging, datetime
from concurrent.futures import ProcessPoolExecutor
from functools import partial

os.environ['PROJ_LIB'] = 'C:\\Users\\natha\\anaconda3\\envs\\WeatherPreProcessing\\Library\\share'
"""
Read Flight Track-Point Files and Plot in Basemap
"""

import numpy as np
import matplotlib.pyplot as plt
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


# file is local reference, program must enter containing directory
def process_file(PATH_PROJECT: str, TARGET_SAMPLE_SIZE: int, PATH_LOG: str, file: str):
    logging.basicConfig(filename=PATH_LOG, filemode='a', level=logging.INFO)

    print('processing ' + file)

    data = np.loadtxt(file, delimiter=',', usecols=(1, 2, 3, 4))
    data_slicing_incr = int(np.floor(len(data) / gb.TARGET_SAMPLE_SIZE))
    # data_slicing_incr = 0

    times, lats, lons, alts = None, None, None, None
    if (data_slicing_incr == 0):
        logging.warning(' ' + str(file) + ' length (' + str(len(data)) + ') is too short for target size ' + str(
            TARGET_SAMPLE_SIZE))
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
    save_data = save_data[save_data[:, 0].argsort()]
    parent_dir = os.path.abspath(file).split('\\')[-2]
    save_date = datetime.datetime.strptime(parent_dir.split('-')[-1], '%b%d_%Y')

    PATH_TO_SORTED_TRACKPOINTS = PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/'
    modified_filename = file.split('_')
    if not (modified_filename[0] == 'Flight'):
        modified_filename.pop(0)
    modified_filename = '_'.join(modified_filename)
    gb.save_csv_by_date(PATH_TO_SORTED_TRACKPOINTS, save_date, save_data, modified_filename, orig_filename=file,
                        bool_delete_original=True)
    print('processed ' + str(file))
    return 0


def main():
    PATH_TRACK_POINTS = gb.PATH_PROJECT + '/data/IFF_Track_Points/'
    PATH_FT_LOG = gb.PATH_PROJECT + '/Output/Flight Tracks/FT_Prep.log'
    if os.path.isfile(PATH_FT_LOG):
        os.remove(PATH_FT_LOG)
    logging.basicConfig(filename=PATH_FT_LOG, filemode='w', level=logging.INFO)

    # Open, plot, and downsample each flight-track CSV
    os.chdir(PATH_TRACK_POINTS)
    if gb.TARGET_SAMPLE_SIZE <= 0:
        logging.warning(
            ' target sample size (' + str(gb.TARGET_SAMPLE_SIZE) + ') <= 0; using default (unaltered) sampling')

    sttime = datetime.datetime.now()
    logging.info(' Starting: ' + sttime.isoformat())

    track_objs = [x for x in os.listdir() if not (x == 'Shifted' or x == 'Sorted')]
    func_process_file = partial(process_file, gb.PATH_PROJECT, gb.TARGET_SAMPLE_SIZE, PATH_FT_LOG)

    for obj in track_objs:
        if os.path.isdir(obj):
            print('Reading from ' + obj)
            os.chdir(obj)
            track_files = [x for x in os.listdir() if (x.__contains__('Flight_Track') and x.__contains__('.txt'))]
            # with ProcessPoolExecutor(max_workers=6) as ex:
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
            logging.warning(' ' + str(dr) + ' may contain unresolved flight tracks')

    edtime = datetime.datetime.now()
    delta = edtime - sttime
    logging.info(' Done: ' + edtime.isoformat())
    logging.info(' Execution Time: ' + str(delta.total_seconds()) + ' s')
    print('Execution complete. Check log file (' + PATH_FT_LOG + ') for details')


if __name__ == '__main__':
    main()
