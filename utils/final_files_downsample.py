import pandas as pd
from netCDF4 import Dataset
import numpy as np
import os
import Global_Tools as gb

def downsample_file(abspath: str, decimation_factor: int):
    newfile = None
    if abspath.__contains__('.nc'):
        grp = Dataset(abspath, 'r')
        pass
    else:
        nda_tmp = np.genfromtxt(abspath, delimiter=',')
        newfile = nda_tmp[range(0,len(nda_tmp), decimation_factor)]

    # Save interpolated files to sorted location
    newdir = '\\'.join(abspath.split('\\')[:-2]) + '\\Interpolated'
    if not os.path.isdir(newdir):
        os.mkdir(newdir)
    abspath_newfile = os.path.join(newdir, os.path.split(abspath)[1])
    if abspath_newfile.__contains__('.nc'):
        pass
    else:
        np.savetxt(abspath_newfile, newfile, fmt='%s', delimiter=',')




def main():
    rootpath = '../Data'
    # rootpath = 'F:/Aircraft-Data/Torchdir/'
    os.chdir(rootpath)

    fp_dates = [x for x in os.listdir('IFF_Flight_Plans/Sorted') if os.path.isdir('IFF_Flight_Plans/Sorted/{}'.format(x))]
    for date in fp_dates:
        os.chdir('IFF_Flight_Plans/Sorted/{}'.format(date))
        files = [os.path.abspath(x) for x in os.listdir('.') if os.path.isfile(x) and x.__contains__('Flight_Plan')]
        if gb.BLN_MULTIPROCESS:
            pass #TODO: multiprocess
        else:
            for file in files:
                downsample_file(file)
        os.chdir('..')

    ft_dates = [x for x in os.listdir('Flight Tracks') if os.path.isdir('Flight Tracks/{}'.format(x))]
    for date in ft_dates:
        os.chdir(date)

        os.chdir('..')

    wc_dates = [x for x in os.listdir('Weather Cubes') if os.path.isdir('Weather Cubes/{}'.format(x))]
    for date in wc_dates:
        os.chdir(date)

        os.chdir('..')

if __name__ == '__main__':
    main()