from netCDF4 import Dataset, num2date, date2num, MFDataset
import numpy as np
import os, logging
from mpl_toolkits.basemap import Basemap
from matplotlib import cm, pyplot as plt
import Global_Tools as gb
from mpl_toolkits.mplot3d import axes3d
from concurrent import futures
from functools import partial
import pstats, io, datetime

'''
EXCLUDE PROFILER
import cProfile

def profile(fnc):
    def inner(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = fnc(*args,**kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        PATH_DUMP_FILE = gb.PATH_PROJECT + '/Output/Profiler/NC_Data_Prep.txt'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats(.25)
        ps.print_callers(.25).sort_stats(sortby)
        print(s.getvalue())
        return retval
    return inner
'''


def process_file(var: str, path_et: str, PATH_LOG: str, file: str):
    logging.basicConfig(filename=PATH_LOG, filemode='a', level=logging.INFO)

    print('Processing ' + str(file))
    rootgrp_orig = Dataset(file, "r", format="netCDF4")

    # Identify as Current or Forecast Data
    if rootgrp_orig.variables.keys().__contains__('forecast_period'):
        STR_SORT_FORECAST = 'Forecast'
        SIZE_TIME = 15
        # TODO: REWORK TO USE gb.FORE_REFRESH_RATE
        if not file.__contains__('0000Z'):
            rootgrp_orig.close()
            logging.info(' Skipping ' + file)
            return
        time = rootgrp_orig.variables["times"][:15]
        time.units = rootgrp_orig.variables["times"].units
        time.calendar = rootgrp_orig.variables["times"].calendar
        # echotop = rootgrp_orig.variables[var][:15]
        # echotop.units = rootgrp_orig.variables[var].units
        # echotop.scale_factor = rootgrp_orig.variables[var].scale_factor
        # echotop.add_offset = rootgrp_orig.variables[var].add_offset
        # echotop._FillValue = rootgrp_orig.variables[var]._FillValue


    else:
        STR_SORT_FORECAST = 'Current'
        SIZE_TIME = 1
        time = rootgrp_orig.variables["time"]
        rootgrp_orig.variables[var].set_auto_mask(False)
        # echotop = rootgrp_orig.variables[var]

    x0 = rootgrp_orig.variables["x0"][:]
    y0 = rootgrp_orig.variables["y0"][:]
    z0 = rootgrp_orig.variables["z0"][:]
    fillval = rootgrp_orig.variables[var]._FillValue
    date = num2date(time[0], units=time.units, calendar=time.calendar)
    # time = echotop[:], time[:]

    # Save Data as Sorted netCDF4
    str_current_date = date.isoformat()[:10]
    if not os.path.isdir(path_et + '\\Sorted\\' + str_current_date):
        os.mkdir(path_et + '\\Sorted\\' + str_current_date)
    if not os.path.isdir(path_et + '\\Sorted\\' + str_current_date + '\\' + STR_SORT_FORECAST):
        os.mkdir(path_et + '\\Sorted\\' + str_current_date + '\\' + STR_SORT_FORECAST)
    str_sorted_file = path_et + 'Sorted\\' + str_current_date + '\\' + STR_SORT_FORECAST + '\\' + os.path.split(file)[1]

    '''
        Map EchoTop x,y to Lambert Conformal Projection
          x0,y0: meters from lat:38 long:-90
          xlat,ylong: equivalent lat\\long values
        '''
    y0, x0 = gb.rel_to_latlong(x0[:], y0[:], gb.LAT_ORIGIN, gb.LON_ORIGIN, gb.R_EARTH)


    '''# PLOT_ONLY:
    # Create Basemap, plot on Latitude\\Longitude scale
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


    # PLOT_ONLY:x_long_mesh, y_lat_mesh = np.meshgrid(x_lon, y_lat)


    # PLOT_ONLY:
    # Define filled contour levels and plot
    color_levels = np.arange(-1e3, 10e3, 1e3)
    ET_Lambert_Contour = m.contourf(x0, y0, rootgrp_orig['ECHO_TOP'][0][0], color_levels, latlon=True, cmap=cm.coolwarm)
    m.colorbar(ET_Lambert_Contour, location='right', pad='5%')
    plt.show(block=False)
    PATH_FIGURE_PROJECTION = gb.PATH_PROJECT + '\\Output\\EchoTop_Projected\\' \
                             + dates[0].isoformat().replace(':', '_') + '.' + gb.FIGURE_FORMAT
    plt.savefig(PATH_FIGURE_PROJECTION, format=gb.FIGURE_FORMAT)
    plt.close()'''


    rootgrp_sorted = Dataset(str_sorted_file, 'w', format="NETCDF4")

    # Add Dimensions: t, X\\YPoints
    rootgrp_sorted.createDimension('time', size=SIZE_TIME)
    rootgrp_sorted.createDimension('x0', size=5120)
    rootgrp_sorted.createDimension('y0', size=3520)
    rootgrp_sorted.createDimension('z0', size=1)

    # Add Variables: t, X\\YPoints, lat\\lon, echotop
    rootgrp_sorted.createVariable('time', datatype=float, dimensions=('time'), zlib=True, complevel=6)
    rootgrp_sorted.variables['time'].units = time.units
    rootgrp_sorted.variables['time'].calendar = time.calendar
    rootgrp_sorted.variables['time'] = time
    del time
    rootgrp_sorted.createVariable('lons', datatype=float, dimensions=('y0','x0'), zlib=True, complevel=6,
                                  least_significant_digit=5)
    rootgrp_sorted.variables['lons'].units = 'degrees longitude'
    rootgrp_sorted.variables['lons'][:] = x0[:]
    del x0
    rootgrp_sorted.createVariable('lats', datatype=float, dimensions=('y0','x0'), zlib=True, complevel=6,
                                  least_significant_digit=5)
    rootgrp_sorted.variables['lats'].units = 'degrees latitude'
    rootgrp_sorted.variables['lats'][:] = y0[:]
    del y0
    rootgrp_sorted.createVariable('alt', datatype=float, dimensions=('z0'), zlib=True, complevel=6,
                                  least_significant_digit=5)
    rootgrp_sorted.variables['alt'].units = 'meters'
    rootgrp_sorted.variables['alt'][:] = z0[:]
    del z0
    rootgrp_sorted.createVariable(var, datatype=float, dimensions=('time', 'z0', 'y0', 'x0'), zlib=True,
                                  complevel=6, least_significant_digit=5, fill_value=fillval)
    rootgrp_sorted.variables[var].units = rootgrp_orig.variables[var].units
    rootgrp_sorted.variables[var].add_offset = rootgrp_orig.variables[var].add_offset
    rootgrp_sorted.variables[var].scale_factor = rootgrp_orig.variables[var].scale_factor
    rootgrp_sorted.variables[var][:] = rootgrp_orig.variables[var][:SIZE_TIME]
    # del echotop
    rootgrp_orig.close()
    rootgrp_sorted.close()

    print('converted ' + file)
    return


