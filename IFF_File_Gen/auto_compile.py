import os
import shutil
import subprocess
import pandas as pd
from dateutil import parser as dparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import Global_Tools as gb


def main():
    pathprj = os.path.abspath('.')
    os.chdir('/media/dualboot/New Volume/NathanSchimpf/Aircraft-Data/IFF Data/100 Days IFF')
    list_day_csvs = [os.path.abspath(x) for x in os.listdir()]
    # output_global = 'C:\\\\Users\\\\natha\\\\PycharmProjects\\\\WeatherPreProcessing\\\\Data'
    gblout = '/media/dualboot/New Volume/NathanSchimpf/Aircraft-Data/'
    os.chdir(pathprj)
    list_orig_dest_pairs = [('KSEA', 'KDEN'), ('KATL', 'KMCO'), ('KATL', 'KORD'), ('KJFK', 'KLAX'), ('KIAH', 'KBOS'),
                            ('KLAX', 'KSFO'), ('KLAS', 'KLAX'), ('KSEA', 'KPDX'), ('KSEA', 'KLAX'), ('KSFO', 'KSEA'),
                            ('KBOS', 'KLGA'), ('KATL', 'KLAGA'), ('KATL', 'KLGA'), ('KSJC', 'KLAX'), ('KPHX', 'KLAX'),
                            ('KFLL', 'KATL'), ('KHOU', 'KDAL'), ('KORD', 'KLAX'), ('KSFO', 'KLAS'), ('KSEA', 'KGEG'),
                            ('KDFW', 'KLAX'), ('KDEN', 'KPHX'), ('KDEN', 'KLAX'), ('KORD', 'KLGA'), ('KATL', 'KDFW'),
                            ('KSFO', 'KSAN'), ('KSLC', 'KDEN'), ('KORD', 'KDCA'), ('KBOS', 'KPHL'), ('KJFK', 'KSFO'),
                            ('KLAX', 'KSMF'), ('KLAS', 'KSEA'), ('KDEN', 'KLAS')]
    # list_orig_dest_pairs = [('KJFK','KLAX'),('KIAH','KBOS'),('KATL','KORD'),('KATL','KMCO'),('KSEA','KDEN')]
    # list_orig_dest_pairs = [('KORD','KLGA')]

    func_process_file = partial(pd_gen, pathprj, list_orig_dest_pairs, gblout)
    if gb.BLN_MULTIPROCESS:
        with ProcessPoolExecutor(max_workers=gb.PROCESS_MAX) as ex:
            return_code = ex.map(func_process_file, list_day_csvs)
    else:
        for csv in list_day_csvs:
            func_process_file(csv)

def pd_gen(pathprj, list_orig_dest_pairs, output_global, csvfile):
    os.chdir(pathprj)
    datestr = dparse.parse(csvfile.split('_')[2]).isoformat()[:10]
    cols = [0, 1, 2, 7, 9, 10, 11, 13, 15, 17, 18]
    fpcols = ['7','2','1','17','13','15']
    ftcols = ['7','2','9','10','11','15','17','18']

    names = [str(x) for x in cols]
    df = pd.read_csv(csvfile, usecols=cols,header=None,skiprows=3, names=names)

    #get all unique records
    df_sums = df[df['0'] == 2][['2', '7', '10', '11']]
    # df_sums = df_sums[(df['10'] in list_orig_dest_pairs) & (df['11'] in list_orig_dest_pairs)]
    dffpskip = df[df['0'] != 4].index; dffpskip = list(dffpskip + 3) + [0, 1, 2]
    dfftskip = df[df['0'] != 3].index; dfftskip = list(dfftskip + 3) + [0, 1, 2]
    del df
    df_fps = pd.read_csv(csvfile, usecols=cols, header=None, skiprows=dffpskip, names=names)
    df_fts = pd.read_csv(csvfile, usecols=cols, header=None, skiprows=dfftskip, names=names)
    # df_fps = df_fps[fpcols]; df_fts = df_fts[ftcols]

    #for each orig-dest pair
    for orig, dest in list_orig_dest_pairs:

        #run twice, inverse flight too
        for invert in [False, True]:
            #find all associated flightNumbers
            if invert: orig, dest = dest, orig
            keys = df_sums[(df_sums['10']==orig) & (df_sums['11']==dest)]['2']


            #save each unique flightNumber FP and FT
            for key in keys.to_numpy():
                dffp = df_fps[df_fps['2'] == key]
                outfile = os.path.join(output_global, "Flight Plans", datestr, "{}_{}_{}_fp.txt".format(orig,dest,dffp['7'].to_numpy()[0]))
                outdir = '/'.join(outfile.split('/')[:-1])
                if not os.path.isdir(outdir): os.makedirs(outdir)
                dffp.to_csv(outfile); del dffp

                dfft = df_fts[df_fts['2'] == key]
                outfile = os.path.join(output_global, "Flight Track", datestr, "{}_{}_{}_ft.txt".format(orig, dest, dfft['7'].to_numpy()[0]))
                outdir = '/'.join(outfile.split('/')[:-1])
                if not os.path.isdir(outdir): os.makedirs(outdir)
                dfft.to_csv(outfile); del dfft

    del df_fps, df_fts, df_sums
    print("{} COMPLETE".format(datestr))

