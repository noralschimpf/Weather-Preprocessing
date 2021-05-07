# Weather-Preprocessing
Preprocessing scripts for CIWS EchoTop Data, following:
>Aircraft Trajectory Prediction using LSTM Neural Network with Embedded Convolutional Layer  
>Pang, Y., Xu, N., & Liu, Y    
>https://www.phmpapers.org/index.php/phmconf/article/download/849/phmc_19_849    
# Using the Repo

## Environment
Project was developed using a combination of PyCharm, Eclipse 2020-09, and Microsoft Powershell ISE.



#### PyCharm Environment
Project was developed and tested using PyCharm 2020.1. If using PyCharm, it is strongly encouraged to disable indexing and Windows Defender scanning of the data directory.
* To disable indexing, right click on `Data` in the project explorer, and follow `mark as` | `excluded`
* When PyCharm is first started, it will display a pop-up to disable Windows Defender Scanning (`Windows Defender might be impacting your build and IDE performance. PyCharm checked the following directories:`)
  * Running the linked script (`elevator.exe`) will disable this permanently, despite the pop-up reapperaing with session launches.
  * alternatively, in windows settings: `Virus and threat protection settings` | `add or remove exclusions` | `add exclusion` and point to the data directory in this project.

The project interpreter was built as an Anaconda environment, using Python 3.6. A list of used libraries is provided, as well as the exported Anaconda environment (*environment.yml*)
* matplotlib
  * basemap
* beautifulsoup4
* numpy
* pandas
* requests

Some packages were installed via pip rather than anaconda, including
* utm
* pygrib

## Eclipse Environment
`Track_Gen.c` was modified, debugged, and compiled using Eclipse 2020-09 with the [MinGW-w64](https://sourceforge.net/projects/mingw-w64/) compiler. 
## Project Execution
The Python Scripts are written to be run in stages for each data-type, leading up to the generation of weather cubes.

#### Preparing Flight Files
Generating flight files requires access to a database of Integrated Flight Format (IFF) entries. 
* Once available, the program in `Track_Gen_C-files` should be modified to match the local source and destination file locations.
 Compiling and running the program will generate the appropriate flight plan (`_fp.txt.`) and track-point (`_trk.txt`) files. Flight-plan and track-point CSV's may be dropped directly into `Data/IFF_Flight_Plans` and `Data/IFF_Track_Points` respectively. 
* `IFF_Track_Point_Prep.py` should be executed first. It will interpolate the number of track-point entries and save the track-points into directores sorted by-date. Processed Track points will be saved to `Data/IFF_Track_Points/Sorted/`
* `IFF_Flight_Plan_Prep.py` May then be executed. It will parse the initially-reported waypoints and navaids into their latitude and longitude coordinates by querying [OpenNav](https://opennav.com/). These will be assigned a timestamp from the flight's matching track point file, and then interpolated to a 1-second interval. 
  * Since OpenNav is queried to find waypoint and navaid coordinates, an internet connection is required for this script.
* Once generated, it may be desirable to decimate both files into a smaller time interval. This can be done via `utils/final_files_downsample`, though some modifications may be necessary. Default decimation rate is 60, producing 1-minute interval files.
 
#### Preparing NOAA Data
For this project, Data was collected from [NOAA High Resolution Rapid Refresh (HRRR)](https://console.cloud.google.com/marketplace/product/noaa-public/hrrr?project=python-232920&pli=1), though other sources may be supported. 
HRRR Data is provided as gridded binary (.grib) files, and must be parsed into messages rather than directly accessed.
* HRRR Data Should be placed in`Data/HRRR`, and will be processed and placed into `Data/HRRR/Sorted`.
* HRRR Data is expected as gridded binary (`.grib`) files, and stored as NetCDF4 (`.nc`) files.

#### Preparing CIWS Data  
* CIWS Data is mapped in terms of a relative distance from a reference coordinate. Executing `NC_Data_Prep.py` will convert this mapping into latitude and longitude coordinates, as well as move the file to it's sorted by-date folder. Since avilable CIWS data was collected from separate sources (NASA Sherlock Data Warehouse and MIT Lincoln Labs directly), weather products are stored in separate folders `Data/EchoTop/Sorted` and `Data/VIL/Sorted`.
  * Much like with the Flight file preparation, EchoTop data should be placed directly in `Data/Echotop/` or `Data/VIL/`, depending on the relevant product.
  * At current, Weather cube extraction relies on EchoTop filenames ending in the UTC-date and time of reporting.
  * Echotop data is anticipated in NetCDF-format
#### Generating Weather Cubes
* At current, Weather cubes are extracted based on the sorted, interpolated flight plan files. Once all Track point files for a batch have been sorted, `Weather_Cubes.py` will generate a netCDF file containing the EchoTop data relevant to each flight.
# Project Parameters
All Project parameters are located in `Global_Tools.py`
* `LAT_ORIGIN`, `LON_ORIGIN`: the reference coordinates used by EchoTop databases.
* `R_EARTH`: The Earth's radius, in Kilometers, used to map relative data to latitude and longitude coordinates. Currently specified for EchoTop data.
* `CUBE_SIZE`: Specifies the number of points along each spatial dimension to collect for weather cubes. Currently set to 20, following Pang et. al.
* `LOOKAHEAD_SECONDS`: Number of seconds to extract weather cubes in advance of. **must be a list**. specifying 0 will read EchoTop reported data. Any non-zero value will read from EchoTop forecasts at the expected times for the flight.
* `TARGET_SAMPLE_SIZE`: Ideal number of entries per flight file. This number is targetted when downsampling track points or interpolating flight plans. Current value is -500, which defaults generation to 1 sample/second.
* `FIGURE_FORMAT`: When validation-figures are generated, this specifies the format to save each as. Currently specified as PNG.
* `BLN_MULTIPROCESS`: Global flag for enabling multiprocessing, default True. Primarily present to ease the developer's forgetfullness.
* `PROCESS_MAX`: maximum number of process generated to batch preprocessing. This will more likely be memory-constrained than CPU-constrained.
  * Tested for 1 process with default PyCharm heap (4GB).
  * Tested for 4 processes with 10Gb heap. 

# Future Work
### Optimization
* Beginning in Python 3.8, memory can be shared between processes without locking or relying on OS-dependent mechanisms. Upgrading to 3.8 may improve multiprocessing for `Weather_Cubes.py`
* At current, Basemap is a deprecated package. The use of basemap for verification and image generation should be transitioned toward [Cartopy](https://scitools.org.uk/cartopy/docs/latest/).

