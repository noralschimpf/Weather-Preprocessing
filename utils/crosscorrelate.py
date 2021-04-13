import numpy as np
from sklearn.preprocessing import MinMaxScaler
from scipy import interpolate
from scipy.signal import correlate2d
import matplotlib.pyplot as plt
from netCDF4 import Dataset
import warnings
import Global_Tools as gb
import tqdm
import os
import cv2
import dateutil.parser as dparser
from functools import partial
from concurrent import futures

def xcorr_srcs(src: dict, dest: dict):
    dates = [x for x in os.listdir(src['path']) if os.path.isdir('{}/{}'.format(src['path'],x)) and
             os.path.isdir('{}/{}'.format(dest['path'],x)) and not 'Sorted' in x]
    conus_xcorrs = []
    for date in dates:
        files_src = [x for x in os.listdir('{}/{}/Current'.format(src['path'],date)) if '.nc' in x]
        files_dest = [x for x in os.listdir('{}/{}/Current'.format(dest['path'],date)) if '.nc' in x]
        times_src, times_dest = [dparser.parse(x.split('.')[1]) for x in files_src], [dparser.parse(x.split('.')[1]) for x in files_dest]
        idxkeep_src, idxkeep_dest = [],[]
        for i in range(len(times_src)):
            if times_src[i] in times_dest:
                idxkeep_src.append(i)
                idxkeep_dest.append(times_dest.index(times_src[i]))
        files_src_keep = [files_src[x] for x in idxkeep_src]
        files_dest_keep = [files_dest[x] for x in idxkeep_dest]
        for f in tqdm.tqdm(range(len(files_src_keep)), desc='{}-{}'.format(src['product'],dest['product'])):
            srcgrp = Dataset('{}/{}/Current/{}'.format(src['path'],date,files_src_keep[f]))
            destgrp = Dataset('{}/{}/Current/{}'.format(dest['path'],date,files_dest_keep[f]))
            srcdat, destdat = None, None

            if not srcgrp[src['product']].shape == destgrp[dest['product']].shape:
                ciwsgrp, hrrrgrp = None, None
                ciws_lats, ciws_lons, hrrr_lats, hrrr_lons, hrrr_alts = None, None, None, None, None
                if src['product'] == 'ECHO_TOP' or src['product'] == 'VIL':
                    ciwsgrp = srcgrp[src['product']][0]
                    ciws_lats, ciws_lons = srcgrp['y0'][:], srcgrp['x0'][:]
                    hrrrgrp = destgrp[dest['product']][0]
                    hrrr_lats, hrrr_lons = destgrp['lats'][:], destgrp['lons'][:]-360
                    hrrr_alts = destgrp['alt'][:]
                elif dest['product'] == 'ECHO_TOP' or dest['product'] == 'VIL':
                    ciwsgrp = destgrp[dest['product']][0]
                    ciws_lats, ciws_lons = destgrp['y0'][:], destgrp['x0'][:]
                    hrrrgrp = srcgrp[src['product']][0]
                    hrrr_lats, hrrr_lons = srcgrp['lats'][:], srcgrp['lons'][:]
                    hrrr_alts = srcgrp['alt'][:]

                # Match Lat/Lon Coodinates
                ## Crop ciws and hrrr files
                latmin, latmax = max(hrrr_lats.min(), ciws_lats.min()), min(hrrr_lats.max(), ciws_lats.max())
                lonmin, lonmax = max(hrrr_lons.min(), ciws_lons.min()), min(hrrr_lons.max(), ciws_lons.max())

                hrrr_latkey = np.logical_and(latmin <= hrrr_lats, hrrr_lats <= latmax)
                hrrr_lonkey = np.logical_and(lonmin <= hrrr_lons, hrrr_lons <= lonmax)
                hrrr_key = np.logical_and(hrrr_lonkey,hrrr_latkey)

                # crop hrrr_key to known rectangle (1094x1059)
                for j in range(hrrr_key.shape[1]):
                    if not np.sum(hrrr_key[:,j]) == 1059:
                        hrrr_key[:,j] = np.zeros_like(hrrr_key[:,j])
                        hrrr_latkey[:,j] = np.zeros_like(hrrr_lats[:,j])
                        hrrr_lonkey[:,j] = np.zeros_like(hrrr_lons[:,j])
                hrrr_croplat = hrrr_lats[np.where(hrrr_latkey)].reshape(1059,-1)
                hrrr_croplon = hrrr_lons[np.where(hrrr_lonkey)].reshape(1059,-1)
                del hrrr_latkey; del hrrr_lonkey;


                ciws_latkey = np.logical_and(hrrr_croplat.min() <= ciws_lats, ciws_lats <= hrrr_croplat.max())
                ciws_lonkey = np.logical_and(hrrr_croplon.min() <= ciws_lons, ciws_lons <= hrrr_croplon.max())
                ciws_key = np.logical_and(np.tile(ciws_lonkey,(3520,1)),np.tile(ciws_latkey,(5120,1)).T)
                del hrrr_croplon; del hrrr_croplat;

                # Cropped Data
                ciws_crop = np.stack([ciwsgrp[x][np.where(ciws_key)].reshape(np.sum(ciws_latkey),np.sum(ciws_lonkey)) for x in range(ciwsgrp.shape[0])])
                hrrr_crop = np.stack([hrrrgrp[x][np.where(hrrr_key)].reshape(1059,-1) for x in range(hrrrgrp.shape[0])])
                del ciws_key; del hrrr_key; del ciws_latkey; del ciws_lonkey;

                ## Interpolate Cropped Grids to Match Dimensions
                pts1 = np.float32([[0,0],[0,hrrr_crop.shape[2]],[hrrr_crop.shape[1],0],[hrrr_crop.shape[1],hrrr_crop.shape[2]]])
                pts2 = np.float32([[0,0],[0,ciws_crop.shape[2]],[ciws_crop.shape[1], 0],[ciws_crop.shape[1], ciws_crop.shape[2]]])
                M = cv2.getPerspectiveTransform(pts1,pts2)
                hrrr_interp = np.stack([cv2.warpPerspective(hrrr_crop[x],M, (ciws_crop.shape[2],ciws_crop.shape[1])) for x in range(hrrr_crop.shape[0])])
                del hrrr_crop

                # Expand Elevation
                ## ET: Acerage score over all lower altitudes
                if dest['product'] == 'ECHO_TOP' or src['product'] == 'ECHO_TOP':
                    ciws_crop = np.repeat(ciws_crop,hrrr_interp.shape[0],0)
                    for z in range(len(hrrr_alts)):
                        elements_to_clear = hrrr_alts[z] > ciws_crop[z]
                        ciws_crop[z,elements_to_clear] = 0
                    grid_divisors = np.count_nonzero(ciws_crop,axis=0)
                    ciws_crop = ciws_crop/grid_divisors


                ## VIL: Average score over all altitudes
                if dest['product'] == 'VIL' or src['product'] == 'VIL':
                    ciws_crop = np.repeat(ciws_crop, hrrr_interp.shape[0],0)
                    ciws_crop = ciws_crop/hrrr_interp.shape[0]

                # Re-assign scaled matrices as src/destgrp data
                if src['product'] == 'ECHO_TOP' or src['product'] == 'VIL':
                    srcdat = ciws_crop
                    destdat = hrrr_interp
                elif dest['product'] == 'ECHO_TOP' or dest['product'] == 'VIL':
                    srcdat = hrrr_interp
                    destdat = ciws_crop

            else:
                srcdat =srcgrp[src['product']][0]
                destdat = destgrp[dest['product']][0]
            srcdat = src['scaler'].transform(srcdat.reshape(-1,1)).reshape(-1, srcdat.shape[1], srcdat.shape[2])
            destdat = dest['scaler'].transform(destdat.reshape(-1,1)).reshape(-1, destdat.shape[1], destdat.shape[2])
            for z in range(srcdat.shape[0]):
                conus_xcorrs.append(correlate2d(srcdat[z],destdat[z],mode='valid').squeeze()/srcdat[z].size)

    np.savetxt('xcorr_conus_{}-{}.txt'.format(src['product'],dest['product']),np.asarray(conus_xcorrs),delimiter=',')
    plt.hist(conus_xcorrs)
    plt.title('Cross-Correlation of Matching CONUS Measurements, {}-{}'.format(src['product'], dest['product']))
    plt.xlabel('Cross-Correlation of Measurements')
    plt.ylabel('Count')
    plt.savefig('CONUS XCorr {}-{}.png'.format(src['product'],dest['product']),dpi=300)
    plt.close()