def c_gen(pathprj, list_orig_dest_pairs, list_day_csvs, output_global):
    for orig, dest in list_orig_dest_pairs:
        for day in list_day_csvs:
            os.chdir(pathprj)
            date_substr = day.split('_')[2]
            output_fp = '{}\\\\IFF_Flight_Plans\\\\{}_{}_{}\\\\'.format(output_global,orig,dest,date_substr)
            output_ft = '{}\\\\IFF_Track_Points\\\\{}_{}_{}\\\\'.format(output_global, orig, dest, date_substr)
            if not os.path.isdir(output_fp):
                os.makedirs(output_fp)
                os.makedirs(output_ft)

            # Modify C Program
            with open('IFF_File_Gen.c','r') as fr:
                with open('IFF_File_Gen_Copy.c','w') as fw:
                    for line in fr:
                        #line = line.strip()
                        if 'const char *source_path' in line and not line[:2] == '//':
                            pathstrt = line.index('\"')
                            pathend = line.index('\"',pathstrt+1)
                            newline = line.replace(line[pathstrt:pathend+1],'\"{}\"'.format(day))
                            fw.write(newline)
                        elif 'char dest_path_header[] =' in line and not line[:2] == '//':
                            # listsplt = line.split('\\\\')
                            # listsplt[-4] = '{}_{}'.format(orig,dest)
                            # listsplt[-2] = date_substr
                            # newline = '\\\\'.join(listsplt)
                            newline = line.replace(line[line.index('='):], '= \"{}\";\n'.format(output_fp))
                            fw.write(newline)
                        elif 'char desired_orig[]' in line:
                            newline = line.replace(line[line.index('='):], '= \"{}\\0\";\n'.format(orig))
                            fw.write(newline)
                        elif 'char desired_dest[]' in line:
                            newline = line.replace(line[line.index('='):], '= \"{}\\0\";\n'.format(dest))
                            fw.write(newline)
                        else:
                            fw.write(line)
            fw.close(); fr.close()

            # compile C program
            execname = 'IFF_EXECUTABLE.out'
            gccloc = 'C:/MinGW/bin/gcc'
            cmd = [gccloc, '-O3', '-Wall', '{}/IFF_File_Gen_Copy.c'.format(os.path.abspath('.')), '-o', os.path.join(os.path.abspath('.'),execname)]
            p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
            # Execute C Program and wait
            execmd = [execname]
            retcode = subprocess.call(execmd)

            # Cleanup - delete .kml, move _trk.txt to IFF_Flight_Track
            os.chdir(output_fp)
            for file in os.listdir():
                if '.kml' in file:
                    os.remove(file)
                if '_trk.txt' in file:
                    if not os.path.isdir(os.path.join(output_ft)):
                        os.makedirs(os.path.join(output_ft))
                    shutil.move(file, os.path.join(output_ft))

if __name__ == '__main__': main()