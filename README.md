# Weather-Preprocessing
Preprocessing scripts for CIWS EchoTop Data, following:
>Aircraft Trajectory Prediction using LSTM Neural Network with Embedded Convolutional Layer  
>Pang, Y., Xu, N., & Liu, Y    
>https://www.phmpapers.org/index.php/phmconf/article/download/849/phmc_19_849    
# Using the Repo

## Environment
Project was developed in Pycharm, using Python 3.6. A list of used libraries is provided, as well as the exported Anaconda environment (*environment.yml*)
* matplotlib
  * basemap
* beautifulsoup4
* numpy
* numba
* pandas
* requests
* scipy
## Project Execution
The Python Scripts are written to be run in stages for each data-type, leading up to the generation of weather cubes.
#### Preparing Flight Files
Generating flight files requires access to a database of Integrated Flight Format (IFF) entries. Once available, the program in `Track_Gen_C-files` may be compiled to generate the appropriate flight plan (`_fp.txt.`) and track-point (`_trk.txt`) files.
Flight-plan and track-point CSV's may be dropped directly into `Data/IFF_Flight_Plans` and `Data/IFF_Track_Points` respectively. 
* `IFF_Track_Point_Prep.py` should be executed first. It will downsample the number of track-point entries and save the track-points into directores sorted by-date using the first available timestamp. Processed Track points will be saved to `Data/IFF_Track_Points/Sorted/`
* `IFF_Flight_Plan_Prep.py` May then be executed. It will parse the initially-reported waypoints and navaids into their latitude and longitude coordinates by querying [OpenNav](https://opennav.com/). These will be interpolated and, if possible, assigned a timestamp from the flight's track point file. 
  * Since OpenNav is queried to find waypoint and navaid coordinates, an internet connection is required for this script.
#### Preparing EchoTop Data  
* Echotop Data is mapped in terms of a relative distance from a reference coordinate. Executing `NC_Data_Prep.py` will convert this mapping into latitude and longitude coordinates, as well as move the file to it's sorted by-date folder, `Data/EchoTop/Sorted`.
  * Much like with the Flight file preparation, EchoTop data should be placed directly in `Data/Echotop/`
  * At current, Weather cube extraction relies on EchoTop filenames ending in the UTC-date and time of reporting.
  * Echotop data is anticipated in NetCDF-format
#### Generating Weather Cubes
* At current, Weather cubes are extracted based on the sorted track point files. Once all Track point files for a batch have been sorted, `Weather_Cubes.py` will generate a netCDF file containing the EchoTop data relevant to each flight.
# Project Parameters
All Project parameters are located in `Global_Tools.py`
* LAT_ORIGIN, LON_ORIGIN: the reference coordinates used by EchoTop databases.
* R_EARTH: The Earth's radius, in Kilometers, used to map relative data to latitude and longitude coordinates. Currently specified for EchoTop data.
* LOOKAHEAD_SECONDS: Number of seconds to extract weather cubes in advance of. Approximated as 200 seconds, in order to accommodate real-time predictions future deep-learning networks. **Currently not in use.**
* TARGET_SAMPLE_SIZE: Ideal number of entries per flight file. This number is targetted when downsampling track points or interpolating flight plans. Current value is 500, roughly a quarter the number of entries in a flight from JFK to LAX.
* FIGURE_FORMAT: When validation-figures are generated, this specifies the format to save each as. Currently specified as PNG.

# Future Work
## NDFD Data
The National Weather Service's [National Digital Data Forecast](https://vlab.ncep.noaa.gov/web/mdl/degrib-for-ndfd) contains a breadth of weather data covering North America. Future Data Processing may include these measurements.
* Batch-Downloading data is being handled in Powershell currently, and requires the installation of [degrib](https://www.weather.gov/mdl/degrib_home).
* Currently built to consider wind data, intend to use for temperature

## NDFD Weather Cubes
* Anticipating NDFD data to vary by altitude. Weather cube generation will rely on matched-tree querying, described in: 
 >   Predicting Aircraft Trajectories: A Deep Generative Convolutional Recurrent Neural Networks Approach  
 >   Yulin Liu and Mark Hansen, 2018   
 >   https://arxiv.org/ftp/arxiv/papers/1812/1812.11670.pdf

