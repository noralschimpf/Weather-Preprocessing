import pandas as pd
from netCDF4 import Dataset
import numpy as np
import datetime
import os
import Global_Tools as gb
from concurrent.futures import ProcessPoolExecutor
from functools import partial

def downsample_file(decimation_factor: int, abspath: str):
    newfile = None

    # Save interpolated files to sorted location
    newdir = '\\'.join(abspath.split('\\')[:-3]) + '\\Interpolated'
    if not os.path.isdir(newdir):
        os.mkdir(newdir)
    newdate = abspath.split('\\')[-2]
    newdir = newdir + '\\' + newdate
    if not os.path.isdir(newdir):
        os.mkdir(newdir)

    abspath_newfile = os.path.join(newdir, os.path.split(abspath)[1])

    if abspath.__contains__('.nc'):
        grp = Dataset(abspath, 'r')
        decimation_idx = range(0,len(grp['Echo_Top']),decimation_factor)

        newfile = Dataset(abspath_newfile, 'w', type='NetCDF4')

        # Add Dimensions: t, X/YPoints
        newfile.createDimension('time', size=None)
        newfile.createDimension('XPoints', size=gb.CUBE_SIZE)
        newfile.createDimension('YPoints', size=gb.CUBE_SIZE)

        # Add Variables: t, X/YPoints, lat/lon, echotop
        newfile.createVariable('time', datatype=float, dimensions=('time'))
        newfile.variables['time'].units = 'Seconds since 1970-01-01T00:00:00'
        newfile.variables['time'].calendar = 'gregorian'
        newfile.createVariable('XPoints', datatype=float, dimensions=('XPoints'))
        newfile.variables['XPoints'].units = 'indexing for each weather cube'
        newfile.createVariable('YPoints', datatype=float, dimensions=('YPoints'))
        newfile.variables['YPoints'].units = 'indexing for each weather cube'
        newfile.createVariable('Latitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
        newfile.createVariable('Longitude', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))
        newfile.createVariable('Echo_Top', datatype=float, dimensions=('time', 'XPoints', 'YPoints'))

        # Add Metadata: Flight Callsign, Earth-radius,
        newfile.Callsign = os.path.split(abspath_newfile)[1].split('_')[4][:-3]
        newfile.rEarth = gb.R_EARTH
        if len(decimation_idx) > 0:
            # Assign Weather Cube Data to netCDF Variables
            newfile.variables['XPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
            newfile.variables['YPoints'][:] = np.arange(0, gb.CUBE_SIZE, 1)
            newfile.variables['time'][:] = grp['time'][decimation_idx]
            newfile.variables['Latitude'][:] = grp['Latitude'][decimation_idx]
            newfile.variables['Longitude'][:] = grp['Longitude'][decimation_idx]
            newfile.variables['Echo_Top'][:] = grp['Echo_Top'][decimation_idx]
        newfile.close()

    else:
        nda_tmp = np.genfromtxt(abspath, delimiter=',')
        if isinstance(nda_tmp, np.ndarray):
            newfile = nda_tmp[range(0,len(nda_tmp), decimation_factor)]
            np.savetxt(abspath_newfile, newfile, fmt='%s', delimiter=',')
        else:
            print('{} invalid file, no entries'.format(abspath))




def main():
    #rootpath = 'H:\\TorchDir Archive\\14 Days Unified 1 Second\\'
    rootpath = 'D:/NathanSchimpf/PyCharmProjects/Weather-Preprocessing/Data'
    dec_rate = 60
    # rootpath = 'F:/Aircraft-Data/Torchdir/'
    os.chdir(rootpath)
    func_process = partial(downsample_file, dec_rate)

    fp_dates = [x for x in os.listdir('IFF_Flight_Plans/Sorted') if os.path.isdir('IFF_Flight_Plans/Sorted/{}'.format(x))]
    os.chdir('IFF_Flight_Plans/Sorted')
    for date in fp_dates:
        print('Flight Plans: {}'.format(date))
        os.chdir(date)
        files = [os.path.abspath(x) for x in os.listdir('.') if os.path.isfile(x) and x.__contains__('Flight_Plan')]
        if gb.BLN_MULTIPROCESS:
            with ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as executor:
                executor.map(func_process, files)
        else:
            for file in files:
                func_process(file)
        os.chdir('..')
    os.chdir('../')


    '''ft_dates = [x for x in os.listdir('IFF_Track_Points') if os.path.isdir('IFF_Track_Points/{}'.format(x))]
    os.chdir('IFF_Track_Points')
    for date in ft_dates:
        print('Flight Tracks: {}'.format(date))
        os.chdir(date)
        files = [os.path.abspath(x) for x in os.listdir('.') if os.path.isfile(x) and x.__contains__('Flight_Track')]
        if gb.BLN_MULTIPROCESS:
            with ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as executor:
                executor.map(func_process, files)
        else:
            for file in files:
                func_process(file)
        os.chdir('..')
    os.chdir('../')

    wc_dates = [x for x in os.listdir('Weather Cubes') if os.path.isdir('Weather Cubes/{}'.format(x))]
    os.chdir('Weather Cubes')
    for date in wc_dates:
        print('Weather Cubes: {}'.format(date))
        os.chdir(date)
        files = [x for x in os.listdir('.') if os.path.isfile(x) and x.__contains__('.nc')]
        files = [os.path.abspath(x) for x in os.listdir('.') if os.path.isfile(x) and x.__contains__('.nc')]
        for file in files:
            func_process(file)
        os.chdir('..')
    os.chdir('..')'''

if __name__ == '__main__':
    main()