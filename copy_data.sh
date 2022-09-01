#!/bin/bash

# Cd into our working directory in case we're not into it already
cd "$(dirname "$0")";

echo "ecmwf: Starting processing of ECMWF ENS model data - `date`"

export MODEL_DATA_FOLDER=/home/ekman/ssd/guido/ecmwf-ens/
export IMGDIR=/home/ekman/ssd/guido/ecmwf-ens/
export HOME_FOLDER=$(pwd)
export NCFTP_BOOKMARK="mid"
DATA_DOWNLOAD=true
DATA_PLOTTING=true
DATA_UPLOAD=true

# Make sure we're using bash
export SHELL=$(type -p bash)
# We need to open many files at the same time
ulimit -Sn 8192
########################################### 

mkdir -p ${MODEL_DATA_FOLDER}

##### COMPUTE the date variables to determine the run
export MONTH=$(date -u +"%m")
export DAY=$(date -u +"%d")
export YEAR=$(date -u +"%Y")
export HOUR=$(date -u +"%H")

if [ $HOUR -ge 9 ] && [ $HOUR -lt 14 ]
then
    export RUN=00
elif [ $HOUR -ge 14 ] && [ $HOUR -lt 18 ]
then
    export RUN=06
elif [ $HOUR -ge 21 ]
then
    export RUN=12
elif [ $HOUR -ge 2 ] && [ $HOUR -lt 9 ]
then
    DAY=$(date -u -d'yesterday' +"%d")
    export RUN=18
else
    echo "Invalid hour!"
fi

echo "----------------------------------------------------------------------------------------------"
echo "ecmwf: run ${YEAR}${MONTH}${DAY}${RUN}"
echo "----------------------------------------------------------------------------------------------"

# Move to the data folder to do processing
cd ${MODEL_DATA_FOLDER} || { echo 'Cannot change to DATA folder' ; exit 1; }

# SECTION 1 - DATA DOWNLOAD ############################################################

if [ "$DATA_DOWNLOAD" = true ]; then
    echo "-----------------------------------------------"
    echo "ecmwf: Starting downloading of data - `date`"
    echo "-----------------------------------------------"
    rm ${MODEL_DATA_FOLDER}/*.grib2
    rm ${MODEL_DATA_FOLDER}/*.idx
    cp ${HOME_FOLDER}/*.py ${MODEL_DATA_FOLDER}
    #loop through forecast hours
    python download_data.py "${YEAR}${MONTH}${DAY}" "${RUN}"
fi

# SECTION 2 - DATA PLOTTING ############################################################

if [ "$DATA_PLOTTING" = true ]; then
    echo "-----------------------------------------------"
    echo "ecmwf: Starting plotting of data - `date`"
    echo "-----------------------------------------------"
    python --version
    export QT_QPA_PLATFORM=offscreen 

    python plot_meteogram.py Milano Roma Palermo Hamburg Pisa Utrecht Toulouse Sassari Napoli 
fi


# SECTION 3 - IMAGES UPLOAD ############################################################
# Use ncftpbookmarks to add a new FTP server with credentials
if [ "$DATA_UPLOAD" = true ]; then
    echo "-----------------------------------------------"
    echo "ecmwf: Starting FTP uploading - `date`"
    echo "-----------------------------------------------"

    ncftpput -R -v -DD -m ${NCFTP_BOOKMARK} ecmwf_ens ${IMGDIR}/meteogram_*
fi

# SECTION 4 - CLEANING ############################################################

echo "-----------------------------------------------"
echo "ecmwf: Finished cleaning up - `date`"
echo "----------------------------------------------_"

############################################################

cd -
