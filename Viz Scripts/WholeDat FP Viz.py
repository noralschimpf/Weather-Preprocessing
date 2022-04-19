import os, csv, shutil
import pandas as pd
import numpy as np

os.environ['PROJ_LIB'] = 'C:\\Users\\natha\\anaconda3\\envs\\WeatherPreProcessing\\Library\\share'
from mpl_toolkits.basemap import Basemap
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt

os.chdir('F:/Aircraft-Data/IFF Data/Wholedat/')

files = [x for x in os.listdir() if '.csv' in x and not 'DIF' in x]
for file in files:
    nda_fp, nda_fpnull, nda_ft = np.zeros((1, 4)), np.zeros((1, 4)), np.zeros((1, 4))
    with open(file, 'r', newline='') as f:
        reader = csv.reader(f, delimiter=',')
        for line in reader:
            if line[0] == '3':
                nda_line = np.array([line[1], line[9], line[10], float(line[11]) * 100], dtype='float').reshape(1, 4)
                if len(nda_ft) == 1 and (nda_ft == np.zeros_like(nda_ft)).all():
                    nda_ft[0] = nda_line
                else:
                    nda_ft = np.concatenate((nda_ft, nda_line))
            elif line[0] == '4':
                nda_line = np.array([line[1], '400.', '400.', '400.'], dtype='float').reshape(1, 4)
                if line[6] == '0xE02':
                    if len(nda_fpnull) == 1 and (nda_fpnull == np.zeros_like(nda_fpnull)).all():
                        nda_fpnull[0] = nda_line
                    else:
                        nda_fpnull = np.concatenate((nda_fpnull, nda_line))
                else:
                    if len(nda_fp) == 1 and (nda_fp == np.zeros_like(nda_fp)).all():
                        nda_fp[0] = nda_line
                    else:
                        nda_fp = np.concatenate((nda_fp, nda_line))
    for nda in [nda_fp, nda_fpnull]:
        for row in nda:
            ft_idx = np.where(np.abs(row[0] - nda_ft[:, 0]) == np.min(np.abs(row[0] - nda_ft[:, 0])))[0][0]
            row[1:] = nda_ft[ft_idx, 1:]

    m = Basemap(projection='merc', llcrnrlat=20., urcrnrlat=50.,
                llcrnrlon=-123., urcrnrlon=-67., resolution='l',
                rsphere=6370997, lat_0=40., lon_0=-98., lat_ts=20.)
    m.drawcoastlines()
    Parallels = np.arange(0., 80., 10.)
    Meridians = np.arange(10., 351., 20.)
    # Labels = [left,right,top,bottom]
    m.drawparallels(Parallels, labels=[False, True, True, False])
    m.drawmeridians(Meridians, labels=[True, False, False, True])
    fig = plt.gca()
    m.plot(nda_ft[:, 2], nda_ft[:, 1], latlon=True, color='blue', label='Flight Track')
    m.scatter(nda_fp[:, 2], nda_fp[:, 1], latlon=True, color='red', marker='.', label='Flight Plan Updates')
    m.scatter(nda_fpnull[:, 2], nda_fpnull[:, 1], latlon=True, color='green', marker='.',
              label='Flight Plan Updates (0xE02)')
    plt.title(file.replace('_wholedat.csv', ' Flight Track and Plan Changes'))
    plt.legend()
    plt.savefig(file.replace('.csv', '.png'), dpi=300)
    plt.close()

    fig = plt.figure(); ax = plt.axes(projection='3d')
    ax.plot(nda_ft[:, 2], nda_ft[:, 1], nda_ft[:, 3], color='blue', label='Track Points')
    ax.scatter(nda_fp[:, 2], nda_fp[:, 1], nda_fp[:, 3], color='red', label='Flight Plan Updates')
    ax.scatter(nda_fpnull[:, 2], nda_fpnull[:, 1], nda_fpnull[:, 3], color='green', label='Flight Plan Updates (0xE02)')
    ax.set_xlabel('Degrees Latitude'); ax.set_ylabel('Degrees Longitude'); ax.set_zlabel('Altitude')
    plt.title(file.replace('_wholedat.csv', ' Flight Track and Plan Changes'))
    plt.legend()
    plt.savefig(file.replace('.csv', '4D.png'), dpi=300)
    plt.close()