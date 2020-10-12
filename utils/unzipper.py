import zipfile, os

'''
unzipper.py
recursively unzips files in an archived-tree
must be one level in (e.g. viewing multiple .zip files)
'''

#'Sherlock Data-20201006T003313Z-001.zip'
def unzip_recurse(path_abs_zip : str, path_output_loc : str) -> int:
    zip_name = path_abs_zip.split('/')[-1]
    folder_name = zip_name[:-4]
    with zipfile.ZipFile(path_abs_zip, 'r') as zip_ref:
        zip_ref.extractall(path_output_loc)
    os.chdir(path_output_loc)
    dirs_to_recurse = [x for x in os.listdir() if os.path.isdir(x)]
    folders_to_unzip = [x for x in os.listdir() if x.__contains__('.zip')]
    folders_output = [x[:-4] for x in folders_to_unzip]
    for i in range(len(folders_to_unzip)):
        print(str(folders_to_unzip[i]) + '\t' + str(folders_output[i]))
        unzip_recurse(folders_to_unzip[i], folders_output[i])
    for dir in dirs_to_recurse:
        os.chdir(dir)
        subdir_unzip_folders = [x for x in os.listdir() if x.__contains__('.zip')]
        for unzip in subdir_unzip_folders:
            unzip_out = os.path.abspath(unzip)[:-4]
            print(str(unzip) + '\t' + str(unzip_out))
            unzip_recurse(unzip, unzip_out)
        os.chdir('../..')
    os.chdir('../..')
    return 0

if __name__ == '__main__':
    os.chdir('C:/Users/natha/Downloads/Sherlock Data')
    unzip_folders = [x for x in os.listdir() if x.__contains__('.zip')]
    unzip_dests = [x[:-4] for x in unzip_folders]
    for i in range(len(unzip_folders)):
        unzip_recurse(unzip_folders[i], unzip_dests[i])