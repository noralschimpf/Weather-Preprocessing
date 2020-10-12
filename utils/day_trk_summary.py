from netCDF4 import num2date
import pandas as pd
import os
import Global_Tools as gb

'''
day_trk_summary.py
Reads from a tree of flight track files to report:
   - first entry time
   - last entry time
   - assigned folder date
saving data to a local CSV file
'''

PATH_TRK = gb.PATH_PROJECT + '/Data/IFF_Track_Points'
os.chdir(PATH_TRK)
dirs_trk = [x for x in os.listdir() if not (x == 'Shifted' or x == 'Sorted')]
outfile = gb.PATH_PROJECT + '/Output/Flight_Track_Summary.csv'
df_out = pd.DataFrame(columns=['Callsign', 'assigned', 'first_entry', 'last_entry'])
for trkdir in dirs_trk:
    os.chdir(trkdir)
    trk_files = [x for x in os.listdir() if (os.path.isfile(x) and not x.__contains__('Summary'))]
    print('\n' + trkdir + ':')
    for file in trk_files:
        data = pd.read_csv(file).values
        callsign = data[0, 0]
        first_time = data[0, 1]
        last_time = data[-1, 1]
        first_time = num2date(first_time, units='Seconds since 1970-01-01T00:00:00Z', calendar='gregorian')
        last_time = num2date(last_time, units='Seconds since 1970-01-01T00:00:00Z', calendar='gregorian')
        df_out = df_out.append({'Callsign': callsign, 'assigned': trkdir, 'first_entry': first_time, 'last_entry': last_time}, ignore_index=True)
        print(callsign + ':\t' + first_time.isoformat() + '\t' + last_time.isoformat())
    os.chdir('../..')
df_out.to_csv(outfile)