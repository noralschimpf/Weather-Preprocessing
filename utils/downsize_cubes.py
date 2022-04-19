import os, numpy as np, tqdm
from netCDF4 import Dataset as DSet


delvars = ['latitude', 'longitude', 'altitudes', 'lookahead', 'time', 'XPoints', 'YPoints']
compvars = ['ECHO_TOP']

def create_compressed_copy(orig: str, new: str, filename: str, del_orig=False):
    nc = DSet(os.path.join(orig, filename),'r')
    ncnew = DSet(os.path.join(new,filename), 'w')
    mini, maxi = None, None
    for name, dim in nc.dimensions.items():
        ncnew.createDimension(name, len(dim) if not dim.isunlimited() else None)
    for name, var in nc.variables.items():
        if not (name in compvars or name in delvars):
            ncnew.createVariable(name, var.datatype, var.dimensions)
            ncnew.variables[name][:] = nc.variables[name][:]
            ncnew.variables[name].setncatts(nc.variables[name].__dict__)
        elif name in compvars:
            scale = 1000 if name == 'ECHO_TOP' else 1
            if name == 'ECHO_TOP': ncnew.createVariable(name, np.int8, var.dimensions, fill_value=-1, zlib=True, complevel=6)
            elif name == 'time': ncnew.createVariable(name, np.uint32, var.dimensions, zlib=True, complevel=6)
            else: ncnew.createVariable(name, np.int8, var.dimensions, zlib=True, complevel=6)
            a = (nc.variables[name][:]/scale).astype(ncnew[name].datatype)
            ncnew.variables[name][:] = a
            ncnew.variables[name].setncatts({x: nc.variables[name].__dict__[x] for x in nc.variables[name].__dict__
                                             if not x == '_FillValue'})
            if name == 'ECHO_TOP':
                ncnew.variables[name].scale_factor = scale
                ncnew.variables[name].add_offset = 0
                ncnew.variables[name].set_auto_scale(True)
                mini, maxi = a.min(), a.max()
    return [mini, maxi]

def main(path_orig: str, path_new: str):
    ranges = []
    for dir in tqdm.tqdm([x for x in os.listdir(path_orig) if os.path.isdir(os.path.join(path_orig,x))]):
        origdir = os.path.join(path_orig, dir); newdir = os.path.join(path_new,dir)
        if not os.path.isdir(newdir): os.makedirs(newdir)
        ncfiles = [x for x in os.listdir(origdir) if '.nc' in x]
        for nc in ncfiles:
            ranges.extend(create_compressed_copy(origdir, newdir, nc, del_orig=False))
    print(min(ranges), max(ranges))


if __name__ == '__main__':
    main('F:/Aircraft-Data/Weather Cubes/14 Days Unified 1 Minute', 'F:/Aircraft-Data/Weather Cubes/14 Days Compressed')