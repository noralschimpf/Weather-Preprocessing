import os, datetime, shutil
import logging
from dateutil import parser as dparse

def main(logsources=True, logdests=True):
    logging.basicConfig(filename='ET Missing Files.log',filemode='w')
    # os.chdir('F:/Aircraft-Data/CIWS_Echo_Top_November_2018')

    src = '/media/dualboot/New Volume/NathanSchimpf/Aircraft-Data/Sherlock Data/CIWS_Echo_Top'.replace('/',os.sep)
    dst = '/media/dualboot/New Volume/NathanSchimpf/PyCharmProjects/Weather-Preprocessing/Data/EchoTop'.replace('/',os.sep)

    ## CHECK FOR MISSING FILES FROM SOURCE DATA
    os.chdir(src)
    # Expected Timestamps
    ncrange = range(000000, 240000, 250)
    ncrange = [x for x in ncrange if x % 10000 < 6000]
    for i in range(len(ncrange)):
        if ncrange[i] % 100 == 50:
            ncrange[i] = ncrange[i] - 20

    # Expected Dates
    stdate = datetime.datetime(2018, 11, 1)
    dates_exp = [stdate + datetime.timedelta(days=x) for x in range(100)]
    dirs_exp = [x.strftime("EchoTop_%Y-%m-%d %A") for x in dates_exp]

    dirs = [x for x in os.listdir('.') if os.path.isdir(x)]

    # Summary Header
    missing_dates = set(dirs_exp) - set(dirs)
    for x in missing_dates:
        if logsources: logging.error('{}: Folder Missing'.format(x))

    for dir in dirs:
        files = os.listdir(dir)
        if len(files) < len(ncrange):
            if logsources: logging.warning('{}: {} Files Missing'.format(dir, len(ncrange) - len(files)))

    # Detailed Header
    for dir in dirs:
        files = os.listdir(dir)
        dir_date = datetime.datetime.strptime(dir, "EchoTop_%Y-%m-%d %A")
        ncexp = ['ciws.EchoTop.{}T{:0>6d}Z.nc'.format(dir_date.strftime('%Y%m%d'), x) for x in ncrange]

        if len(files) < len(ncexp):
            if logsources: logging.warning("{}: {} Files Missing".format(dir, len(ncexp) - len(files)))
            missing_files = set(ncexp) - set(files)
            for x in missing_files:
                if logsources: logging.warning(("\t{} Missing".format(x)))


    ## CHECK FOR DISCREPENCIES BETWEEN SOURCE AND SORTED FILES
    os.chdir(dst)

    # Src format: "ciws.EchoTop.YYYYMMDDTHHMMSSZ.nc" file, "EchoTop_YYYY-MM-DD DayofWeek" folder
    # Dst format: "ECHO_TOP.YYYY-MM-DDTHHMMSSZ.nc", "YYYY-MM-DD" folder
    src_dirs = dirs; src_dates = [dparse.parse(x[8:]) for x in src_dirs]
    dst_dirs = os.listdir('Sorted'); dst_dates = [dparse.parse(x) for x in dst_dirs]

        # missing dates
    missing_dates = set(src_dates) - set(dst_dates)
    for s in range(len(src_dates)):
        if logdests and src_dates[s] in missing_dates:
            try:
                shutil.copy(f'{src}{os.sep}{src_dirs[s]}')
            except Exception as e:
                logging.warning(f'SORTED DATE {x}: MISSING: {e}')

    for d, date in enumerate(dst_dates):
        curpath = os.path.abspath('.')
        dst_files = os.listdir(f'{curpath}{os.sep}Sorted{os.sep}{dst_dirs[d]}{os.sep}Current')
        s = None
        for s_idx in range(len(src_dates)):
            if src_dates[s_idx] == date: s = s_idx
        src_files = os.listdir(f'{src}{os.sep}{src_dirs[s]}')
        src_times = [dparse.parse(x.split('.')[2]) for x in src_files]
        dst_times = [dparse.parse(x.split('.')[1]) for x in dst_files]
        missing_times = set(src_times) - set(dst_times)
        for s_idx in range(len(src_times)):
            if logdests and src_times[s_idx] in missing_times:
                try:
                    dstpath = f'{dst}{os.sep}{src_dirs[s]}'
                    if not os.path.isdir(dstpath): os.makedirs(dstpath)
                    shutil.copy(f'{src}{os.sep}{src_dirs[s]}{os.sep}{src_files[s_idx]}',
                                 f'{dstpath}{os.sep}{src_files[s_idx]}')
                except Exception as e:
                    logging.warning(f'SORTED FILE MISSING AT TIME {x}: {e}')



if __name__ == '__main__':
    main(logsources=False, logdests=True)