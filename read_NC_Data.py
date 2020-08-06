from netCDF4 import Dataset, num2date, date2num, MFDataset
import numpy as np
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib import cm
import EchoTop_Data_Tools as et
from mpl_toolkits.mplot3d import axes3d
from datetime import datetime



rootgrp = Dataset("Data/EchoTop/ciws.EchoTop.20200622T232730Z.nc", "r", format="netCDF4")

#TODO: Aggregrate dimension for multi-file access
#mfrootgrp = MFDataset("Data/EchoTop/ciws.EchoTop.20200622T23***0Z.nc")

print("Variables:")
for v in rootgrp.variables:
    print(v)

x0 = rootgrp.variables["x0"]
y0 = rootgrp.variables["y0"]
z0 = rootgrp.variables["z0"]
echotop = rootgrp.variables["ECHO_TOP"]
echotop_f = rootgrp.variables["ECHO_TOP_FLAGS"]
time = rootgrp.variables["time"]



# Unlock Masked Data
for v in [x0, y0, z0, echotop, echotop_f, time]:
    if v.mask:
        v.set_auto_mask(False)
        v = v[::]

dates = num2date(time[:], units=time.units, calendar=time.calendar)


# check for poor echotop readings based on status flags
# NO LONGER USED
arr_echotop_f = echotop_f[::]
#arr_temp = arr_echotop_f.flat
#for temp in arr_temp:
#    if (temp == 1 or temp == 2):
#        print("FLAG: ",temp)


arr_echotop = echotop[::]
#for temp in arr_echotop.flat:
#    if (temp != -1000.):
#        print("ALT: ",temp)

# Plot EchoTop Readings
#TODO: Map Coordinates matching
fig = plt.figure()
ax = fig.gca(projection='3d')
xm,ym = np.meshgrid(x0,y0)
surf = ax.plot_surface(xm,ym,echotop[0][0],cmap=cm.coolwarm)
plt.title("EchoTops for " + time.string)
ax.view_init(elev=90,azim=-90)
fig.colorbar(surf, shrink=0.5, aspect=5)
plt.show(block=False)
plt.savefig("Output/EchoTop_Raw.png",format='png')
plt.close()

# Create Basemap, plot on Latitude/Longitude scale
m = Basemap(width=12000000,height=9000000,rsphere=et.R_EARTH, \
            resolution='l',area_thresh=1000.,projection='lcc',\
            lat_0=et.LAT_ORIGIN,lon_0=et.LONG_ORIGIN)
#m.drawmapboundary(fill_color='aqua')
#m.fillcontinents(color='coral',lake_color='aqua')
m.drawcoastlines()


# Draw Meridians and Parallels
Parallels = np.arange(0.,80.,10.)
Meridians = np.arange(10.,351.,20.)
#Labels = [left,right,top,bottom]
m.drawparallels(Parallels,labels=[False,True,True,False])
m.drawmeridians(Meridians,labels=[True,False,False,True])
fig2 = plt.gca()

# Map to Lambert Conformal Projection
# x0,y0: meters from lat:38 long:-90
# xlat,ylong: equivalent lat/long values
# x1,y1: mapped lat/long values to basemap figure
#TODO: more efficient method, search docs
ylat, xlong = et.relToLatLong(x0[:],y0[:],et.LAT_ORIGIN,et.LONG_ORIGIN,et.R_EARTH)
xlongm,ylatm = np.meshgrid(xlong,ylat)
#x1,y1 = m(xlongm,ylatm)

# define filled contour levels
clevs = np.arange(-1e3,10e3,1e3)
#xcontour = np.reshape(x1,-1)
#ycontour = np.reshape(y1,-1)
#et_contour = np.reshape(echotop[0][0],-1)
ET_Lambert_Contour = m.contourf(xlongm,ylatm,echotop[0][0],clevs,latlon=True,cmap=cm.coolwarm)
m.colorbar(ET_Lambert_Contour,location='right',pad='5%')
plt.show(block=False)
plt.savefig("Output/EchoTop_Projected.png",format='png')
plt.close()
rootgrp.close()


