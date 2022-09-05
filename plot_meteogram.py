import time
from tqdm.contrib.concurrent import process_map
import sys
from utils import get_city_coordinates, processes, folder_images
import metpy.calc as mpcalc
import xarray as xr
from matplotlib.dates import DateFormatter
from cdo import Cdo
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


print('Starting script to plot meteograms')

# Get the projection as system argument from the call so that we can
# span multiple instances of this script outside
if not sys.argv[1:]:
    print('City not defined, falling back to default (Hamburg)')
    cities = ['Hamburg']
else:
    cities = sys.argv[1:]


def main():
    dset = xr.open_dataset('/home/ekman/ssd/guido/ecmwf-ens/2t.grib2')
    abs_time = (dset.valid_time.dt.dayofyear.astype(str).astype(object) +
                    np.char.zfill(dset.valid_time.dt.hour.astype(str), 2).astype(object)).astype(int).compute()
    del dset

    # read climatology
    clima = xr.open_dataset(
        '/home/ekman/guido/climatologies/clima_1981-2010_CSFR_t_850.nc').squeeze().sel(time='2010')

    clima['abs_time'] = (clima.time.dt.dayofyear.astype(str).astype(object) +
                         np.char.zfill(clima.time.dt.hour.astype(str), 2).astype(object)).astype(int)
    clima = clima.assign_coords({'time': clima['abs_time']})
    clima = clima.sel(time=abs_time, method='nearest')
    #
    clima_t2 = xr.open_dataset(
        '/home/ekman/guido/climatologies/clima_1981-2010_CSFR_t_2m.nc').squeeze().sel(time='2010')
    clima_t2['abs_time'] = (clima_t2.time.dt.dayofyear.astype(str).astype(object) +
                            np.char.zfill(clima_t2.time.dt.hour.astype(str), 2).astype(object)).astype(int)
    clima_t2 = clima_t2.assign_coords({'time': clima_t2['abs_time']})
    clima_t2 = clima_t2.sel(time=abs_time, method='nearest')

    cdo = Cdo(tempdir="/home/ekman/ssd/guido/ecmwf-ens/")
    it = []
    for city in cities:
        lon, lat = get_city_coordinates(city)
        filename = cdo.remapnn(f'lon={lon}/lat={lat}',
                               input='-merge /home/ekman/ssd/guido/ecmwf-ens/*.grib2', options='-P 12')
        d = xr.open_dataset(filename, engine='cfgrib').squeeze().copy()
        c = clima.sel(lon=lon, lat=lat, method='nearest').copy()
        c2 = clima_t2.sel(lon=lon, lat=lat, method='nearest').copy()
        d.attrs['city'] = city
        d['t_clim'] = xr.DataArray(c['t'].values,
                                   dims=d['t'].dims[1:],
                                   attrs=d['t'].attrs)
        d['2t_clim'] = xr.DataArray(c2['2t'].values,
                                    dims=d['t'].dims[1:],
                                    attrs=d['t'].attrs)
        d['tp'] = d['tp'].diff(dim='step')
        it.append(d)
        del d

    process_map(plot, it, max_workers=processes, chunksize=2)


