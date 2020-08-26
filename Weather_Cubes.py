import Global_Tools as gb
import numpy as np
import math
from mpl_toolkits.basemap import Basemap
from matplotlib import cm, pyplot as plt
from netCDF4 import Dataset, num2date

#open sample Trajectory and Echotop data
CUBE_SIZE = 20
PATH_COORDS = gb.PATH_PROJECT + '/Data/IFF_Track_Points/Sorted/2020-06-01/Flight_TrackKLAX_KJFK_JBU624_trk.txt.modified'
PATH_ECHOTOP_NC = gb.PATH_PROJECT + '/Data/EchoTop/Sorted/2020-06-22/ciws.EchoTop.20200622T230230Z.nc'
flight_tr = np.loadtxt(PATH_COORDS, delimiter=',')
echotop_rootgrp = Dataset(PATH_ECHOTOP_NC, delimiter=',', format='NETCDF4')

et_lon = echotop_rootgrp.variables['x0']
et_lat = echotop_rootgrp.variables['y0']
et_echotop = echotop_rootgrp.variables['ECHO_TOP'][0][0]

# Create Basemap, plot on Latitude/Longitude scale
m = Basemap(width=12000000, height=9000000, rsphere=gb.R_EARTH,
            resolution='l', area_thresh=1000., projection='lcc',
            lat_0=gb.LAT_ORIGIN, lon_0=gb.LONG_ORIGIN)
m.drawcoastlines()

# Draw Meridians and Parallels
Parallels = np.arange(0., 80., 10.)
Meridians = np.arange(10., 351., 20.)

# Labels = [left,right,top,bottom]
m.drawparallels(Parallels, labels=[False, True, True, False])
m.drawmeridians(Meridians, labels=[True, False, False, True])
fig2 = plt.gca()

# Generate Weather Cubes for 100 samples, testrun
# TODO: incorporate timestamps, read against multiple netCDF files
# x, y, delta_x, delta_y are are arrays for validation. Change to single-element for processing
x = np.array([], dtype=float)
y = np.array([], dtype=float)
delta_x = np.array([], dtype=float)
delta_y = np.array([], dtype=float)

