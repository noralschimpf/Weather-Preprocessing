import numpy as np
import pandas as pd
import os


# For each Flight Track, collect array of timesteps
PATH_FT = 'F:/Aircraft-Data/IFF Data/Flight Track Data - JFK to LAX'
dirs = [x for x in os.listdir(PATH_FT) if os.path.isdir(os.path.join(PATH_FT, x))]

nda_timesteps = np.array(())

for date in dirs:
    path_date = os.path.join(PATH_FT, date)
    files = [x for x in os.listdir(path_date) if x.__contains__('Flight_Track') and x.__contains__('.txt')]
    print('Reading {}'.format(date))
    for ft in files:
        ft_path = os.path.join(path_date, ft)
        df_ft = pd.read_csv(ft_path, names=['callsign', 'time', 'lat', 'lon', 'alt', 'gndspeed', 'course'])
        df_ft = df_ft.sort_values(by='time')
        times = df_ft['time'].values
        deltas = [times[i+1] - times[i] for i in range(len(times)-1)]
        nda_timesteps = np.append(nda_timesteps, deltas)
        
nda_timesteps.tofile('timesteps.csv', sep=',')