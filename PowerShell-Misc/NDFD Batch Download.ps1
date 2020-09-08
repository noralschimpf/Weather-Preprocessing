# batch download reported top-of-the-hour data given an archived date
# Filtering Metadata based on
#   https://www.weather.gov/media/mdl/ndfd/NDFDelem_fullres_201906.xls



#TODO: Set as Function Variables

$STR_DOWNLOAD_DAY = '2018-11-01'
$BATCH_ONLY = $TRUE


$PATH_OUTPUT_LOCATION = 'C:\Users\natha\Desktop\NDFD_Downloads'
$PATH_DOWNLOADED_WINDDIR = 'C:\Users\natha\Desktop\NDFD_Downloads\WindDir\'
$PATH_DOWNLOADED_WINDSPD = 'C:\Users\natha\Desktop\NDFD_Downloads\WindSpd\'
$PATH_OUTPUT_BATCHED = 'C:\Users\natha\Desktop\NDFD_Downloads\Output'
$LINK_BASE = 'https://www.ncei.noaa.gov/data/national-digital-forecast-database/access/historical/'
$degrib = 'C:\ndfd\degrib\bin\degrib.exe'


# Initialize Workspace
foreach($p in $PATH_OUTPUT_LOCATION,$PATH_DOWNLOADED_WINDDIR,$PATH_DOWNLOADED_WINDSPD,$PATH_OUTPUT_BATCHED){
    if (-Not $(Test-Path -Path ($p))){
        mkdir -Path $p
    }
}

#Set File Arguments
#Link Format Ex:
#    https://www.ncei.noaa.gov/data/national-digital-forecast-database/access/historical/201811/20181101/YBUZ98_KWBN_201811012317

$DATE_DOWNLOAD_DAY = [Datetime]::ParseExact($STR_DOWNLOAD_DAY,'yyyy-MM-dd',$null)
$DATE_DAY_PRIOR = $DATE_DOWNLOAD_DAY.AddDays(-1)

$LINK_DAY = $LINK_BASE + $DATE_DOWNLOAD_DAY.ToString('yyyyMM') + '/' + $DATE_DOWNLOAD_DAY.ToString('yyyyMMdd')
$LINK_DAY_PRIOR = $LINK_BASE + $DATE_DAY_PRIOR.ToString('yyyyMM') + '/' + $DATE_DAY_PRIOR.ToString('yyyyMMdd')

$PREFIX_WINDDIRS_CONUS = 'YBUZ87_KWBN_','YBUZ88_KWBN_','YBUZ97_KWBN_','YBUZ98_KWBN_'
$PREFIX_WINDSPDS_CONUS = 'YCUZ87_KWBN_','YCUZ88_KWBN_','YCUZ97_KWBN_','YCUZ98_KWBN_'
$PREFIX_MEASUREMENTS = $PREFIX_WINDDIRS_CONUS + $PREFIX_WINDSPDS_CONUS


#Query indexing page for dayof and day prior files
$regex = list-to-regex($PREFIX_MEASUREMENTS)

$page_day_prior = Invoke-WebRequest $LINK_DAY_PRIOR
$page_files = $page_day_prior.Links | foreach {$_.href}
$filtered_files = @($page_files) -match $(list-to-regex($PREFIX_MEASUREMENTS))


$page_day_of = Invoke-WebRequest $LINK_DAY
$page_files = $page_day_of.Links | foreach{$_.href}
$filtered_files = $filtered_files + @($page_files) -match $(list-to-regex($PREFIX_MEASUREMENTS))


#Select and download one file closest to top-of-hour for each measurement
#Workflow Download-Data
#{
    for($i=0; $i -lt ($PREFIX_MEASUREMENTS.Count-3); $i+=4)
    {
        echo("Category: " + (($i/4)+1) + "/" + $PREFIX_MEASUREMENTS.Count/4)
        $cat = $PREFIX_MEASUREMENTS[$i..$($i+3)]
        $relevant_files = @($filtered_files) -match $(list-to-regex($cat))
        $relevant_datetimes = $relevant_files | foreach {[datetime]::ParseExact($_.substring($_.length - 12, 12), 'yyyyMMddHHmm', $null)}

        $files_to_download = @()
    
    

        $hours = @(0..23)
 #       foreach -Parallel -throttlelimit 1 ($hour in $hours)
        foreach ($hour in $hours)
        {
     
            #select one file closest to the top of each hour
            $top_of_hour = $DATE_DOWNLOAD_DAY.AddHours($hour)
            #note: force toward 15' past, when closest to realtime report message
            $quarter_past = $top_of_hour.AddMinutes(15)
            $time_differences = $relevant_datetimes | foreach {$_.subtract($quarter_past)}
            $time_differences = $time_differences | foreach {if($_ -lt 0) {$_.negate()}}
            $idx_closest_file = $($time_differences | Measure -Minimum).Count
        
            #Download file to appropriate location
            $PATH_OUTPUT_FILE = ''
            #Workflow compare_prefixes{
            $comp_winddirs = Compare-Object -ReferenceObject $PREFIX_WINDDIRS_CONUS -DifferenceObject $cat
            $comp_windspds = Compare-Object -ReferenceObject $PREFIX_WINDSPDS_CONUS -DifferenceObject $cat
            #}
            #inline if statements in order to utilize parallel workflow
            if($comp_winddirs.count.equals(0)) {$PATH_OUTPUT_FILE = $PATH_DOWNLOADED_WINDDIR + $relevant_files[$idx_closest_file]}
            if($comp_windspds.count.Equals(0)) {$PATH_OUTPUT_FILE = $PATH_DOWNLOADED_WINDSPD + $relevant_files[$idx_closest_file]}

            $LINK_FILE_TO_DOWNLOAD = $LINK_BASE + $relevant_datetimes[$idx_closest_file].toString('yyyyMM') + '/' + $relevant_datetimes[$idx_closest_file].toString('yyyyMMdd') + '/' + $relevant_files[$idx_closest_file]

            Invoke-WebRequest $LINK_FILE_TO_DOWNLOAD -OutFile $PATH_OUTPUT_FILE

        }
    #}
}


#Clean the downloaded files as single-message NetCDF3s
cd $PATH_OUTPUT_LOCATION
$dirs = Get-ChildItem -Exclude 'output'
foreach($dir in $dirs)
{
    cd $dir
    $files = ls
 #   Workflow Convert-Files
    #Pass project working directory
    #{
        $PATH_DEGRIB_CFG = 'C:\Users\natha\PycharmProjects\WeatherPreProcessing\PowerShell-Misc\ncdf.cfg'

        #Param(
        #    [Parameter(Mandatory=$TRUE)]
        #       [String]$PATH_DOWNLOAD_DIR)

        #ForEach -Parallel ($file in $files)
        ForEach ($file in $files)
        {
            #inlinescript
            #{
                $filename = $PATH_OUTPUT_BATCHED +'\' + $dir.name + '\' + $file.name
                C:\ndfd\degrib\bin\degrib.exe -in $file.fullname -cfg $PATH_DEGRIB_CFG -out $filename
            #}
        }
    #}
    cd ../
}
    







Function list-to-regex ([String[]]$list) {
    $list_flat = @($list | ForEach-Object {$_})
    $regex = '('
    for($i=0; $i -lt $list_flat.Count; $i++){
        $regex = $regex + $list_flat[$i] + ')'
        if($i -lt $($list_flat.Count-1)){
            $regex = $regex + '|('
        }
    }
    Return $regex
}

Function IIf($If, $Right) {If ($If) {$Right}}