def main():
    PATH_NC_RAW = {'et': gb.PATH_PROJECT + '\\Data\\EchoTop\\', 'vil': gb.PATH_PROJECT + '\\Data\\VIL\\'}
    products = {'vil': 'VIL', 'et': 'ECHO_TOP'}
    prod = 'et'

    PATH_NC_LOG = gb.PATH_PROJECT + '/Output/{}/{}_Prep.log'.format(products[prod], products[prod])
    logging.basicConfig(filename=PATH_NC_LOG, filemode='w', level=logging.INFO)
    sttime = datetime.datetime.now()
    logging.info(' Started: ' + sttime.isoformat())

    os.chdir(PATH_NC_RAW[prod])
    process_file_partial = partial(process_file, products[prod], PATH_NC_RAW[prod], PATH_NC_LOG)
    files_to_delete = []
    dirs = [x for x in os.listdir('.') if os.path.isdir(x) and not x.__contains__('Sorted')]
    for dir in dirs:
        nc_files = ["{}\\{}".format(os.path.abspath(dir),x) for x in os.listdir(dir) if x.__contains__('.nc')]

        if gb.BLN_MULTIPROCESS:
            with futures.ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as executor:
                executor.map(process_file_partial, nc_files)
        else:
            for file in nc_files:
                process_file_partial(file)

        files_to_delete.append([os.path.abspath(x) for x in os.listdir() if not os.path.isdir(x)])

    yndelete = input('delete unsorted files? [y/n]')
    if yndelete.lower() == 'y':
        for file in files_to_delete:
            os.remove(file)

    edtime = datetime.datetime.now()
    delta = edtime - sttime
    logging.info(' completed: ' + edtime.isoformat())
    logging.info(' execution time: ' + str(delta.total_seconds()) + ' s')

    os.chdir(gb.PATH_PROJECT)

    print('Execution complete. Check log file (' + PATH_NC_LOG + ') for details')


if __name__ == '__main__':
    main()
