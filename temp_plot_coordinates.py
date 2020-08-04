import os
# set PROJ_LIB to containing directory for epsg (Anaconda, Basemap)
os.environ['PROJ_LIB'] = 'C:\\Users\\natha\\anaconda3\\envs\\WeatherPreProcessing\\Library\\share'
"""
plot temperature map
(uses scipy.ndimage.filters and netcdf4-python)
"""
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from mpl_toolkits.basemap import Basemap, addcyclic
from scipy.ndimage.filters import minimum_filter, maximum_filter
from netCDF4 import Dataset

def extrema(mat,mode='wrap',window=10):
    """find the indices of local extrema (min and max)
    in the input array."""
    mn = minimum_filter(mat, size=window, mode=mode)
    mx = maximum_filter(mat, size=window, mode=mode)
    # (mat == mx) true if pixel is equal to the local max
    # (mat == mn) true if pixel is equal to the local in
    # Return the indices of the maxima, minima
    return np.nonzero(mat == mn), np.nonzero(mat == mx)

# plot 00 UTC today.
#date = datetime.now().strftime('%Y%m%d')+'00'

# open TMP_200mb.txt that stores the temperature data at 200mb height.

data = np.loadtxt('Data/TMP_200mb.txt', delimiter=',',usecols=(-3,-2,-1))
print(data[0:10])

# read lats,lons.
#lons1=data[0:100,0]
#lats=data[0:100,1]
lons1=data[:,0]
lats=data[:,1]
print('Latitude:', lats[0:10])
print('Longitude:', lons1[0:10])
nlats = len(lats)
nlons = len(lons1)
# read temperature (in Keith Unit)
#tmp=data[0:100,2]
tmp=data[:,2]
print('Temperature:', tmp[0:10])
print('tmp data size:', np.shape(tmp))
# the window parameter controls the number of highs and lows detected.
# (higher value, fewer highs and lows)
local_min, local_max = extrema(tmp, mode='wrap', window=50)


#llcrnrlat=12.19,urcrnrlat=57.33, llcrnrlon=-152.88,urcrnrlon=-50.
#m = Basemap(llcrnrlat=12.19,urcrnrlat=57.33, llcrnrlon=-152.88, urcrnrlon=-50, projection='mill')


# create Basemap instance.
m = Basemap(projection='cyl',llcrnrlat=12.19,urcrnrlat=57.33,\
            llcrnrlon=-152.88,urcrnrlon=-50.,resolution='c')

#tmp, lons = addcyclic(tmp, lons1)
#print('tmp size:', np.shape(tmp))
#print('lons size:', np.shape(lons))
#print('clevs size:', np.shape(clevs))


# find x,y of map projection grid.
x, y = m(lons1, lats)
print('x size:', np.shape(x))
print('y size:', np.shape(y))
print('x[0:10]:', x[0:10])
print('y[0:10]:', y[0:10])
#lats=np.array([20, 20, 40, 50] )
#lons1=np.array([-70, -80, -90, -100])
#lons1 = [-70, -80, -90, -100]
#lats = [20, 20, 40, 50]

#draw boundary, fill continents, draw costlines, draw parrallels, draw meridians
m.drawmapboundary(fill_color='aqua')
m.fillcontinents(color='coral',lake_color='aqua')
m.drawcoastlines(linewidth=1.25)
m.drawparallels(np.arange(10,60,10),labels=[1,1,0,0])
m.drawmeridians(np.arange(-160,-50,10),labels=[0,0,0,1])
m.scatter(x,y,marker='D',color='m')

# create figure.
fig = plt.figure(figsize=(8,4.5))
#ax = fig.add_axes([0.05,0.05,0.9,0.85])

xlows = x[local_min]
xhighs = x[local_max]
ylows = y[local_min]
yhighs = y[local_max]
lowvals = tmp[local_min]
highvals = tmp[local_max]

# plot lows as blue L's, with min temeprature value underneath.
xyplotted = []

# plot show
plt.title('Temperature Prediction Coordinates Shows in Equirectangular Projection')
plt.show()


''' 
# read lats,lons.
lats = data.variables['lat'][:]
lons1 = data.variables['lon'][:]
nlats = len(lats)
nlons = len(lons1)
# read prmsl, convert to hPa (mb).
prmsl = 0.01*data.variables['prmslmsl'][0]
# the window parameter controls the number of highs and lows detected.
# (higher value, fewer highs and lows)
local_min, local_max = extrema(prmsl, mode='wrap', window=50)
# create Basemap instance.
m =\
Basemap(llcrnrlon=0,llcrnrlat=-80,urcrnrlon=360,urcrnrlat=80,projection='mill')
# add wrap-around point in longitude.
prmsl, lons = addcyclic(prmsl, lons1)
# contour levels
clevs = np.arange(900,1100.,5.)
# find x,y of map projection grid.
lons, lats = np.meshgrid(lons, lats)
x, y = m(lons, lats)
# create figure.
fig=plt.figure(figsize=(8,4.5))
ax = fig.add_axes([0.05,0.05,0.9,0.85])
cs = m.contour(x,y,prmsl,clevs,colors='k',linewidths=1.)
m.drawcoastlines(linewidth=1.25)
m.fillcontinents(color='0.8')
m.drawparallels(np.arange(-80,81,20),labels=[1,1,0,0])
m.drawmeridians(np.arange(0,360,60),labels=[0,0,0,1])
xlows = x[local_min]; xhighs = x[local_max]
ylows = y[local_min]; yhighs = y[local_max]
lowvals = prmsl[local_min]; highvals = prmsl[local_max]
# plot lows as blue L's, with min pressure value underneath.
xyplotted = []
# don't plot if there is already a L or H within dmin meters.
yoffset = 0.022*(m.ymax-m.ymin)
dmin = yoffset
for x,y,p in zip(xlows, ylows, lowvals):
    if x < m.xmax and x > m.xmin and y < m.ymax and y > m.ymin:
        dist = [np.sqrt((x-x0)**2+(y-y0)**2) for x0,y0 in xyplotted]
        if not dist or min(dist) > dmin:
            plt.text(x,y,'L',fontsize=14,fontweight='bold',
                    ha='center',va='center',color='b')
            plt.text(x,y-yoffset,repr(int(p)),fontsize=9,
                    ha='center',va='top',color='b',
                    bbox = dict(boxstyle="square",ec='None',fc=(1,1,1,0.5)))
            xyplotted.append((x,y))
# plot highs as red H's, with max pressure value underneath.
xyplotted = []
for x,y,p in zip(xhighs, yhighs, highvals):
    if x < m.xmax and x > m.xmin and y < m.ymax and y > m.ymin:
        dist = [np.sqrt((x-x0)**2+(y-y0)**2) for x0,y0 in xyplotted]
        if not dist or min(dist) > dmin:
            plt.text(x,y,'H',fontsize=14,fontweight='bold',
                    ha='center',va='center',color='r')
            plt.text(x,y-yoffset,repr(int(p)),fontsize=9,
                    ha='center',va='top',color='r',
                    bbox = dict(boxstyle="square",ec='None',fc=(1,1,1,0.5)))
            xyplotted.append((x,y))
plt.title('Mean Sea-Level Pressure (with Highs and Lows) %s' % date)
plt.show()
'''