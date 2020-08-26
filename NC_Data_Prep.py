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

for file in nc_files:
    rootgrp_orig = Dataset(file, "r", format="netCDF4")

    time = rootgrp_orig.variables["time"]
    dates = num2date(time[:], units=time.units, calendar=time.calendar)

    # Save Data as Sorted netCDF4
    str_current_date = dates[0].isoformat()[:10]
    if (not os.listdir(PATH_ECHOTOP_RAW + '/Sorted/').__contains__(str_current_date)):
        os.mkdir(PATH_ECHOTOP_RAW + '/Sorted/' + str_current_date)
    str_sorted_file = 'Sorted/' + str_current_date + '/' + file
    copyfile(file, str_sorted_file)

    rootgrp_sorted = Dataset(str_sorted_file, 'r+', format="netCDF4")

    #TODO: Concatenate EchoTop Data by Day

    x0 = rootgrp_sorted.variables["x0"]
    y0 = rootgrp_sorted.variables["y0"]
    z0 = rootgrp_sorted.variables["z0"]
    echotop = rootgrp_sorted.variables["ECHO_TOP"]
    echotop_f = rootgrp_sorted.variables["ECHO_TOP_FLAGS"]




    # Unlock Masked Data
    for v in [x0, y0, z0, echotop, echotop_f, time]:
        if v.mask:
            v.set_auto_mask(False)
            v = v[::]



    '''
    Plot EchoTop Readings, Raw
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    xm,ym = np.meshgrid(x0, y0)
    surf = ax.plot_surface(xm, ym, echotop[0][0], cmap=cm.coolwarm)
    plt.title("EchoTops for " + time.string)
    ax.view_init(elev=90,azim=-90)
    fig.colorbar(surf, shrink=0.5, aspect=5)
    plt.show(block=False)
    plt.savefig("Output/EchoTop_Raw.png", format='png')
    plt.close()
    '''


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

    '''
    Map EchoTop x,y to Lambert Conformal Projection
      x0,y0: meters from lat:38 long:-90
      xlat,ylong: equivalent lat/long values
    '''
    y_lat, x_long = gb.rel_to_latlong(x0[:], y0[:], gb.LAT_ORIGIN, gb.LONG_ORIGIN, gb.R_EARTH)
    x_long_mesh, y_lat_mesh = np.meshgrid(x_long, y_lat)
    rootgrp_sorted.variables['x0'] = x_long
    rootgrp_sorted.variables['y0'] = y_lat


    # Define filled contour levels and plot
    color_levels = np.arange(-1e3, 10e3, 1e3)
    ET_Lambert_Contour = m.contourf(x_long_mesh, y_lat_mesh, echotop[0][0], color_levels, latlon=True, cmap=cm.coolwarm)
    m.colorbar(ET_Lambert_Contour, location='right', pad='5%')
    plt.show(block=False)
    PATH_FIGURE_PROJECTION = gb.PATH_PROJECT + '/Output/EchoTop_Projected/' \
                             + dates[0].isoformat().replace(':', '_') + '.' + gb.FIGURE_FORMAT
    plt.savefig(PATH_FIGURE_PROJECTION, format=gb.FIGURE_FORMAT)
    plt.close()


    rootgrp_sorted.close()