def plot(dset_city):
    city = dset_city.attrs['city']
    nrows = 3
    ncols = 1
    sns.set(style="white")

    time = pd.to_datetime(dset_city['valid_time'].values)
    # Array needed for the box plot
    pos = np.array((time - time[0]) / pd.Timedelta('1 hour')).astype("int")

    print('Producing meteogram for %s' % city)
    # Recover units which somehow are deleted by interpolate_na,
    # no idea why....
    dset_city['t2m'].attrs['units'] = 'K'
    dset_city['t'].attrs['units'] = 'K'
    dset_city['tp'].attrs['units'] = 'm'
    # dset_city['10u'].attrs['units'] = 'm/s'
    # dset_city['10v'].attrs['units'] = 'm/s'
    dset_city['t2m'] = dset_city['t2m'].metpy.convert_units(
        'degC').metpy.dequantify()
    dset_city['t'] = dset_city['t'].metpy.convert_units(
        'degC').metpy.dequantify()
    dset_city['tp'] = dset_city['tp'].metpy.convert_units(
        'mm').metpy.dequantify()
    dset_city['t_clim'] = dset_city['t_clim'].metpy.convert_units(
        'degC').metpy.dequantify()
    dset_city['2t_clim'] = dset_city['2t_clim'].metpy.convert_units(
        'degC').metpy.dequantify()
    # wind_speed = mpcalc.wind_speed(
    #     dset_city['10u'], dset_city['10v']).metpy.convert_units('kph').metpy.dequantify()

    fig = plt.figure(1, figsize=(9, 10))
    ax1 = plt.subplot2grid((nrows, ncols), (0, 0))
    ax1.set_title("ECMWF-ENS meteogram for "+city+" | Run " +
                  (time[0]-np.timedelta64(3, 'h')).strftime('%Y%m%d %H UTC'))
    bplot = ax1.boxplot(dset_city['t2m'].values, patch_artist=True,
                        showfliers=False, positions=pos, widths=2.5)
    for box in bplot['boxes']:
        box.set(color='LightBlue')
        box.set(facecolor='LightBlue')

    ax1.plot(pos, dset_city['t2m'].mean(dim='number'), 'r-', linewidth=1)
    ax1.plot(pos, dset_city['2t_clim'], '-',
             color='gray', linewidth=3, alpha=0.5)
    ax1.set_xlim(pos[0], pos[-1])
    ax1.set_ylabel("2m Temp. [C]", fontsize=8)
    ax1.yaxis.grid(True)
    ax1.xaxis.grid(True, color='gray', linewidth=0.2)
    ax1.tick_params(axis='y', which='major', labelsize=8)
    ax1.tick_params(axis='x', which='both', bottom=False)

    ax2 = plt.subplot2grid((nrows, ncols), (1, 0))
    bplot_rain = ax2.boxplot(dset_city['tp'].values, patch_artist=True,
                             showfliers=False, positions=pos, widths=2.5)
    for box in bplot_rain['boxes']:
        box.set(color='LightBlue')
        box.set(facecolor='LightBlue')

    ax2.plot(pos, dset_city['tp'].mean(dim='number'), 'r-', linewidth=1)
    ax2.set_ylim(bottom=0)
    ax2.set_xlim(pos[0], pos[-1])
    ax2.yaxis.grid(True)
    ax2.set_ylabel("Precipitation [mm]", fontsize=8)
    ax2.xaxis.grid(True, color='gray', linewidth=0.2)
    ax2.tick_params(axis='y', which='major', labelsize=8)

    ax4 = plt.subplot2grid((nrows, ncols), (2, 0))
    ax4.plot(time, dset_city['t'].values.T, '-', linewidth=0.8)
    ax4.plot(time, dset_city['t_clim'].values, '-', linewidth=2, color='gray')
    ax4.set_xlim(time[0], time[-1])
    ax4.set_ylabel("850 hPa Temp. [C]", fontsize=8)
    ax4.tick_params(axis='y', which='major', labelsize=8)
    ax4.yaxis.grid(True)
    ax4.xaxis.grid(True)
    ax4.xaxis.set_major_locator(mdates.DayLocator())
    ax4.xaxis.set_major_formatter(DateFormatter('%d %b %Y'))

    ax4.annotate('Grid point %3.1fN %3.1fE' % (dset_city.latitude, dset_city.longitude),
                 xy=(0.7, -0.7), xycoords='axes fraction', color="gray")

    fig.subplots_adjust(hspace=0.1)
    fig.autofmt_xdate()

    plt.savefig(folder_images+"meteogram_"+city, dpi=100, bbox_inches='tight')
    plt.clf()


if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time()-start_time
    print("script took " + time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
