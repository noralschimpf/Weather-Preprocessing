from netCDF4 import Dataset, num2date, date2num, MFDataset
import numpy as np
import os
from shutil import copyfile
from mpl_toolkits.basemap import Basemap
from matplotlib import cm, pyplot as plt
import Global_Tools as gb
from mpl_toolkits.mplot3d import axes3d
from datetime import datetime

PATH_ECHOTOP_RAW = gb.PATH_PROJECT + '/Data/EchoTop/'
os.chdir(PATH_ECHOTOP_RAW)
nc_files = [x for x in os.listdir() if x.__contains__('.nc')]

#TODO: Multiprocessing
file_count = 0
for file in nc_files:
    rootgrp_orig = Dataset(file, "r", format="netCDF4")

    # Identify as Current or Forecast Data
    if(rootgrp_orig.variables.keys().__contains__('forecast_period')):
        STR_SORT_FORECAST = 'Forecast'
        if not file.__contains__('0000Z'):
            rootgrp_orig.close()
            file_count += 1
            continue
        time = rootgrp_orig.variables["times"][:15]
        time.units = rootgrp_orig.variables["times"].units
        time.calendar = rootgrp_orig.variables["times"].calendar
        echotop = rootgrp_orig.variables["ECHO_TOP"][:15]
    else:
        STR_SORT_FORECAST = 'Current'
        time = rootgrp_orig.variables["time"]
        echotop = rootgrp_orig.variables["ECHO_TOP"]
    x0 = rootgrp_orig.variables["x0"]
    y0 = rootgrp_orig.variables["y0"]
    z0 = rootgrp_orig.variables["z0"]

    date = num2date(time[0], units=time.units, calendar=time.calendar)

    # Save Data as Sorted netCDF4
    str_current_date = date.isoformat()[:10]
    if not os.path.isdir(PATH_ECHOTOP_RAW + '/Sorted/' + str_current_date):
        os.mkdir(PATH_ECHOTOP_RAW + '/Sorted/' + str_current_date)
    if not os.path.isdir(PATH_ECHOTOP_RAW + '/Sorted/' + str_current_date + '/' + STR_SORT_FORECAST):
        os.mkdir(PATH_ECHOTOP_RAW + '/Sorted/' + str_current_date + '/' + STR_SORT_FORECAST)
    str_sorted_file = PATH_ECHOTOP_RAW + 'Sorted/' + str_current_date + '/' + STR_SORT_FORECAST + '/' + file


    # Unlock Masked Data
    for v in [x0, y0, z0, echotop, time]:
        if v.mask:
            v.set_auto_mask(False)
            v = v[::]
    '''
        Map EchoTop x,y to Lambert Conformal Projection
          x0,y0: meters from lat:38 long:-90
          xlat,ylong: equivalent lat/long values
        '''
    y_lat, x_lon = gb.rel_to_latlong(x0[:], y0[:], gb.LAT_ORIGIN, gb.LON_ORIGIN, gb.R_EARTH)

    '''
    PLOT_ONLY:
    # Create Basemap, plot on Latitude/Longitude scale
    m = Basemap(width=12000000, height=9000000, rsphere=gb.R_EARTH,
                resolution='l', area_thresh=1000., projection='lcc',
                lat_0=gb.LAT_ORIGIN, lon_0=gb.LON_ORIGIN)
    m.drawcoastlines()


    # Draw Meridians and Parallels
    Parallels = np.arange(0., 80., 10.)
    Meridians = np.arange(10., 351., 20.)

    # Labels = [left,right,top,bottom]
    m.drawparallels(Parallels, labels=[False, True, True, False])
    m.drawmeridians(Meridians, labels=[True, False, False, True])
    fig2 = plt.gca()
    '''


    #PLOT_ONLY:x_long_mesh, y_lat_mesh = np.meshgrid(x_lon, y_lat)


    '''
    PLOT_ONLY:
    # Define filled contour levels and plot
    color_levels = np.arange(-1e3, 10e3, 1e3)
    ET_Lambert_Contour = m.contourf(x_long_mesh, y_lat_mesh, echotop[0][0], color_levels, latlon=True, cmap=cm.coolwarm)
    m.colorbar(ET_Lambert_Contour, location='right', pad='5%')
    plt.show(block=False)
    PATH_FIGURE_PROJECTION = gb.PATH_PROJECT + '/Output/EchoTop_Projected/' \
                             + dates[0].isoformat().replace(':', '_') + '.' + gb.FIGURE_FORMAT
    plt.savefig(PATH_FIGURE_PROJECTION, format=gb.FIGURE_FORMAT)
    plt.close()
    '''
    rootgrp_orig.close()

    rootgrp_sorted = Dataset(str_sorted_file, 'w', format="NETCDF4")

    # Add Dimensions: t, X/YPoints
    rootgrp_sorted.createDimension('time', size=15)
    rootgrp_sorted.createDimension('x0', size=5120)
    rootgrp_sorted.createDimension('y0', size=3520)
    rootgrp_sorted.createDimension('z0', size=1)

    # Add Variables: t, X/YPoints, lat/lon, echotop
    rootgrp_sorted.createVariable('time', datatype=float, dimensions=('time'), zlib=True, least_significant_digit=5)
    rootgrp_sorted.variables['time'].units = 'Seconds since 1970-01-01T00:00:00'
    rootgrp_sorted.variables['time'].calendar = 'gregorian'
    rootgrp_sorted.createVariable('x0', datatype=float, dimensions=('x0'), zlib=True, least_significant_digit=5)
    rootgrp_sorted.variables['x0'].units = 'degrees longitude'
    rootgrp_sorted.createVariable('y0', datatype=float, dimensions=('y0'), zlib=True, least_significant_digit=5)
    rootgrp_sorted.variables['y0'].units = 'degrees latitude'
    rootgrp_sorted.createVariable('z0', datatype=float, dimensions=('z0'), zlib=True, least_significant_digit=5)
    rootgrp_sorted.variables['y0'].units = 'meters'
    rootgrp_sorted.createVariable('ECHO_TOP', datatype=float, dimensions=('time', 'z0', 'y0', 'x0'), zlib=True, least_significant_digit=5)


    # Assign Weather Cube Data to netCDF Variables
    rootgrp_sorted.variables['x0'][:] = x_lon
    rootgrp_sorted.variables['y0'][:] = y_lat
    rootgrp_sorted.variables['z0'][:] = z0[:]
    rootgrp_sorted.variables['time'][:] = time
    rootgrp_sorted.variables['ECHO_TOP'][:] = echotop

    rootgrp_sorted.close()
    file_count += 1
    print('converted:\t', file_count, ' of ', len(nc_files))

files_to_delete = [x for x in os.listdir() if not os.path.isdir(x)]
os.remove(files_to_delete)
os.chdir(gb.PATH_PROJECT)