weather_cubes_lat = np.array([], dtype=float)
weather_cubes_lon = np.array([], dtype=float)
weather_cubes_et = np.array([], dtype=float)
for i in range(1000, 1099):

    #Heading Projection & Ortho for point
    x = np.append(x, [flight_tr[i][3]])
    y = np.append(y, flight_tr[i][2])

    tr_delta_ = np.append(delta_x, flight_tr[i+1][3] - flight_tr[i][3])
    tr_delta_ortho = np.append(delta_y, flight_tr[i+1][2] - flight_tr[i][2])

    heading = gb.heading_a_to_b(flight_tr[i][3], flight_tr[i][2], flight_tr[i+1][3], flight_tr[i+1][2])
    heading_ortho = (heading + 90) % 360

    theta = math.radians(heading-90)
    theta_ortho = math.radians(heading_ortho - 90)

    #find track-point in ET data and calculate point-steps
    et_x_idx = np.abs(et_lon - x[i-1000]).argmin()
    et_y_idx = np.abs(et_lat - y[i-1000]).argmin()
    et_x, et_y = et_lon[et_x_idx], et_lat[et_y_idx]
    et_delta_x, et_delta_y = np.abs(et_x - et_lon[et_x_idx+1]), np.abs(et_y - et_lat[et_y_idx+1])

    unitstep_x = (CUBE_SIZE/2)*et_delta_x*math.cos(theta)
    unitstep_y = (CUBE_SIZE/2)*et_delta_y*math.sin(theta)
    unitstep_ortho_x = (CUBE_SIZE/2)*et_delta_x*math.cos(theta_ortho)
    unitstep_ortho_y = (CUBE_SIZE/2)*et_delta_y*math.sin(theta_ortho)

    #Generate 20 points along heading_ortho
    centerline_ortho_x, actual_ortho_delta_x = np.linspace(- (CUBE_SIZE / 2) * unitstep_ortho_x,
                                                           (CUBE_SIZE/2) * unitstep_ortho_x, num=CUBE_SIZE, retstep=True)
    centerline_ortho_y, actual_ortho_delta_y = np.linspace(- (CUBE_SIZE / 2) * unitstep_ortho_y,
                                                           (CUBE_SIZE/2) * unitstep_ortho_y, num=CUBE_SIZE, retstep=True)

    centerline_x, actual_delta_x = np.linspace(- (CUBE_SIZE/2)*unitstep_x,
                                               (CUBE_SIZE/2)*unitstep_x, num=CUBE_SIZE, retstep=True)
    centerline_y, actual_delta_y = np.linspace(- (CUBE_SIZE/2)*unitstep_y,
                                               (CUBE_SIZE/2)*unitstep_y, num=CUBE_SIZE, retstep=True)



    #scale resolution by 10 (point/step is 10,000, not 1,000
    weather_cube_proj = np.zeros((2, CUBE_SIZE, CUBE_SIZE), dtype=float)
    weather_cube_actual = np.zeros((2, CUBE_SIZE, CUBE_SIZE), dtype=float)
    weather_cube_et = np.zeros((CUBE_SIZE, CUBE_SIZE), dtype=float)

    for idx_ in range(0,CUBE_SIZE):
        for idx_ortho in range(0, CUBE_SIZE):
            #Project expected data points using heading and ortho axes
            weather_cube_proj[0][idx_][idx_ortho] = x[i-1000] + centerline_x[idx_] + centerline_ortho_x[idx_ortho]
            weather_cube_proj[1][idx_][idx_ortho] = y[i-1000] + centerline_y[idx_] + centerline_ortho_y[idx_ortho]

            #collect nearest EchoTop points
            et_actual_idx_x = np.abs(et_lon - weather_cube_proj[0][idx_][idx_ortho]).argmin()
            et_actual_idx_y = np.abs(et_lat - weather_cube_proj[1][idx_][idx_ortho]).argmin()

            weather_cube_actual[0][idx_][idx_ortho] = et_lon[et_actual_idx_x]
            weather_cube_actual[1][idx_][idx_ortho] = et_lat[et_actual_idx_y]
            weather_cube_et[idx_][idx_ortho] = et_echotop[et_actual_idx_y][et_actual_idx_x]



    #plot and verify single track-point
    '''
    m.quiver(flight_tr[i][3], flight_tr[i][2], tr_delta_, tr_delta_ortho, latlon=True)
    m.plot(centerline_ortho_x + x, centerline_ortho_y + y, latlon=True, marker='p', color='red')
    m.plot(centerline_x + x, centerline_y + y, latlon=True, marker='p', color='blue')
    m.scatter(weather_cubes_proj[0], weather_cubes_proj[1], latlon=True, marker=',', color='yellow')
    m.scatter(weather_cubes_actual[0],weather_cubes_actual[1],latlon=True,marker=',',color='green')
    #m.contourf(Weather_Cubes_proj[0], Weather_Cubes_proj[1],np.zeros(CUBE_SIZE,CUBE_SIZE))
    plt.show()
    '''

    #Print the max Error between cube points
    err = np.abs(weather_cube_actual - weather_cube_proj)
    err_dist = np.sqrt(np.square(err[0]) + np.square(err[1]))
    print("Max Distance Err:\t", err_dist.flatten()[err_dist.argmax()], "\t", i, '/1000')

    #Append current cube to list of data
    weather_cubes_lat = np.append(weather_cubes_lat, weather_cube_actual[1])
    weather_cubes_lon = np.append(weather_cubes_lon, weather_cube_actual[0])
    weather_cubes_et = np.append(weather_cubes_et, weather_cube_et)




m.scatter(weather_cubes_lon,weather_cubes_lat,marker=',',color='green', latlon=True)
m.quiver(flight_tr[:-1, 3], flight_tr[:-1, 2], flight_tr[1:, 3], flight_tr[1:, 2], latlon=True, minlength=3)
plt.show(block=True)
print('done')


   # for j in range(0, CUBE_SIZE):

    #position_echotop =




