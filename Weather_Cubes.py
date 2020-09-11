import Global_Tools as gb
import numpy as np
import math, os, datetime
from mpl_toolkits.basemap import Basemap
from matplotlib import cm, pyplot as plt
from netCDF4 import Dataset, num2date, date2num
from dateutil import parser as dparser
from numba import jit

# open sample Trajectory and Echotop data
CUBE_SIZE = 20
START_POS = 0
PATH_COORDS = gb.PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/'
PATH_ECHOTOP_NC = gb.PATH_PROJECT + '/Data/EchoTop/Sorted/'
PATH_ECHOTOP_FILE = PATH_ECHOTOP_NC + '2020-06-22/ciws.EchoTop.20200622T180000Z.nc'
PATH_TEMP_DATA = gb.PATH_PROJECT + '/Data/TMP_200mb.txt'
PATH_OUTPUT_CUBES = gb.PATH_PROJECT + '/Output/Weather Cubes/'


# temp_data = np.loadtxt(PATH_TEMP_DATA)
echotop_rootgrp = Dataset(PATH_ECHOTOP_FILE + '', delimiter=',', format='NETCDF4')

et_lon = echotop_rootgrp.variables['x0'][:]
et_lat = echotop_rootgrp.variables['y0'][:]

echotop_rootgrp.close()
os.chdir(PATH_COORDS)
dirs = [x for x in os.listdir() if os.path.isdir(x)]
for dir in dirs:
    os.chdir(dir)
    for file in os.listdir():

        # Load Flight Data and EchoTop Coordinates
        flight_tr = np.loadtxt(file, delimiter=',')

        # echotop_rootgrp.variables['ECHO_TOP'].set_auto_mask(False)
        # et_echotop = echotop_rootgrp.variables['ECHO_TOP'][0][0]

        flt_callsign = PATH_COORDS.split('_')[-2]
        flt_time = flight_tr[:, 0]
        flt_lat = flight_tr[:, 1]
        flt_lon = flight_tr[:, 2]
        flt_alt = flight_tr[:, 3]

        # Generate list of EchoTop Report Times
        flt_startdate = num2date(flt_time[0], units='seconds since 1970-01-01T00:00:00', calendar='gregorian')
        PATH_ECHOTOP_FLIGHTDATE = PATH_ECHOTOP_NC + flt_startdate.isoformat()[:10] + '/'
        et_timestamps = [date2num(dparser.parse(x[-19:-3]), units='Seconds since 1970-01-01T00:00:00',
                                  calendar='gregorian') for x in os.listdir(PATH_ECHOTOP_FLIGHTDATE)]

        # Create Basemap, plot on Latitude/Longitude scale
        '''
        m = Basemap(width=12000000, height=9000000, rsphere=gb.R_EARTH,
                    resolution='l', area_thresh=1000., projection='lcc',
                    lat_0=gb.LAT_ORIGIN, lon_0=gb.LONG_ORIGIN)
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
        weather_cubes_et = np.array([], dtype=float)

        print('Data Collection Begin\t', str(datetime.datetime.now()))
        for i in range(START_POS, len(flight_tr[:, ]) - 1):

            # Open EchoTop File Covering the Current Time
            idx_relevant_et = np.argmin((flt_time[i]) % et_timestamps)
            PATH_RELEVANT_ET = PATH_ECHOTOP_FLIGHTDATE + os.listdir(PATH_ECHOTOP_FLIGHTDATE)[idx_relevant_et]
            relevant_rootgrp = Dataset(PATH_RELEVANT_ET, 'r', type='NetCDF4')
            relevant_et = relevant_rootgrp.variables["ECHO_TOP"][0][0]
            relevant_et._set_mask(False)
            relevant_rootgrp.close()

            # Heading Projection & Ortho for point
            heading = gb.heading_a_to_b(flt_lon[i], flt_lat[i], flt_lat[i + 1], flt_lon[i + 1])
            heading_ortho = (heading + 90) % 360
            theta = math.radians(heading - 90)
            theta_ortho = math.radians(heading_ortho - 90)

            # find track-point in ET data and calculate point-steps
            et_x_idx = np.abs(et_lon - flt_lon[i]).argmin()
            et_y_idx = np.abs(et_lat - flt_lat[i - START_POS]).argmin()

            # Select nearest-available point to determine step-sizes
            et_x, et_y = et_lon[et_x_idx], et_lat[et_y_idx]
            et_x_neighbor, et_y_neighbor = -1, -1
            if (et_x_idx == len(et_lon) - 1):
                et_x_neighbor = et_x_idx - 1
            else:
                et_x_neighbor = et_x_idx + 1
            if (et_y_idx == len(et_lat) - 1):
                et_y_neighbor = et_y_idx - 1
            else:
                et_y_neighbor = et_y_idx + 1
            et_delta_x, et_delta_y = np.abs(et_x - et_lon[et_x_neighbor]), np.abs(et_y - et_lat[et_y_neighbor])

            unitstep_x = (CUBE_SIZE / 2) * et_delta_x * math.cos(theta)
            unitstep_y = (CUBE_SIZE / 2) * et_delta_y * math.sin(theta)
            unitstep_ortho_x = (CUBE_SIZE / 2) * et_delta_x * math.cos(theta_ortho)
            unitstep_ortho_y = (CUBE_SIZE / 2) * et_delta_y * math.sin(theta_ortho)

            # Generate 20-point axis orthogonal to heading
            centerline_ortho_x, actual_ortho_delta_x = np.linspace(- (CUBE_SIZE / 2) * unitstep_ortho_x,
                                                                   (CUBE_SIZE / 2) * unitstep_ortho_x, num=CUBE_SIZE,
                                                                   retstep=True)
            centerline_ortho_y, actual_ortho_delta_y = np.linspace(- (CUBE_SIZE / 2) * unitstep_ortho_y,
                                                                   (CUBE_SIZE / 2) * unitstep_ortho_y, num=CUBE_SIZE,
                                                                   retstep=True)
            # Generate 20-point axis along heading
            centerline_x, actual_delta_x = np.linspace(- (CUBE_SIZE / 2) * unitstep_x,
                                                       (CUBE_SIZE / 2) * unitstep_x, num=CUBE_SIZE, retstep=True)
            centerline_y, actual_delta_y = np.linspace(- (CUBE_SIZE / 2) * unitstep_y,
                                                       (CUBE_SIZE / 2) * unitstep_y, num=CUBE_SIZE, retstep=True)

            # Collect and Append Single Cube
            # TODO: Find Weather data to test altitude dependency on
            weather_cube_proj = np.zeros((2, CUBE_SIZE, CUBE_SIZE), dtype=float)
            weather_cube_actual = np.zeros((2, CUBE_SIZE, CUBE_SIZE), dtype=float)
            weather_cube_et = np.zeros((CUBE_SIZE, CUBE_SIZE), dtype=float)

            # Vectorized Cube Data Extraction
            weather_cube_proj[0] = flt_lon[i] + np.tile(centerline_x, (CUBE_SIZE, 1)) + np.tile(centerline_ortho_x,
                                                                                                (CUBE_SIZE, 1)).T
            weather_cube_proj[1] = flt_lat[i] + np.tile(centerline_y, (CUBE_SIZE, 1)) + np.tile(centerline_ortho_y,
                                                                                                (CUBE_SIZE, 1)).T

            a = np.arange(CUBE_SIZE)
            b = np.arange(CUBE_SIZE)
            temp_act = np.zeros((2, CUBE_SIZE, CUBE_SIZE), dtype=float)
            with np.nditer([weather_cube_proj[0].reshape(1, 400), weather_cube_proj[1].reshape(1, 400),
                            weather_cube_actual[0].reshape(1, 400), weather_cube_actual[1].reshape(1, 400)],
                           op_flags=[['readonly', 'no_broadcast'], ['readonly', 'no_broadcast'],
                                     ['writeonly'], ['writeonly']]) as it:
                for (proj_x, proj_y, act_x, act_y) in it:
                    et_actual_idx_x = np.abs(et_lon - proj_x).argmin()
                    et_actual_idx_y = np.abs(et_lat - proj_y).argmin()
                    act_x[...] = et_lon[et_actual_idx_x]
                    act_y[...] = et_lat[et_actual_idx_y]

            # Print the max Error between cube points
            err = np.abs(weather_cube_actual - weather_cube_proj)
            err_dist = np.sqrt(np.square(err[0]) + np.square(err[1]))
            print("Max Distance Err:\t", "{:10.4f}".format(err_dist.flatten()[err_dist.argmax()]), "\t", str(i+1), ' / ',
                  len(flight_tr[:, 1] - 1))

            # Append current cube to list of data
            weather_cubes_lat = np.append(weather_cubes_lat, weather_cube_actual[1])
            weather_cubes_lon = np.append(weather_cubes_lon, weather_cube_actual[0])
            weather_cubes_et = np.append(weather_cubes_et, weather_cube_et)
            weather_cubes_time = np.append(weather_cubes_time, flt_time[i])


        # Verification: Plot collected cubes v. actual flight points
        '''
        m.scatter(weather_cubes_lon, weather_cubes_lat, marker=',', color='blue', latlon=True)
        m.scatter(flight_tr[:, 2], flight_tr[:, 1], marker=',', color='red', latlon=True)
        plt.show(block=False)
        PATH_FIGURE_PROJECTION = gb.PATH_PROJECT + '/Output/Weather Cubes/Plots/' \
                                 + flt_startdate.isoformat().replace(':', '_') + '.' + gb.FIGURE_FORMAT
        plt.savefig(PATH_FIGURE_PROJECTION, format=gb.FIGURE_FORMAT)
        plt.close()
        '''

        # reshape and write to NetCDF
        weather_cubes_lat = weather_cubes_lat.reshape(-1, CUBE_SIZE * CUBE_SIZE)
        weather_cubes_lon = weather_cubes_lon.reshape(-1, CUBE_SIZE * CUBE_SIZE)
        weather_cubes_et = weather_cube_et.reshape(-1, CUBE_SIZE * CUBE_SIZE)

        PATH_NC_FILENAME = PATH_OUTPUT_CUBES + flt_startdate.isoformat()[:10] + '/' + file.split('.')[0] + '.nc'
        if (not os.listdir(PATH_OUTPUT_CUBES).__contains__(flt_startdate.isoformat()[:10])):
            os.mkdir(PATH_OUTPUT_CUBES + flt_startdate.isoformat()[:10])
        cubes_rootgrp = Dataset(PATH_NC_FILENAME, 'w', type='NetCDF4')

        # Add Dimensions: t, X/YPoints
        cubes_rootgrp.createDimension('time', size=None)
        cubes_rootgrp.createDimension('XPoints', size=20)
        cubes_rootgrp.createDimension('YPoints', size=20)

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
        cubes_rootgrp.createVariable('Echo_Top', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))

        # Add Metadata: Flight Callsign, Earth-radius,
        cubes_rootgrp.Callsign = file.split('_')[3]
        cubes_rootgrp.rEarth = gb.R_EARTH

        # Assign Weather Cube Data to netCDF Variables
        cubes_rootgrp.variables['XPoints'][:] = np.arange(0, CUBE_SIZE, 1)
        cubes_rootgrp.variables['YPoints'][:] = np.arange(0, CUBE_SIZE, 1)
        cubes_rootgrp.variables['time'][:] = weather_cubes_time
        cubes_rootgrp.variables['Latitude'][:] = weather_cubes_lat
        cubes_rootgrp.variables['Longitude'][:] = weather_cubes_lon

        cubes_rootgrp.close()
    os.chdir('..')
os.chdir(gb.PATH_PROJECT)
print('done', datetime.datetime.now())