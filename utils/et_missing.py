import os, datetime
import logging

def main():
    logging.basicConfig(filename='ET Missing Files.log',filemode='w')
    os.chdir('F:/Aircraft-Data/CIWS_Echo_Top_November_2018')

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
        logging.error('{}: Folder Missing'.format(x))

    for dir in dirs:
        files = os.listdir(dir)
        if len(files) < len(ncrange):
            logging.warning('{}: {} Files Missing'.format(dir, len(ncrange) - len(files)))

    # Detailed Header
    for dir in dirs:
        files = os.listdir(dir)
        dir_date = datetime.datetime.strptime(dir, "EchoTop_%Y-%m-%d %A")
        ncexp = ['ciws.EchoTop.{}T{:0>6d}Z.nc'.format(dir_date.strftime('%Y%m%d'), x) for x in ncrange]

        if len(files) < len(ncexp):
            logging.warning("{}: {} Files Missing".format(dir, len(ncexp) - len(files)))
            missing_files = set(ncexp) - set(files)
            for x in missing_files:
                logging.warning(("\t{} Missing".format(x)))

if __name__ == '__main__':
    main()