from sklearn.preprocessing import MinMaxScaler
from netCDF4 import Dataset
import numpy as np
import tqdm
import time
import os

def flt_fit(PATH_FP, dir, fp):
        fp_abspath = os.path.join(PATH_FP, dir, fp)
        nda_fp = np.genfromtxt(fp_abspath, delimiter=',')
        if len(nda_fp[:,0]) > 0:
            nda_fp[:,1] = lat_scaler.transform(nda_fp[:,1].reshape(-1,1)).reshape(-1)
            nda_fp[:,2] = lon_scaler.transform(nda_fp[:,2].reshape(-1,1)).reshape(-1)
            nda_fp[:,3] = alt_scaler.transform(nda_fp[:,3].reshape(-1,1)).reshape(-1)
        np.savetxt(fp_abspath, nda_fp, delimiter=',', newline='\n')
def fit_nc():


def main():

    product = 'ECHO_TOP'
    #PATH_PROJ = 'D:\\NathanSchimpf\\PyCharmProjects\\Weather-Preprocessing'
    PATH_PROJ = '/media/dualboot/New Volume/NathanSchimpf/PyCharmProjects/Weather-Preprocessing'
    PATH_FP = os.path.join(PATH_PROJ, 'Data','IFF_Flight_Plans','Interpolated')
    PATH_TP = os.path.join(PATH_PROJ, 'Data','IFF_Track_Points','Interpolated')
    #PATH_WC = os.path.join(PATH_PROJ, 'Output\\Weather Cubes\\{}'.format(product))
    PATH_WC = os.path.join(PATH_PROJ, 'Output/Weather Cubes/{}'.format(product))
    filename = 'Data_MinMax.csv'
    abs_filepath = os.path.join(os.path.abspath('.'), filename)

    if os.path.isfile(abs_filepath):
        print('{} already exists: skip to writing....'.format(abs_filepath))
    else:
        nda_minmax = np.empty((6,0))
        # For every Weather Cube, Log the Minimum/Maximum latitude, longitude, echo top
        wc_dates = [x for x in os.listdir(PATH_WC) if os.path.isdir(os.path.join(PATH_WC, x))]
        for dir in tqdm.tqdm(wc_dates):
            files = [y for y in os.listdir(os.path.join(PATH_WC, dir)) if y.__contains__('.nc')]
            for wc in files:
                wc_abspath = os.path.join(PATH_WC, dir, wc)
                grp = Dataset(wc_abspath, 'r', format='netCDF4')
                if len(grp['Latitude']) > 0:
                    nda_tmp = np.array([grp['Latitude'][:].min(), grp['Latitude'][:].max(), grp['Longitude'][:].min(),
                                        grp['Longitude'][:].max(), grp['VIL'][:].min(), grp['VIL'][:].max()])
                    nda_tmp = nda_tmp.reshape((6,1))
                    nda_minmax = np.hstack((nda_minmax, nda_tmp))
                grp.close()

        '''
        # for every flight plan, Log the Minimum/Maximum latitude, longitude, altitude
        fp_dates = [x for x in os.listdir(PATH_FP) if os.path.isdir(os.path.join(PATH_FP, x))]
        for dir in tqdm.tqdm(fp_dates):
            files = [y for y in os.listdir(os.path.join(PATH_FP, dir)) if y.__contains__('.txt')]
            for fp in files:
                fp_abspath = os.path.join(PATH_FP, dir, fp)
                nda_fp = np.genfromtxt(fp_abspath, delimiter=',')
                if len(nda_fp[:,0]) > 0:
                    nda_tmp = np.array([nda_fp[:,1].min(), nda_fp[:,1].max(), nda_fp[:,2].min(),
                                        nda_fp[:,2].max(), nda_fp[:,3].min(), nda_fp[:,3].max()])
                    nda_tmp = nda_tmp.reshape((6, 1))
                    nda_minmax = np.hstack((nda_minmax, nda_tmp))


        # for every flight track, Log the Minimum/Maximum latitude, longitude, altitude
        tp_dates = [x for x in os.listdir(PATH_TP) if os.path.isdir(os.path.join(PATH_TP, x))]
        for dir in tqdm.tqdm(tp_dates):
            files = [y for y in os.listdir(os.path.join(PATH_TP, dir)) if y.__contains__('.txt')]
            for tp in files:
                tp_abspath = os.path.join(PATH_TP, dir, tp)
                nda_tp = np.genfromtxt(tp_abspath, delimiter=',')
                if len(nda_tp) > 0:
                    nda_tmp = np.array([nda_tp[:, 1].min(), nda_tp[:, 1].max(), nda_tp[:, 2].min(),
                                        nda_tp[:, 2].max(), nda_tp[:, 3].min(), nda_tp[:, 3].max()])
                    nda_tmp = nda_tmp.reshape((6, 1))
                    nda_minmax = np.hstack((nda_minmax, nda_tmp))


        # Save log and identify overall min/max latitude, longitude, altitude
        print('Saving Metadata to CSV')
        np.savetxt(abs_filepath, nda_minmax, fmt='%f', delimiter=',', newline='\n')'''


    print('Generating MinMaxScalers')
    nda_minmax = np.genfromtxt(abs_filepath, delimiter=',')
    nda_minmax = nda_minmax.reshape(3,-1)

    # Create MinMax Scaler using overall parameters
    lat_scaler = MinMaxScaler(feature_range=[0,1])
    lon_scaler = MinMaxScaler(feature_range=[0,1])
    alt_scaler = MinMaxScaler(feature_range=[0,1])
    vil_scaler = MinMaxScaler(feature_range=[0,1])
    tmp_scaler = MinMaxScaler(feature_range=[0,1])
    uw_scaler = MinMaxScaler(feature_range=[0,1])
    vw_scaler = MinMaxScaler(feature_range=[0,1])

    # lat_scaler.fit(nda_minmax[0,:].reshape(-1,1))
    # lon_scaler.fit(nda_minmax[1,:].reshape(-1,1))
    # alt_scaler.fit(nda_minmax[2,:].reshape(-1,1))
    lat_scaler.fit(np.array([[24.],[50.]]))
    lon_scaler.fit(np.array([[-126.],[-66.]]))
    alt_scaler.fit(np.array([[-1000.],[64000.]]))
    #alt_scaler.fit(np.array([[-1000.],[80000.]]))
    vil_scaler.fit(np.array([[-.00244140625], [80]]))
    tmp_scaler.fit(np.array([[150],[350]]))
    uw_scaler.fit(np.array([[-150],[150]]))
    vw_scaler.fit(np.array([[-150],[150]]))

    # # Scale every Flight Plan
    # fp_dates = [x for x in os.listdir(PATH_FP) if os.path.isdir(os.path.join(PATH_FP, x))]
    # for dir in tqdm.tqdm(fp_dates, desc='scaling flight plans'):
    #     files = [y for y in os.listdir(os.path.join(PATH_FP, dir)) if y.__contains__('.txt')]
    #     for fp in files:
    #         fp_abspath = os.path.join(PATH_FP, dir, fp)
    #         nda_fp = np.genfromtxt(fp_abspath, delimiter=',')
    #         if len(nda_fp[:,0]) > 0:
    #             nda_fp[:,1] = lat_scaler.transform(nda_fp[:,1].reshape(-1,1)).reshape(-1)
    #             nda_fp[:,2] = lon_scaler.transform(nda_fp[:,2].reshape(-1,1)).reshape(-1)
    #             nda_fp[:,3] = alt_scaler.transform(nda_fp[:,3].reshape(-1,1)).reshape(-1)
    #         np.savetxt(fp_abspath, nda_fp, delimiter=',', newline='\n')
    #
    #
    # # Scale every Flight Track
    # tp_dates = [x for x in os.listdir(PATH_TP) if os.path.isdir(os.path.join(PATH_TP, x))]
    # for dir in tqdm.tqdm(tp_dates, desc='scaling trajectories'):
    #     files = [y for y in os.listdir(os.path.join(PATH_TP, dir)) if y.__contains__('.txt')]
    #     for tp in files:
    #         tp_abspath = os.path.join(PATH_TP, dir, tp)
    #         nda_tp = np.genfromtxt(tp_abspath, delimiter=',')
    #         if len(nda_tp[:,0]) > 0:
    #             nda_tp[:,1] = lat_scaler.transform(nda_tp[:,1].reshape(-1,1)).reshape(-1)
    #             nda_tp[:,2] = lon_scaler.transform(nda_tp[:,2].reshape(-1,1)).reshape(-1)
    #             nda_tp[:,3] = alt_scaler.transform(nda_tp[:,3].reshape(-1,1)).reshape(-1)
    #         np.savetxt(tp_abspath, nda_tp, delimiter=',', newline='\n')

    # # Scale every Flight Plan
    # fp_dates = [x for x in os.listdir(PATH_FP) if os.path.isdir(os.path.join(PATH_FP, x))]
    # for dir in tqdm.tqdm(fp_dates, desc='scaling flight plans'):
    #     files = [y for y in os.listdir(os.path.join(PATH_FP, dir)) if y.__contains__('.txt')]
    #     for fp in files:
    #         fp_abspath = os.path.join(PATH_FP, dir, fp)
    #         nda_fp = np.genfromtxt(fp_abspath, delimiter=',')
    #         if len(nda_fp[:,0]) > 0:
    #             nda_fp[:,1] = lat_scaler.transform(nda_fp[:,1].reshape(-1,1)).reshape(-1)
    #             nda_fp[:,2] = lon_scaler.transform(nda_fp[:,2].reshape(-1,1)).reshape(-1)
    #             nda_fp[:,3] = alt_scaler.transform(nda_fp[:,3].reshape(-1,1)).reshape(-1)
    #         np.savetxt(fp_abspath, nda_fp, delimiter=',', newline='\n')
    #
    #
    # # Scale every Flight Track
    # tp_dates = [x for x in os.listdir(PATH_TP) if os.path.isdir(os.path.join(PATH_TP, x))]
    # for dir in tqdm.tqdm(tp_dates, desc='scaling trajectories'):
    #     files = [y for y in os.listdir(os.path.join(PATH_TP, dir)) if y.__contains__('.txt')]
    #     for tp in files:
    #         tp_abspath = os.path.join(PATH_TP, dir, tp)
    #         nda_tp = np.genfromtxt(tp_abspath, delimiter=',')
    #         if len(nda_tp[:,0]) > 0:
    #             nda_tp[:,1] = lat_scaler.transform(nda_tp[:,1].reshape(-1,1)).reshape(-1)
    #             nda_tp[:,2] = lon_scaler.transform(nda_tp[:,2].reshape(-1,1)).reshape(-1)
    #             nda_tp[:,3] = alt_scaler.transform(nda_tp[:,3].reshape(-1,1)).reshape(-1)
    #         np.savetxt(tp_abspath, nda_tp, delimiter=',', newline='\n')


    # Scale every Weather Cube
    wc_dates = [x for x in os.listdir(PATH_WC) if os.path.isdir(os.path.join(PATH_WC, x))]
    for dir in tqdm.tqdm(wc_dates, desc='scaling weather cubes'):
        files = [y for y in os.listdir(os.path.join(PATH_WC, dir)) if y.__contains__('.nc')]
        for wc in files:
            wc_abspath = os.path.join(PATH_WC, dir, wc)
            #if time.time() - os.path.getmtime(wc_abspath) < 3600:
            #    continue
            grp = Dataset(wc_abspath, 'r+', format='netCDF4')
            if 'Latitude' in grp.variables.keys():
                print(wc_abspath)
                grp.close()
                os.remove(wc_abspath)
                continue
            #else:
            #    continue
            if len(grp['latitude']) > 0:
                if product == 'ECHO_TOP':
                    grp['latitude'][:] = lat_scaler.transform(grp['latitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    grp['longitude'][:] = lon_scaler.transform(grp['longitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    grp['ECHO_TOP'][:] = alt_scaler.transform(grp['ECHO_TOP'][:].reshape(-1,1)).reshape(-1,20,20)
                if product == 'VIL':
                    grp['Latitude'][:] = lat_scaler.transform(grp['Latitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    grp['Longitude'][:] = lon_scaler.transform(grp['Longitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    grp['VIL'][:] = vil_scaler.transform(grp['VIL'][:].reshape(-1,1)).reshape(-1,20,20)
                if product == 'HRRR':
                    grp['latitude'][:] = lat_scaler.transform(grp['latitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    grp['longitude'][:] = lon_scaler.transform(grp['longitude'][:].reshape(-1,1)).reshape(-1,20,20)
                    prdshape = grp['uwind'].shape
                    grp['uwind'][:] = uw_scaler.transform(grp['uwind'][:].reshape(-1,1)).reshape(prdshape)
                    grp['vwind'][:] = vw_scaler.transform(grp['vwind'][:].reshape(-1,1)).reshape(prdshape)
                    grp['tmp'][:] = tmp_scaler.transform(grp['tmp'][:].reshape(-1,1)).reshape(prdshape)
            grp.close()

    print('Done')




if __name__ == '__main__':
    main()