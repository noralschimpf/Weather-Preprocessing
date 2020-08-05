from netCDF4 import Dataset, num2date, date2num, MFDataset
import numpy as np
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib import cm
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


# Create Basemap, plot on Latitude/Longitude scale
m = Basemap(width=12000000,height=9000000,rsphere=6370997, \
            resolution='l',area_thresh=1000.,projection='lcc',\
            lat_0=38.,lon_0=-90.)
m.drawmapboundary(fill_color='aqua')
m.fillcontinents(color='coral',lake_color='aqua')
m.drawcoastlines()

# Draw Meridians and Parallels
Parallels = np.arange(0.,80.,10.)
Meridians = np.arange(10.,351.,20.)
#Labels = [left,right,top,bottom]
m.drawparallels(Parallels,labels=[False,True,True,False])
m.drawmeridians(Meridians,labels=[True,False,False,True])
fig2 = plt.gca()


# Plot EchoTop Readings
#TODO: Map Coordinates matching
fig = plt.figure()
ax = fig.gca(projection='3d')
x1,y1 = np.meshgrid(x0,y0)
surf = ax.plot_surface(x1,y1,echotop[0][0],cmap=cm.coolwarm)
plt.title("EchoTops for " + time.string)
ax.view_init(elev=90,azim=-90)
fig.colorbar(surf, shrink=0.5, aspect=5)
plt.show()

# Map to Lambert Conformal Projection
#x0,y0: meters from lat:38 long:-90
#x1,y1: equivalent lat/long values

rootgrp.close()
