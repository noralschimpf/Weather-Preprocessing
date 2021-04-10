import pygrib
import numpy as np
from netCDF4 import Dataset, date2num
import Global_Tools as gb
import os
import dateutil.parser as dparser
from datetime import datetime
import logging
from functools import partial
from concurrent import futures


def grb_to_grid(grb_obj):
    """Takes a single grb object containing multiple
    levels. Assumes same time, pressure levels. Compiles to a cube"""
    n_levels = len(grb_obj)
    levels = np.array([grb_element['level'] for grb_element in grb_obj])
    indexes = np.argsort(levels)[::-1] # highest pressure first
    cube = np.zeros([n_levels, grb_obj[0].values.shape[0], grb_obj[1].values.shape[1]])
    for i in range(n_levels):
        cube[i,:,:] = grb_obj[indexes[i]].values
    cube_dict = {'data' : cube, 'units' : grb_obj[0]['units'],
                 'levels' : levels[indexes]}
    return cube_dict

def hpa_to_alt(hpa: np.array):
    '''Pass pressure levels directly (not scaled)
    Simplified Conversion:
    https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf'''
    alt = (1-(hpa/1013.25)**0.190284)*145366.45
    return alt

def process_file(logfile, path_sorted, date, file):
    logging.basicConfig(filename=logfile, filemode='a', level=logging.INFO)
    grfile = pygrib.open(file)
    grb_tmp = grfile.select(name='Temperature')
    grb_uwind = grfile.select(name='U component of wind')
    grb_vwind = grfile.select(name='V component of wind')
    grbshape = grfile[1].values.shape
    lats, lons = grb_tmp[0]['latitudes'].reshape(grbshape[0],grbshape[1]), grb_tmp[0]['longitudes'].reshape(grbshape[0], grbshape[1])
    grb_tmp = grb_to_grid(grb_tmp)
    grb_uwind = grb_to_grid(grb_uwind)
    grb_vwind = grb_to_grid(grb_vwind)
    validtime = dparser.parse(str(grfile[1]['validityDate']) + 'T' + '{:04d}'.format(grfile[1]['validityTime']))
    newfile = file.split('.')
    newfile[1] = validtime.isoformat().replace(':','') + 'Z'
    newfile[-1] = 'nc'
    newfile = '.'.join(newfile)

    tmp_lvls, uwind_lvls, vwind_lvls = set(grb_tmp['levels']), set(grb_uwind['levels']), set(grb_vwind['levels'])
    if not ((grb_tmp['levels'] == grb_uwind['levels']).all() and (grb_tmp['levels'] == grb_vwind['levels']).all() and
            (grb_uwind['levels'] == grb_vwind['levels']).all()):
        logging.info('Pressure level mismatch between products: Selecting Intersection : {}'.format(os.path.join(date,file)))
        key = (tmp_lvls.intersection(uwind_lvls)).intersection(vwind_lvls)
        tmp_lvls = [True if x in key else False for x in grb_tmp['levels']]
        uwind_lvls = [True if x in key else False for x in grb_uwind['levels']]
        vwind_lvls = [True if x in key else False for x in grb_vwind['levels']]
        grb_tmp['data'] = grb_tmp['data'][np.where(tmp_lvls)]
        grb_tmp['levels'] = grb_tmp['levels'][np.where(tmp_lvls)]
        grb_uwind['data'] = grb_uwind['data'][np.where(uwind_lvls)]
        grb_uwind['levels'] = grb_uwind['levels'][np.where(uwind_lvls)]
        grb_vwind['data'] = grb_vwind['data'][np.where(vwind_lvls)]
        grb_vwind['levels'] = grb_vwind['levels'][np.where(vwind_lvls)]


    grb_tmp['levels'] = hpa_to_alt(grb_tmp['levels'])
    grb_uwind['levels'] = hpa_to_alt(grb_uwind['levels'])

    grb_vwind['levels'] = hpa_to_alt(grb_vwind['levels'])

    if not os.path.isdir(os.path.join(path_sorted,date)):
        os.makedirs(os.path.join(path_sorted,date))

    grp_save = Dataset('{}'.format(os.path.join(path_sorted,validtime.isoformat()[:10],newfile)), 'w')

    # Add Dimensions: t, X\\YPoints
    grp_save.createDimension('time', size=1)
    grp_save.createDimension('x0', size=grbshape[1])
    grp_save.createDimension('y0', size=grbshape[0])
    grp_save.createDimension('z0', size=len(grb_tmp['levels']))

    # Add Variables: t, lat/lon, tmp, u/vwind
    grp_save.createVariable('time', datatype=float, dimensions=('time'), zlib=True, complevel=6)
    grp_save['time'].units = 'seconds since 1970-01-01T00:00:00Z'
    grp_save['time'].calendar = 'gregorian'
    grp_save.variables['time'] = date2num(validtime, units=grp_save['time'].units,
                                          calendar=grp_save['time'].calendar)

    grp_save.createVariable('lons', datatype=float, dimensions=('y0','x0'), zlib=True, complevel=6,
                            least_significant_digit=5)
    grp_save.variables['lons'].units = 'degrees longitude'
    grp_save.variables['lons'][:] = lons
    del lons

    grp_save.createVariable('lats', datatype=float, dimensions=('y0','x0'), zlib=True, complevel=6,
                            least_significant_digit=5)
    grp_save.variables['lats'].units = 'degrees latitude'
    grp_save.variables['lats'][:] = lats
    del lats

    grp_save.createVariable('alt', datatype=float, dimensions=('z0'), zlib=True, complevel=6,
                            least_significant_digit=5)
    grp_save.variables['alt'].units = 'feet'
    grp_save.variables['alt'][:] = grb_tmp['levels']


    grp_save.createVariable('uwind', datatype=float, dimensions=('time', 'z0', 'y0', 'x0'), zlib=True,
                            complevel=6, least_significant_digit=5)
    grp_save.variables['uwind'].units = grb_uwind['units']
    grp_save.variables['uwind'][:] = grb_uwind['data'].reshape(1, grb_uwind['data'].shape[0],
                                                               grb_uwind['data'].shape[1], grb_uwind['data'].shape[2])
    del grb_uwind

    grp_save.createVariable('vwind', datatype=float, dimensions=('time', 'z0', 'y0', 'x0'), zlib=True,
                            complevel=6, least_significant_digit=5)
    grp_save.variables['vwind'].units = grb_vwind['units']
    grp_save.variables['vwind'][:] = grb_vwind['data'].reshape(1,grb_vwind['data'].shape[0],
                                                               grb_vwind['data'].shape[1], grb_vwind['data'].shape[2])
    del grb_vwind

    grp_save.createVariable('tmp', datatype=float, dimensions=('time', 'z0', 'y0', 'x0'), zlib=True,
                            complevel=6, least_significant_digit=5)
    grp_save.variables['tmp'].units = grb_tmp['units']
    grp_save.variables['tmp'][:] = grb_tmp['data'].reshape(1,grb_tmp['data'].shape[0],
                                                           grb_tmp['data'].shape[1], grb_tmp['data'].shape[2])
    del grb_tmp

    grp_save.close()
    print('converted ' + file)

def main():
    PATH_LOG = os.path.join(gb.PATH_PROJECT, 'Output','Grib_data.log')
    logging.basicConfig(filename=PATH_LOG, filemode='w', level=logging.INFO)
    logging.info('GRIB prep started: {}'.format(datetime.now()))
    source_data = 'D:/NathanSchimpf/Aircraft-Data/NOAA Data'
    path_sorted = os.path.join(gb.PATH_PROJECT,'Data','HRRR','Sorted')
    if not os.path.isdir(path_sorted):
        os.makedirs(path_sorted)

    os.chdir(source_data)
    dates = [x for x in os.listdir('.') if os.path.isdir(x)]
    for date in dates:
        print('\n\nSTART: {}\t{}'.format(date, datetime.now()))
        partial_process = partial(process_file, PATH_LOG, path_sorted, date)
        os.chdir(date)
        files = [x for x in os.listdir('.') if os.path.isfile(x) and '.grib2' in x]
        if gb.BLN_MULTIPROCESS:
            with futures.ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as executor:
                executor.map(partial_process, files)
        else:
            for file in files:
                partial_process(file)
        os.chdir('..')


if __name__ == '__main__':
    main()

