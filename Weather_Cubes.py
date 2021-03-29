import Global_Tools as gb
import numpy as np
import math, os, datetime, logging
from mpl_toolkits.basemap import Basemap
from matplotlib import pyplot as plt
from netCDF4 import Dataset, num2date, date2num
from dateutil import parser as dparser
from concurrent.futures import ProcessPoolExecutor
from functools import partial
'''
EXCLUDE PROFILER
from Global_Tools import profile
'''

def process_flight_plan(var, PATH_DATA_SORTED, PATH_OUTPUT, lons, lats, USES_CUR, USES_FORE, fore_start, PATH_LOG,
                        file):

    logging.basicConfig(filename=PATH_LOG, filemode='a', level=logging.INFO)
    # Load Flight Data and EchoTop Coordinates
    flight_tr = np.loadtxt(file, delimiter=',')
    flt_time = flight_tr[:, 0]
    flt_lat = flight_tr[:, 1]
    flt_lon = flight_tr[:, 2]

    relevant_data = np.zeros((len(gb.LOOKAHEAD_SECONDS), len(lats), len(lons)), dtype=float)
    idx_cur_data, idx_forecast_times = None, [-1] * (len(gb.LOOKAHEAD_SECONDS) - fore_start)

    # Generate list of EchoTop Report Times
    flt_startdate = num2date(flt_time[0], units='seconds since 1970-01-01T00:00:00', calendar='gregorian')
    flt_enddate = num2date(flt_time[-1], units='seconds since 1970-01-01T00:00:00', calendar='gregorian')
    cur_timestamps, fore_timestamps, idx_fore_day_split, idx_cur_day_split = None, None, None, None

    if USES_FORE:
        PATH_DATA_FORE_DATE = [PATH_DATA_SORTED + flt_startdate.isoformat()[:10] + '/Forecast/',
                                  PATH_DATA_SORTED + flt_enddate.isoformat()[:10] + '/Forecast/']
        if not os.path.isdir(PATH_DATA_FORE_DATE):
            logging.error(' EchoTop Forecast Data Does Not Cover ' + file + '(' + flt_startdate.isoformat() + ' - '
                          + flt_enddate.isoformat() + ')')
            return -1
        if var == 'ECHO_TOP':
            fore_timestamps = [date2num(dparser.parse(x[-19:-3]), units='Seconds since 1970-01-01T00:00:00',
                                        calendar='gregorian') for x in os.listdir(PATH_DATA_FORE_DATE[0])]
            idx_fore_day_split = len(fore_timestamps)
            fore_timestamps += [date2num(dparser.parse(x[-19:-3]), units='Seconds since 1970-01-01T00:00:00',
                                         calendar='gregorian') for x in os.listdir(PATH_DATA_FORE_DATE[1])]
        elif var == 'VIL':
            fore_timestamps = [date2num(dparser.parse(x[-23:-3].replace('_','')), units='Seconds since 1970-01-01T00:00:00',
                                        calendar='gregorian') for x in os.listdir(PATH_DATA_FORE_DATE[0])]
            idx_fore_day_split = len(fore_timestamps)
            fore_timestamps += [date2num(dparser.parse(x[-23:-3].replace('_','')), units='Seconds since 1970-01-01T00:00:00',
                                         calendar='gregorian') for x in os.listdir(PATH_DATA_FORE_DATE[1])]

        aligned_fore_start = flt_time[0] + gb.LOOKAHEAD_SECONDS[1]
        aligned_fore_end = flt_time[-1] + gb.LOOKAHEAD_SECONDS[-1]
        aligned_fore_start = aligned_fore_start - (aligned_fore_start % gb.FORE_REFRESH_RATE)
        aligned_fore_end = aligned_fore_end - (aligned_fore_end % gb.FORE_REFRESH_RATE)
        exp_fore_timestamps = aligned_fore_end - (aligned_fore_end % gb.FORE_REFRESH_RATE)

        diff = set(exp_fore_timestamps) - set(fore_timestamps)
        if len(diff) > 0:
            logging.error("EchoTop Forecast Data Missing {} Entries During Flight {} ({} - {})".format(
                len(diff), file, flt_startdate.isoformat(), flt_enddate.isoformat()))
    if USES_CUR:
        PATH_DATA_CUR_DATE = [PATH_DATA_SORTED + flt_startdate.isoformat()[:10] + '/Current/',
                                 PATH_DATA_SORTED + flt_enddate.isoformat()[:10] + '/Current/']
        if not (os.path.isdir(PATH_DATA_CUR_DATE[0]) and os.path.isdir(PATH_DATA_CUR_DATE[1])):
            logging.error(' EchoTop Current Data Does Not Cover ' + file + '(' + flt_startdate.isoformat() + ' - '
                          + flt_enddate.isoformat() + ')')
            return -1

        if var == 'ECHO_TOP':
            cur_timestamps = [date2num(dparser.parse(x[-19:-3]), units='Seconds since 1970-01-01T00:00:00',
                                       calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[0])]
            idx_cur_day_split = len(cur_timestamps)
            cur_timestamps +=[date2num(dparser.parse(x[-19:-3]), units='Seconds since 1970-01-01T00:00:00',
                                   calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[1])]
        elif var == 'VIL':
            cur_timestamps = [date2num(dparser.parse(x[-23:-3].replace('_','')), units='Seconds since 1970-01-01T00:00:00',
                                       calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[0])]
            idx_cur_day_split = len(cur_timestamps)
            cur_timestamps +=[date2num(dparser.parse(x[-23:-3].replace('_','')), units='Seconds since 1970-01-01T00:00:00',
                                       calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[1])]

        aligned_cur_start = flt_time[0] - (flt_time[0] % 150)
        aligned_cur_end = flt_time[-1] - (flt_time[-1] % 150)
        exp_cur_timestamps = np.arange(aligned_cur_start, aligned_cur_end, 150)
        diff = set(exp_cur_timestamps) - set(cur_timestamps)
        if len(diff) > 0:
            logging.error("EchoTop Current Data Missing {} Entries During Flight {} ({} - {})".format(
                len(diff), file, flt_startdate.isoformat(), flt_enddate.isoformat()))

    '''
    # Create Basemap, plot on Latitude/Longitude scale
    m = Basemap(width=12000000, height=9000000, rsphere=gb.R_EARTH,
                resolution='l', area_thresh=1000., projection='lcc',
                lat_0=gb.LAT_ORIGIN, lon_0=gb.LON_ORIGIN)
    m.drawcoastlines()
    Parallels = np.arange(0., 80., 10.)
    Meridians = np.arange(10., 351., 20.)

    # Labels = [left,right,top,bottom]
    m.drawparallels(Parallels, labels=[False, True, True, False])
    m.drawmeridians(Meridians, labels=[True, False, False, True])
    fig2 = plt.gca()
    '''

    # Closest-Approximation - From EchoTop
    weather_cubes_time = np.array([], dtype=float)
    weather_cubes_lat = np.array([], dtype=float)
    weather_cubes_lon = np.array([], dtype=float)
    weather_cubes_data = np.array([], dtype=float)

    print('Data Collection Begin\t', str(datetime.datetime.now()))
    for i in range(1000,len(flight_tr[:, ])):

        # Open EchoTop File Covering the Current Time
        if USES_CUR:
            temp_idx = np.argmin((flt_time[i]) % cur_timestamps)
            if temp_idx != idx_cur_data:
                idx_cur_data = temp_idx
                if idx_cur_data < idx_cur_day_split: idx_cur_day = 0
                else: idx_cur_day = 1
                PATH_DATA_CUR = PATH_DATA_CUR_DATE[idx_cur_day] + os.listdir(PATH_DATA_CUR_DATE[idx_cur_day])[idx_cur_data - (idx_cur_day*idx_cur_day_split)]
                data_cur_rootgrp = Dataset(PATH_DATA_CUR, 'r', format='NetCDF4')
                data_cur_rootgrp.variables[var].set_auto_mask(False)
                relevant_data[0] = data_cur_rootgrp[var][0][0]
                data_cur_rootgrp.close()
        if USES_FORE:
            idx_fore_data = np.argmin(flt_time[i] % fore_timestamps)
            if idx_fore_data < idx_fore_day_split: idx_fore_day = 0
            else: idx_fore_day = 1
            PATH_DATA_FORE = PATH_DATA_FORE_DATE[idx_fore_day] + os.listdir(PATH_DATA_FORE_DATE[idx_fore_day])[idx_fore_data-(idx_fore_day*idx_fore_day_split)]
            data_fore_rootgrp = Dataset(PATH_DATA_FORE, 'r', format='NETCDF4')
            data_fore_timestamps = data_fore_rootgrp['time'][:]
            data_fore_rootgrp.variables[var].set_auto_mask(False)
            for t in range(fore_start, len(gb.LOOKAHEAD_SECONDS)):
                idx_time = np.argmin(
                    data_fore_timestamps % (flt_time[i] + gb.LOOKAHEAD_SECONDS[t]))
                if idx_time != idx_forecast_times[t - fore_start]:
                    idx_forecast_times[t - fore_start] = idx_time
                    relevant_data[t] = data_fore_rootgrp.variables[var][idx_time][0]
            data_fore_rootgrp.close()

        # Heading Projection & Ortho for point
        if i == len(flt_time[:])-1:
            heading = gb.heading_a_to_b(flt_lon[i-1], flt_lat[i-1], flt_lat[i], flt_lon[i])
        else:
            heading = gb.heading_a_to_b(flt_lon[i], flt_lat[i], flt_lat[i + 1], flt_lon[i + 1])
        heading_ortho = (heading + 90) % 360
        theta = math.radians(heading - 90)
        theta_ortho = math.radians(heading_ortho - 90)

        # find track-point in ET data and calculate point-steps
        data_x_idx = np.abs(lons - flt_lon[i]).argmin()
        data_y_idx = np.abs(lats - flt_lat[i]).argmin()

        # Select nearest-available point to determine step-sizes
        data_x, data_y = lons[data_x_idx], lats[data_y_idx]
        data_x_neighbor, data_y_neighbor = -1, -1
        if data_x_idx == len(lons) - 1:
            data_x_neighbor = data_x_idx - 1
        else:
            data_x_neighbor = data_x_idx + 1
        if data_y_idx == len(lats) - 1:
            data_y_neighbor = data_y_idx - 1
        else:
            data_y_neighbor = data_y_idx + 1
        data_delta_x, data_delta_y = np.abs(data_x - lons[data_x_neighbor]), np.abs(data_y - lats[data_y_neighbor])

        unitstep_x = (gb.CUBE_SIZE / 2) * data_delta_x * math.cos(theta)
        unitstep_y = (gb.CUBE_SIZE / 2) * data_delta_y * math.sin(theta)
        unitstep_ortho_x = (gb.CUBE_SIZE / 2) * data_delta_x * math.cos(theta_ortho)
        unitstep_ortho_y = (gb.CUBE_SIZE / 2) * data_delta_y * math.sin(theta_ortho)

        # Generate 20-point axis orthogonal to heading
        centerline_ortho_x, actual_ortho_delta_x = np.linspace(- (gb.CUBE_SIZE / 2) * unitstep_ortho_x,
                                                               (gb.CUBE_SIZE / 2) * unitstep_ortho_x,
                                                               num=gb.CUBE_SIZE,
                                                               retstep=True)
        centerline_ortho_y, actual_ortho_delta_y = np.linspace(- (gb.CUBE_SIZE / 2) * unitstep_ortho_y,
                                                               (gb.CUBE_SIZE / 2) * unitstep_ortho_y,
                                                               num=gb.CUBE_SIZE,
                                                               retstep=True)
        # Generate 20-point axis along heading
        centerline_x, actual_delta_x = np.linspace(- (gb.CUBE_SIZE / 2) * unitstep_x,
                                                   (gb.CUBE_SIZE / 2) * unitstep_x, num=gb.CUBE_SIZE, retstep=True)
        centerline_y, actual_delta_y = np.linspace(- (gb.CUBE_SIZE / 2) * unitstep_y,
                                                   (gb.CUBE_SIZE / 2) * unitstep_y, num=gb.CUBE_SIZE, retstep=True)

        # Collect and Append Single Cube
        # TODO: Find Weather data to test altitude dependency on
        weather_cube_proj = np.zeros((2, gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)
        weather_cube_actual = np.zeros((2, gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)
        weather_cube_et = np.zeros((gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)

        # Vectorized Cube Data Extraction
        weather_cube_proj[0] = flt_lon[i] + np.tile(centerline_x, (gb.CUBE_SIZE, 1)) + np.tile(centerline_ortho_x,
                                                                                            (gb.CUBE_SIZE, 1)).T
        weather_cube_proj[1] = flt_lat[i] + np.tile(centerline_y, (gb.CUBE_SIZE, 1)) + np.tile(centerline_ortho_y,
                                                                                            (gb.CUBE_SIZE, 1)).T
        for idx_ in range(0, gb.CUBE_SIZE):
            for idx_ortho in range(0, gb.CUBE_SIZE):
                data_actual_idx_x = np.abs(lons - weather_cube_proj[0][idx_][idx_ortho]).argmin()
                data_actual_idx_y = np.abs(lats - weather_cube_proj[1][idx_][idx_ortho]).argmin()

                weather_cube_actual[0][idx_][idx_ortho] = lons[data_actual_idx_x]
                weather_cube_actual[1][idx_][idx_ortho] = lats[data_actual_idx_y]
                for t in range(0, len(gb.LOOKAHEAD_SECONDS)):
                    weather_cube_et[idx_][idx_ortho] = relevant_data[t][data_actual_idx_y][data_actual_idx_x]

        # Print the max Error between cube points
        if i % 100 == 0:
            err = np.abs(weather_cube_actual - weather_cube_proj)
            err_dist = np.sqrt(np.square(err[0]) + np.square(err[1]))
            maxerr = err_dist.flatten()[err_dist.argmax()]
            print("Max Distance Err:\t", "{:10.4f}".format(maxerr), "\t", str(i + 1),
                  ' / ', len(flight_tr[:, 1] - 1), '\t', file.split('/')[-1])

        # Append current cube to list of data
        weather_cubes_lat = np.append(weather_cubes_lat, weather_cube_actual[1])
        weather_cubes_lon = np.append(weather_cubes_lon, weather_cube_actual[0])
        weather_cubes_data = np.append(weather_cubes_data, weather_cube_et)
        weather_cubes_time = np.append(weather_cubes_time, flt_time[i])

    '''
    # Verification: Plot collected cubes v. actual flight points
    m.scatter(weather_cubes_lon, weather_cubes_lat, marker=',', color='blue', latlon=True)
    m.scatter(flight_tr[:, 2], flight_tr[:, 1], marker=',', color='red', latlon=True)
    plt.show(block=False)
    PATH_FIGURE_PROJECTION = gb.PATH_PROJECT + '/Output/Weather Cubes/Plots/' \
                             + flt_startdate.isoformat().replace(':', '_') + '.' + gb.FIGURE_FORMAT
    plt.savefig(PATH_FIGURE_PROJECTION, format=gb.FIGURE_FORMAT)
    plt.close()
    '''

    # reshape and write to NetCDF
    weather_cubes_lat = weather_cubes_lat.reshape(-1, gb.CUBE_SIZE * gb.CUBE_SIZE)
    weather_cubes_lon = weather_cubes_lon.reshape(-1, gb.CUBE_SIZE * gb.CUBE_SIZE)
    weather_cubes_data = weather_cubes_data.reshape(-1, gb.CUBE_SIZE * gb.CUBE_SIZE)

    file_local = file.split('/')[-1]
    PATH_NC_FILENAME = PATH_OUTPUT + flt_startdate.isoformat()[:10] + '/' + file_local.split('.')[0] + '.nc'
    print('WRITING TO:\t', PATH_NC_FILENAME)
    if not os.listdir(PATH_OUTPUT).__contains__(flt_startdate.isoformat()[:10]):
        os.mkdir(PATH_OUTPUT + flt_startdate.isoformat()[:10])
    cubes_rootgrp = Dataset(PATH_NC_FILENAME, 'w', type='NetCDF4')

    # Add Dimensions: t, X/YPoints
    cubes_rootgrp.createDimension('time', size=None)
    cubes_rootgrp.createDimension('XPoints', size=gb.CUBE_SIZE)
    cubes_rootgrp.createDimension('YPoints', size=gb.CUBE_SIZE)

    # Add Variables: t, X/YPoints, lat/lon, echotop
    cubes_rootgrp.createVariable('time', datatype=float, dimensions=('time'))
    cubes_rootgrp.variables['time'].units = 'Seconds since 1970-01-01T00:00:00'
    cubes_rootgrp.variables['time'].calendar = 'gregorian'
    cubes_rootgrp.createVariable('XPoints', datatype=float, dimensions=('XPoints'))
    cubes_rootgrp.variables['XPoints'].units = 'indexing for each weather cube'
    cubes_rootgrp.createVariable('YPoints', datatype=float, dimensions=('YPoints'))
    cubes_rootgrp.variables['YPoints'].units = 'indexing for each weather cube'
    cubes_rootgrp.createVariable('Latitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
    cubes_rootgrp.createVariable('Longitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
    cubes_rootgrp.createVariable(var, datatype=float, dimensions=('time', 'XPoints', 'YPoints'))

    # Add Metadata: Flight Callsign, Earth-radius,
    cubes_rootgrp.Callsign = file.split('_')[3]
    cubes_rootgrp.rEarth = gb.R_EARTH

    # Assign Weather Cube Data to netCDF Variables
    cubes_rootgrp.variables['XPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
    cubes_rootgrp.variables['YPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
    cubes_rootgrp.variables['time'][:] = weather_cubes_time
    cubes_rootgrp.variables['Latitude'][:] = weather_cubes_lat
    cubes_rootgrp.variables['Longitude'][:] = weather_cubes_lon
    cubes_rootgrp.variables[var][:] = weather_cubes_data

    cubes_rootgrp.close()
    return 0


def main():
    # open sample Trajectory and Echotop data
    products = {'et': 'ECHO_TOP','vil': 'VIL'}
    prod = 'vil'
    PATH_COORDS = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/Sorted/'
    #PATH_ECHOTOP_NC =
    # PATH_ECHOTOP_FILE =
    PATH_DATA = {'et': gb.PATH_PROJECT + '/Data/EchoTop/Sorted/', 'vil': gb.PATH_PROJECT + '/Data/VIL/Sorted/'}
    PATH_SAMPLE_FILE = {'et': PATH_DATA['et'] + '2018-11-01/Current/ciws.EchoTop.20181101T000000Z.nc',
            'vil': PATH_DATA['vil'] + '2019-01-10/Current/urn_fdc_ll.mit.edu_Dataset_VIL-0024E84DA303_2019-01-10T00_00_00Z.nc'}

    PATH_OUTPUT_CUBES = gb.PATH_PROJECT + '/Output/Weather Cubes/{}/'.format(products[prod])
    PATH_CUBES_LOG = gb.PATH_PROJECT + '/Output/Weather Cubes/{}_Cube_Gen.log'.format(products[prod])

    fmode = 'w'
    if os.path.isfile(PATH_CUBES_LOG):
        overwrite = input("{} exists: overwrite? [y/n]".format(PATH_CUBES_LOG))
        if overwrite.lower() == 'y':
            fmode = 'w'
        elif overwrite.lower() == 'n':
            fmode == 'a'
    logging.basicConfig(filename=PATH_CUBES_LOG, filemode=fmode, level=logging.INFO)

    data = Dataset(PATH_SAMPLE_FILE[prod] + '', delimiter=',', format='NETCDF4')
    data_lon = data.variables['x0'][:]
    data_lat = data.variables['y0'][:]
    data.close()

    USES_CURRENT = gb.LOOKAHEAD_SECONDS.__contains__(0.)
    USES_FORECAST = gb.LOOKAHEAD_SECONDS[len(gb.LOOKAHEAD_SECONDS) - 1] > 0.
    if USES_CURRENT:
        forecast_start = 1
    else:
        forecast_start = 0

    func_process_partial = partial(process_flight_plan, products[prod], PATH_DATA[prod], PATH_OUTPUT_CUBES, data_lon, data_lat,
                                   USES_CURRENT, USES_FORECAST, forecast_start, PATH_CUBES_LOG)

    os.chdir(PATH_COORDS)
    sttime = datetime.datetime.now()
    dirs = [x for x in os.listdir() if os.path.isdir(x)]
    for dir in dirs:
        os.chdir(dir)

        files = [x for x in os.listdir() if os.path.isfile(x)]
        files = [os.path.abspath('.') + '/' + file for file in files]

        if gb.BLN_MULTIPROCESS:
            with ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as ex:
                exit_code = ex.map(func_process_partial, files)
        else:
            for file in files:
                func_process_partial(file)

        os.chdir('..')
        if dir.__contains__('5'):
            cont = input("Completed {}: Continue? y/n".format(dir))
            if cont.lower() == 'n':
                break

    os.chdir(gb.PATH_PROJECT)

    edtime = datetime.datetime.now()
    duration = edtime - sttime
    logging.info('done: ' + edtime.isoformat())
    logging.info('execution time:' + str(duration.total_seconds()) + ' s')
    print('Execution complete. Check ' + PATH_CUBES_LOG + ' for details')

if __name__ == '__main__':
    main()