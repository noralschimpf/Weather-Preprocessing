import numpy as np
import pandas as pd
import os
import Global_Tools as gb

def calc_deviation(fp_interp: str, ft_interp: str):
    df_fp = pd.read_csv(fp_interp, names=['time', 'lat', 'lon', 'alt'])
    df_fp = df_fp.sort_values(by='time')
    fp = df_fp.values[:, 1:3]
    df_ft = pd.read_csv(ft_interp, names=['time','lat','lon','alt'])
    df_ft = df_ft.sort_values(by='time')
    ft = df_ft.values[:, 1:3]
    del df_fp, df_ft
    norms = []
    for i in range(len(fp)):
        if i < len(ft):
            norm = gb.km_between_coords([fp[i,0],ft[i,0]],[fp[i,1],ft[i,1]])
            norms.append(norm[1])
        else:
            print("WARNING: FP-FT length does not match")
            break
    mu = np.mean(norms)
    sigma = np.std(norms)
    return mu, sigma


def main():
    os.chdir(gb.PATH_PROJECT)
    os.chdir('../Data/')
    SORTED_FP = os.path.join(os.path.abspath('.'), 'IFF_Flight_Plans', 'Sorted')
    SORTED_FT = os.path.join(os.path.abspath('.'), 'IFF_Track_Points', 'Sorted')
    DATES = [x for x in os.listdir(SORTED_FP) if os.path.isdir(os.path.join(SORTED_FP,x))]
    df_flights = pd.DataFrame(columns=['Callsign','Date','Mean','Std Deviation'])
    for DATE in DATES:
        fp_date = os.path.join(SORTED_FP, DATE)
        ft_date = os.path.join(SORTED_FT, DATE)
        for flight_plan in os.listdir(fp_date):
            callsign = flight_plan.split('_')[-1][:-4]
            matching_ft = flight_plan.replace('Flight_Plan', 'Flight_Track')
            path_fp = os.path.join(fp_date, flight_plan)
            path_ft = os.path.join(ft_date, matching_ft)
            print("Processing {} ({})".format(callsign, DATE))
            if os.path.isfile(path_fp) and os.path.isfile(path_ft):
                m, s = calc_deviation(path_fp, path_ft)
                df_flights = df_flights.append({'Callsign': callsign, 'Date': DATE, 'Mean': m, 'Std Deviation': s},
                                               ignore_index=True)
            if not os.path.isfile(path_fp):
                print("{}: File Does Not Exist".format(path_fp))
            if not os.path.isfile(path_ft):
                print("{}: File Does Not Exist".format(path_ft))
    df_flights.to_csv(os.path.join(os.path.abspath(gb.PATH_PROJECT), 'FP-FT Deviations.csv'))

if __name__ == '__main__':
    main()