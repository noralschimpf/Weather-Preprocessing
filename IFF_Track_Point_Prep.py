import os, shutil, logging, datetime
from dateutil import parser as dparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import pandas as pd

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

    df = pd.read_csv(file, names=['callsign', 'time', 'lat', 'lon', 'alt', 'gndspeed', 'course'])
    df = df.sort_values(by='time')
    data = df.values[:, 1:5]
    del df

    # data = np.loadtxt(file, delimiter=',', usecols=(1, 2, 3, 4))
    data_slicing_incr = int(np.floor(len(data) / gb.TARGET_SAMPLE_SIZE))
    # data_slicing_incr = 0

    times, lats, lons, alts = None, None, None, None
    if (data_slicing_incr == 0):
        logging.warning(
            ' target sample size (' + str(gb.TARGET_SAMPLE_SIZE) + ') == 0; unaltered slicing')
        times = data[:, 0]
        lats = data[:, 1]
        lons = data[:, 2]
        alts = data[:, 3]

    if data_slicing_incr < 0:
        times = np.round(np.asarray(data[:, 0], dtype=np.float)).astype(np.int)
        lats = data[:, 1]
        lons = data[:, 2]
        alts = data[:, 3]

        samples_per_segment = [times[i] - times[i - 1] for i in range(1, len(times))]
        samples_total = int(np.sum(samples_per_segment))

        times_interp = np.zeros((samples_total,), dtype=np.int)
        lats_interp = np.zeros((samples_total,), dtype=np.float)
        lons_interp = np.zeros((samples_total,), dtype=np.float)
        alts_interp = np.zeros((samples_total,), dtype=np.float)

        for i in range(len(samples_per_segment)):
            bln_endpt = i == len(samples_per_segment) - 1
            sample_start = np.sum(samples_per_segment[:i], dtype=np.int)
            sample_end = np.sum(samples_per_segment[:i + 1], dtype=np.int)
            times_interp[sample_start:sample_end] = np.linspace(times[i], times[i + 1], samples_per_segment[i],
                                                                endpoint=bln_endpt)
            lats_interp[sample_start:sample_end] = np.linspace(lats[i], lats[i + 1], samples_per_segment[i],
                                                               endpoint=bln_endpt)
            lons_interp[sample_start:sample_end] = np.linspace(lons[i], lons[i + 1], samples_per_segment[i],
                                                               endpoint=bln_endpt)
            alts_interp[sample_start:sample_end] = np.linspace(alts[i], alts[i + 1], samples_per_segment[i],
                                                               endpoint=bln_endpt)
        times = times_interp
        lats = lats_interp
        lons = lons_interp
        alts = alts_interp

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
    data_frame = pd.DataFrame(save_data, columns=['times', 'lats', 'lons', 'alts'])
    save_data = data_frame.sort_values(by=['times']).values
    parent_dir = os.path.abspath(file).split('\\')[-2]
    save_date = dparse.parse(parent_dir, fuzzy=True)
    # save_date = datetime.datetime.strptime(parent_dir.split('-')[-1], '%b%d_%Y')

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
    if gb.TARGET_SAMPLE_SIZE < 0:
        logging.warning(
            ' target sample size (' + str(gb.TARGET_SAMPLE_SIZE) + ') < 0; using sampling 1 sample/sec')


    sttime = datetime.datetime.now()
    logging.info(' Starting: ' + sttime.isoformat())

    track_objs = [x for x in os.listdir() if not (x == 'Shifted' or x == 'Sorted')]
    func_process_file = partial(process_file, gb.PATH_PROJECT, gb.TARGET_SAMPLE_SIZE, PATH_FT_LOG)

    for obj in track_objs:
        if os.path.isdir(obj):
            print('Reading from ' + obj)
            os.chdir(obj)
            track_files = [x for x in os.listdir() if (x.__contains__('Flight_Track') and x.__contains__('.txt'))]
            if gb.BLN_MULTIPROCESS:
                with ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as ex:
                    return_code = ex.map(func_process_file, track_files)
            else:
                for file in track_files:
                    func_process_file(file)
            os.chdir('..')
        elif os.path.isfile(obj) and obj.__contains__('Flight_Track') and obj.__contains__('.txt'):
            func_process_file(obj)

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