def main():
    #Open and Cross-Correlate all matching ET-VIL CONUS Data
    PATH_CONUS = 'D:/NathanSchimpf/PyCharmProjects/Weather-Preprocessing/Data/'
    PATH_CONUS_ET = PATH_CONUS + 'EchoTop/Sorted'
    PATH_CONUS_VIL = PATH_CONUS + 'VIL/Sorted'
    PATH_CONUS_HRRR = PATH_CONUS + 'HRRR/Sorted'
    # Generate Temporary normalizers for ET/VIL CONUS Data
    etnorm = MinMaxScaler(feature_range=[0,1], )
    vilnorm = MinMaxScaler(feature_range=[0,1])
    tmpnorm = MinMaxScaler(feature_range=[0,1])
    uwindnorm = MinMaxScaler(feature_range=[0,1])
    vwindnorm = MinMaxScaler(feature_range=[0,1])
    vilnorm.fit(np.asarray([[0],[80.]]))
    etnorm.fit(np.asarray([[0.],[70000.]]))
    tmpnorm.fit(np.asarray([[150.],[350.]]))
    uwindnorm.fit(np.asarray([[-100.],[100.]]))
    vwindnorm.fit(np.asarray([[-100.],[100.]]))


    et_dict = {'path': PATH_CONUS_ET, 'product': 'ECHO_TOP', 'scaler': etnorm}
    vil_dict = {'path': PATH_CONUS_VIL, 'product': 'VIL', 'scaler': vilnorm}
    uwind_dict = {'path':PATH_CONUS_HRRR, 'product': 'uwind', 'scaler': uwindnorm}
    vwind_dict = {'path':PATH_CONUS_HRRR, 'product': 'vwind', 'scaler': vwindnorm}
    tmp_dict = {'path': PATH_CONUS_HRRR, 'product': 'tmp', 'scaler': tmpnorm}

    dsets = [et_dict, vil_dict, tmp_dict]
    dsets_dest = [uwind_dict, vwind_dict, tmp_dict]
    for src in dsets:
        if gb.BLN_MULTIPROCESS:
            func_xcorr = partial(xcorr_srcs, src)
            with futures.ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as executor:
                executor.map(func_xcorr, dsets_dest)
        else:
            for dest in dsets_dest:
                xcorr_srcs(src, dest)


    '''wc_xcorr = []
    # Generate Cross-Correlations list for all Cubes - ET v VIL
    PATH_CUBES = 'H:/TorchDir Archive/14 Days Unified 1 Minute/Weather Cubes'
    PATH_ETCUBES, PATH_VILCUBES = PATH_CUBES + '/Echo Top', PATH_CUBES + '/VIL'
    os.chdir(PATH_ETCUBES)
    dates = [x for x in os.listdir('.') if os.path.isdir(x)]
    for date in tqdm.tqdm(dates):
        files = os.listdir(date)
        etcubes, vilcubes = [],[]
        for file in files:
            vil = '{}/{}/{}'.format(PATH_VILCUBES,date,file)
            et = '{}/{}/{}'.format(PATH_ETCUBES,date,file)
            if os.path.isfile(vil) and os.path.isfile(et):
                etcubes.append(et)
                vilcubes.append(vil)

        for i in range(len(etcubes)):
            et = Dataset(etcubes[i],'r')
            vil = Dataset(vilcubes[i],'r')
            et, vil = et['Echo_Top'][:], vil['VIL'][:]
            if len(et) != len(vil):
                warnings.warn('{}: et ({}) and vil({}) length mismatch, trimming'.format(etcubes[i],len(et),len(vil)))
                newlen = min(len(et),len(vil))
                et, vil = et[:newlen], vil[:newlen]
            if len(et) > 0:
                corr = 0
                for j in range(len(et)):
                    corr = corr + correlate2d(et[j],vil[j], mode='valid').squeeze()/et.size
                wc_xcorr.append(corr/len(et))
    np.savetxt('xcorr_wc.txt',np.asarray(wc_xcorr),delimiter=',')
    plt.hist(wc_xcorr, bins=int(len(wc_xcorr)/10))
    plt.title('Cross-Correlation of Weather Cubes')
    plt.xlabel('Avg Cross-Correlation of Each Flight')
    plt.xlim([0,5e-5])
    plt.ylabel('Count')
    plt.savefig('Weather Cube XCorr.png',dpi=300)
    plt.close()
    '''





if __name__ == '__main__':
    main()