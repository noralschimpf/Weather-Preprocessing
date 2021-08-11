import os
import shutil
import subprocess

pathprj = os.path.abspath('.')
os.chdir('F:/Aircraft-Data/IFF Data/2018-11-01 to 2019-02-05')
list_day_csvs = [os.path.abspath(x).replace('\\','\\\\') for x in os.listdir()]
output_global = 'C:\\\\Users\\\\natha\\\\PycharmProjects\\\\WeatherPreProcessing\\\\Data'
os.chdir(pathprj)
# list_orig_dest_pairs = [('KJFK','KLAX'),('KIAH','KBOS'),('KATL','KORD'),('KATL','KMCO'),('KSEA','KDEN')]
list_orig_dest_pairs = [('KORD','KLGA')]

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