import Global_Tools as gb
import numpy as np
import math, os, datetime, logging
#from mpl_toolkits.basemap import Basemap
#from matplotlib import pyplot as plt
from netCDF4 import Dataset, num2date, date2num
import utm
from dateutil import parser as dparser
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from numba import jit

def get_relevant_timestamps(flt_startdate, flt_enddate, flt_time, file, var, PATH_DATA_SORTED, USES_FORE, USES_CUR):
    fore_timestamps = cur_timestamps = []
    idx_cur_day_split, idx_fore_day_split = None,None
    PATH_DATA_FORE_DATE, PATH_DATA_CUR_DATE = None, None
    if USES_FORE:
        PATH_DATA_FORE_DATE = [PATH_DATA_SORTED + flt_startdate.isoformat()[:10] + '/Forecast/',
                               PATH_DATA_SORTED + flt_enddate.isoformat()[:10] + '/Forecast/']
        if not os.path.isdir(PATH_DATA_FORE_DATE):
            raise FileExistsError(' EchoTop Forecast Data Does Not Cover ' + file + '(' + flt_startdate.isoformat() + ' - '
                          + flt_enddate.isoformat() + ')')
            return -1

        fore_timestamps = [date2num(dparser.parse(x.split('.')[1]), units='Seconds since 1970-01-01T00:00:00',
                                    calendar='gregorian') for x in os.listdir(PATH_DATA_FORE_DATE[0])]
        idx_fore_day_split = len(fore_timestamps)
        fore_timestamps += [date2num(dparser.parse(x.split('.')[1]), units='Seconds since 1970-01-01T00:00:00',
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

        cur_timestamps = [date2num(dparser.parse(x.split('.')[1]), units='Seconds since 1970-01-01T00:00:00',
                                   calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[0])]
        idx_cur_day_split = len(cur_timestamps)
        cur_timestamps +=[date2num(dparser.parse(x.split('.')[1]), units='Seconds since 1970-01-01T00:00:00',
                                   calendar='gregorian') for x in os.listdir(PATH_DATA_CUR_DATE[1])]

    return cur_timestamps, fore_timestamps, idx_fore_day_split, idx_cur_day_split, PATH_DATA_CUR_DATE, PATH_DATA_FORE_DATE

@jit(nopython=True)
def get_axes(lats, lons, flt_lat, flt_lon, heading, dist_m):
    heading_ortho = (heading + 90) % 360
    theta = math.radians(heading - 90)
    theta_ortho = math.radians(heading_ortho - 90)
    data_delta_lat, data_delta_lon = gb.latlon_unitsteps(flt_lat,flt_lon,heading,dist_m=dist_m)

    unitstep_x = data_delta_lon * np.cos(theta)
    unitstep_y = data_delta_lat * np.sin(theta)
    unitstep_ortho_x = data_delta_lon * np.cos(theta_ortho)
    unitstep_ortho_y = data_delta_lat * np.sin(theta_ortho)
    return unitstep_x, unitstep_y, unitstep_ortho_x, unitstep_ortho_y


def fill_cube_utm(weather_cube_proj: np.array, relevant_data: np.array, UTM_dict: dict, UTM_traceback_dict: dict,
                  lats: np.array, lons: np.array, len_lookahead: np.int32, len_prds: np.int32, len_alts: np.int32):
    weather_cube_actual = np.zeros((int(2), gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=np.float64)
    #Cube Dims (lookahead x products x height x lat x lon) (t,v,z,lat,lon)
    weather_cube_data = np.zeros((len_lookahead,len_prds,len_alts, gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=np.float64)
    for idx_ in range(0, gb.CUBE_SIZE):
        for idx_ortho in range(0, gb.CUBE_SIZE):
            proj_lon, proj_lat = weather_cube_proj[0][idx_][idx_ortho], weather_cube_proj[1][idx_][idx_ortho]
            wc_proj_northing, wc_proj_easting, wc_proj_zonenum, wcproj_zonechar = \
                utm.from_latlon(proj_lat,proj_lon)

            # Find coordinates for relevant UTM region
            grpkey = '{}-{}'.format(wcproj_zonechar, wc_proj_zonenum)
            assert grpkey in UTM_dict.keys(), 'Flight UTM Grid {} Does Not Exist'.format(grpkey)
            dist_matrix = gb.utm_dist(wc_proj_northing, wc_proj_easting, UTM_dict[grpkey][0],UTM_dict[grpkey][1])
            idx_point = np.where(np.abs(dist_matrix).min() == np.abs(dist_matrix))
            #idx_point = (idx_point[0][0],idx_point[1][0])
            idx_point = idx_point[0][0]
            x,y = UTM_traceback_dict[grpkey][0,idx_point],UTM_traceback_dict[grpkey][1,idx_point]
            act_lat, act_lon = lats[x,y], lons[x,y]
            '''act_lat, act_lon = utm.to_latlon(UTM_dict[grpkey][0][idx_point], UTM_dict[grpkey][1][idx_],
                                             int(grpkey.split('-')[1]), grpkey.split('-')[0])'''
            weather_cube_actual[1][idx_][idx_ortho] = act_lat
            weather_cube_actual[0][idx_][idx_ortho] = act_lon
            #collect all t, v, alt for the lat/lon point
            weather_cube_data[:,:,:,idx_,idx_ortho] = relevant_data[:,:,:,x,y]
    return weather_cube_actual, weather_cube_data

def process_flight_plan(prd, USES_CUR, USES_FORE, fore_start, file):

    logging.basicConfig(filename=prd['log path'], filemode='a', level=logging.INFO)
    # Load Flight Data and EchoTop Coordinates
    flight_tr = np.loadtxt(file, delimiter=',')
    flt_time = flight_tr[:, 0]
    flt_lat = flight_tr[:, 1]
    flt_lon = flight_tr[:, 2]
    flt_alt = flight_tr[:, 3]

    relevant_data = np.zeros((len(gb.LOOKAHEAD_SECONDS), len(prd['products']), prd['cube height'], prd['lats'].shape[0], prd['lats'].shape[1]), dtype=float)
    idx_active_cur_file, idx_forecast_times = None, [-1] * (len(gb.LOOKAHEAD_SECONDS) - fore_start)


    flt_startdate = num2date(flt_time[0], units='seconds since 1970-01-01T00:00:00', calendar='gregorian')
    flt_enddate = num2date(flt_time[-1], units='seconds since 1970-01-01T00:00:00', calendar='gregorian')
    # Generate list of EchoTop Report Times
    try:
        cur_timestamps, fore_timestamps, idx_fore_day_split, idx_cur_day_split, PATH_DATA_CUR_DATE, PATH_DATA_FORE_DATE \
            = get_relevant_timestamps(flt_startdate, flt_enddate, flt_time, file, prd['products'], prd['sorted path'], USES_FORE, USES_CUR)
    except TypeError:
        return -1

    aligned_cur_start = flt_time[0]  - (flt_time[0] % prd['refresh rate'])
    aligned_cur_end = flt_time[-1] - (flt_time[-1] % prd['refresh rate'])
    expected_cur_timestamps = np.arange(aligned_cur_start, aligned_cur_end, prd['refresh rate'])
    diff = set(expected_cur_timestamps) - set(cur_timestamps)
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

    # Closest-Approximation - From Weather Data
    weather_cubes_time = np.zeros((len(flt_time)), dtype=float)
    weather_cubes_lat = np.zeros((len(flt_time), gb.CUBE_SIZE, gb.CUBE_SIZE))
    weather_cubes_lon = np.zeros((len(flt_time), gb.CUBE_SIZE, gb.CUBE_SIZE))
    weather_cubes_alt = np.zeros((len(flt_time), prd['cube height']))
    weather_cubes_data = np.zeros((len(flt_time), len(gb.LOOKAHEAD_SECONDS), len(prd['products']), prd['cube height'], gb.CUBE_SIZE, gb.CUBE_SIZE))

    print('Data Collection Begin\t', str(datetime.datetime.now()))
    for i in range(len(flight_tr[:, ])):
        # Open EchoTop File Covering the Current Time
        if USES_CUR:
            idx_cur_file = np.argmin((flt_time[i]) % cur_timestamps)
            if idx_cur_file != idx_active_cur_file:
                idx_active_cur_file = idx_cur_file
                if idx_active_cur_file < idx_cur_day_split: idx_cur_day = 0
                else: idx_cur_day = 1
                PATH_DATA_CUR = PATH_DATA_CUR_DATE[idx_cur_day] + os.listdir(PATH_DATA_CUR_DATE[idx_cur_day])[idx_active_cur_file - (idx_cur_day*idx_cur_day_split)]
                data_cur_rootgrp = Dataset(PATH_DATA_CUR, 'r', format='NetCDF4')

                for v in range(len(prd['products'])):
                    data_cur_rootgrp.variables[prd['products'][v]].set_auto_mask(False)
                    idx_alt =  np.abs(prd['alts'] - flt_alt[i]).argmin()
                    if idx_alt == 0: idx_alt = 1;
                    relevant_data[0][v] = data_cur_rootgrp[prd['products'][v]][0,idx_alt-1:idx_alt+2]
                data_cur_rootgrp.close()
        if USES_FORE:
            idx_fore_data = np.argmin(flt_time[i] % fore_timestamps)
            if idx_fore_data < idx_fore_day_split: idx_fore_day = 0
            else: idx_fore_day = 1
            PATH_DATA_FORE = PATH_DATA_FORE_DATE[idx_fore_day] + os.listdir(PATH_DATA_FORE_DATE[idx_fore_day])[idx_fore_data-(idx_fore_day*idx_fore_day_split)]
            data_fore_rootgrp = Dataset(PATH_DATA_FORE, 'r', format='NETCDF4')
            data_fore_timestamps = data_fore_rootgrp['time'][:]
            for v in prd['products']:
                data_fore_rootgrp.variables[v].set_auto_mask(False)
            for t in range(fore_start, len(gb.LOOKAHEAD_SECONDS)):
                idx_time = np.argmin(
                    data_fore_timestamps % (flt_time[i] + gb.LOOKAHEAD_SECONDS[t]))
                if idx_time != idx_forecast_times[t - fore_start]:
                    idx_forecast_times[t - fore_start] = idx_time
                    for v in range(len(prd['products'])):
                        data_fore_rootgrp.variables[prd['products'][v]].set_auto_mask(False)
                        idx_alt =  np.abs(prd['alts'] - flt_alt[i]).argmin()
                        if idx_alt == 0: idx_alt = 1;
                        relevant_data[t][v] = data_cur_rootgrp[prd['products'][v]][0,idx_alt-1:idx_alt+2]
            data_fore_rootgrp.close()

        # Heading Projection & Ortho for point
        if i == len(flt_time[:])-1:
            heading = gb.heading_a_to_b(flt_lon[i-1], flt_lat[i-1], flt_lat[i], flt_lon[i])
        else:
            heading = gb.heading_a_to_b(flt_lon[i], flt_lat[i], flt_lat[i + 1], flt_lon[i + 1])
        unitstep_x, unitstep_y, unitstep_ortho_x, unitstep_ortho_y = get_axes(prd['lats'], prd['lons'],
                                                              flt_lat[i], flt_lon[i], heading, prd['spatial res'])

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
        weather_cube_proj = np.zeros((2, gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)
        weather_cube_actual = np.zeros((2, gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)
        weather_cube_alt = np.zeros((prd['cube height']), dtype=float)
        # Cube Dims (lookahead x products x height x lat x lon) (t,v,z,lat,lon)
        weather_cube_data = np.zeros((len(gb.LOOKAHEAD_SECONDS),len(prd['products']),prd['cube height'],
                                      gb.CUBE_SIZE, gb.CUBE_SIZE), dtype=float)

        # Vectorized Cube Data Extraction
        weather_cube_proj[0] = flt_lon[i] + np.tile(centerline_x, (gb.CUBE_SIZE, 1)) + np.tile(centerline_ortho_x,
                                                                                            (gb.CUBE_SIZE, 1)).T
        weather_cube_proj[1] = flt_lat[i] + np.tile(centerline_y, (gb.CUBE_SIZE, 1)) + np.tile(centerline_ortho_y,
                                                                                            (gb.CUBE_SIZE, 1)).T
        '''
        m.scatter(prd['lons'],prd['lats'],latlon=True)
        m.scatter(weather_cube_proj[0],weather_cube_proj[1],latlon=True)
        '''

        weather_cube_alt = prd['alts'][idx_alt-1:idx_alt+2]

        weather_cube_actual, weather_cube_data = fill_cube_utm(weather_cube_proj, relevant_data, prd['UTM'], prd['UTM-latlon idxs'],
                           prd['lats'],prd['lons'], len(gb.LOOKAHEAD_SECONDS), len(prd['products']),prd['cube height'])

        # Print the max Error between cube points
        if i % 30 == 0:
            err = np.abs(weather_cube_actual - weather_cube_proj)
            err_dist = np.sqrt(np.square(err[0]) + np.square(err[1]))
            maxerr = err_dist.flatten()[err_dist.argmax()]
            print("{}\tMax Distance Err:\t".format(datetime.datetime.now()), "{:10.4f}\t".format(maxerr), "\t", str(i + 1),
                  ' / ', len(flight_tr[:, 1] - 1), '\t', file.split('/')[-1])

        # Append current cube to list of data
        weather_cubes_lat[i] = weather_cube_actual[1]
        weather_cubes_lon[i] = weather_cube_actual[0]
        weather_cubes_alt[i] = weather_cube_alt
        weather_cubes_data[i] = weather_cube_data
        weather_cubes_time[i] = flt_time[i]

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

    # write to NetCDF
    file_local = file.split('/')[-1]
    PATH_NC_FILENAME = prd['output path'] + flt_startdate.isoformat()[:10] + '/' + file_local.split('.')[0] + '.nc'
    print('WRITING TO:\t', PATH_NC_FILENAME)
    if not os.listdir(prd['output path']).__contains__(flt_startdate.isoformat()[:10]):
        os.mkdir(prd['output path'] + flt_startdate.isoformat()[:10])
    cubes_rootgrp = Dataset(PATH_NC_FILENAME, 'w', type='NetCDF4')

    # Add Dimensions
    cubes_rootgrp.createDimension('time', size=None)
    cubes_rootgrp.createDimension('lookahead',size=len(gb.LOOKAHEAD_SECONDS))
    cubes_rootgrp.createDimension('XPoints', size=gb.CUBE_SIZE)
    cubes_rootgrp.createDimension('YPoints', size=gb.CUBE_SIZE)
    cubes_rootgrp.createDimension('ZPoints',size=prd['cube height'])

    # Add Variables
    cubes_rootgrp.createVariable('time', datatype=float, dimensions=('time'))
    cubes_rootgrp.variables['time'].units = 'Seconds since 1970-01-01T00:00:00'
    cubes_rootgrp.variables['time'].calendar = 'gregorian'
    cubes_rootgrp.createVariable('lookahead',datatype=float,dimensions=('lookahead'))
    cubes_rootgrp.variables['lookahead'].units = 'Seconds ahead of current time'
    cubes_rootgrp.createVariable('XPoints', datatype=float, dimensions=('XPoints'))
    cubes_rootgrp.variables['XPoints'].units = 'indexing for each weather cube'
    cubes_rootgrp.createVariable('YPoints', datatype=float, dimensions=('YPoints'))
    cubes_rootgrp.variables['YPoints'].units = 'indexing for each weather cube'
    cubes_rootgrp.createVariable('latitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
    cubes_rootgrp.createVariable('longitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
    cubes_rootgrp.createVariable('altitudes', datatype=float, dimensions=('time','ZPoints'))
    for prod in prd['products']:
        cubes_rootgrp.createVariable(prod, datatype=float, dimensions=('time', 'lookahead', 'ZPoints', 'XPoints', 'YPoints'))


    # Add Metadata: Flight Callsign, Earth-radius,
    cubes_rootgrp.Callsign = file.split('_')[-1].split('.')[0]
    cubes_rootgrp.rEarth = gb.R_EARTH

    # Assign Weather Cube Data to netCDF Variables
    cubes_rootgrp.variables['XPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
    cubes_rootgrp.variables['YPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
    cubes_rootgrp.variables['time'][:] = weather_cubes_time
    cubes_rootgrp.variables['latitude'][:] = weather_cubes_lat
    cubes_rootgrp.variables['longitude'][:] = weather_cubes_lon
    for p in range(len(prd['products'])):
        cubes_rootgrp.variables[prd['products'][p]][:] = weather_cubes_data[:,:,p,:,:,:]
    
    cubes_rootgrp.close()
    print('COMPLETED:\t', PATH_NC_FILENAME)
    return 0


def main():
    # open sample Trajectory and Echotop data
    PATH_COORDS = gb.PATH_PROJECT + '/Data/IFF_Flight_Plans/Interpolated/'

    et_sample = Dataset('Data/EchoTop/Sorted/2019-01-10/Current/ECHO_TOP.2019-01-10T000000Z.nc','r', format='NETCDF4')
    #vil_sample = Dataset('Data/VIL/Sorted/2019-01-10/Current/VIL.2019-01-10T000000Z.nc','r',format='NETCDF4')
    #hrrr_sample = Dataset('Data/HRRR/Sorted/2019-01-10/Current/hrrr.2019-01-10T000000Z.wrfprsf00.nc')
    ciws_lats, ciws_lons = np.array(et_sample['lats'][:]), np.array(et_sample['lons'][:])
    ciws_utmdict, ciws_traceback, df_ciws_verif = gb.longrange_latlon_to_utm(ciws_lats, ciws_lons)
    df_ciws_verif.to_csv(gb.PATH_PROJECT + '/Output/Weather Cubes/CIWS_UTM.csv')
    #hrrr_lats, hrrr_lons = np.array(hrrr_sample['lats'][:]), np.array(hrrr_sample['lons'][:])
    #hrrr_utmdict, hrrr_traceback, df_hrrr_verif = gb.longrange_latlon_to_utm(hrrr_lats, hrrr_lons)
    #df_hrrr_verif.to_csv(gb.PATH_PROJECT + '/Output/Weather Cubes/HRRR_UTM.csv')

    prd_et = {'products': ['ECHO_TOP'], 'cube height': 1, 'lats': ciws_lats, 'lons': ciws_lons,
              'UTM': ciws_utmdict, 'UTM-latlon idxs': ciws_traceback,
              'alts': np.array(et_sample['alt'][:]), 'sorted path': gb.PATH_PROJECT + '/Data/EchoTop/Sorted/',
              'output path': 'F:\\Aircraft-Data\\Weather Cubes\\ECHO_TOP\\', 'refresh rate': 150,'spatial res': 1850,
              'log path': gb.PATH_PROJECT + '/Output/Weather Cubes/ECHO_TOP_Cube_Gen.log'}
# gb.PATH_PROJECT + '/Output/Weather Cubes/ECHO_TOP/'
    # prd_vil = {'products': ['VIL'], 'cube height': 1, 'lats': ciws_lats, 'lons': ciws_lons,
    #            'UTM': ciws_utmdict, 'UTM-latlon idxs': ciws_traceback,
    #            'alts': np.array(vil_sample['alt'][:]), 'sorted path': gb.PATH_PROJECT + '/Data/VIL/Sorted/',
    #            'output path': gb.PATH_PROJECT + '/Output/Weather Cubes/VIL/', 'refresh rate': 150, 'spatial res': 1850,
    #            'log path': gb.PATH_PROJECT + '/Output/Weather Cubes/VIL_Cube_Gen.log'}
    #
    # prd_hrrr = {'products': ['uwind','vwind','tmp'], 'cube height': 3, 'lats': hrrr_lats, 'lons': hrrr_lons,
    #             'UTM': hrrr_utmdict, 'UTM-latlon idxs': hrrr_traceback,
    #             'alts': np.array(hrrr_sample['alt'][:]), 'sorted path': gb.PATH_PROJECT + '/Data/HRRR/Sorted/',
    #             'output path': gb.PATH_PROJECT + '/Output/Weather Cubes/HRRR/', 'refresh rate': 3600, 'spatial res': 3000,
    #             'log path': gb.PATH_PROJECT + '/Output/Weather Cubes/HRRR_Cube_Gen.log'}

    et_sample.close(); #vil_sample.close(); hrrr_sample.close();

    fmode = 'w'
    if os.path.isfile(prd_et['log path']):
        overwrite = input("{} exists: overwrite? [y/n]".format(prd_et['log path']))
        if overwrite.lower() == 'y':
            fmode = 'w'
        elif overwrite.lower() == 'n':
            fmode == 'a'
    logging.basicConfig(filename=prd_et['log path'], filemode=fmode, level=logging.INFO)

    for product in [prd_et]:

        USES_CURRENT = gb.LOOKAHEAD_SECONDS.__contains__(0.)
        USES_FORECAST = gb.LOOKAHEAD_SECONDS[len(gb.LOOKAHEAD_SECONDS) - 1] > 0.
        if USES_CURRENT:
            forecast_start = 1
        else:
            forecast_start = 0
        func_process_partial = partial(process_flight_plan, product, USES_CURRENT, USES_FORECAST, forecast_start)

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
        edtime = datetime.datetime.now()
        duration = edtime - sttime
        logging.info('done: ' + edtime.isoformat())
        logging.info('execution time:' + str(duration.total_seconds()) + ' s')
        print('Execution complete. Check ' + product['path log'] + ' for details')
        cont = input("Completed {}: Continue? y/n".format(', '.join(product['products'])))
        if cont.lower() == 'n':
            break

        os.chdir(gb.PATH_PROJECT)

if __name__ == '__main__':
    main()