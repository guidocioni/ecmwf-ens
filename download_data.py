from ecmwf.opendata import Client
import sys

client = Client(source="ecmwf")

date = sys.argv[1]
time = sys.argv[2]

if time in ['00', '12']:
    steps = list(range(3, 145, 3)) + list(range(150, 361, 6))
elif time in ['06', '18']:
    steps = list(range(3, 145, 3))

for var in ['2t','tp']:
    client.retrieve(
        stream="enfo",
        type="pf",
        date=date,
        time=time,
        param=var,
        target=f"/home/ekman/ssd/guido/ecmwf-ens/{var}.grib2",
        step=steps,
    )

client.retrieve(
    stream="enfo",
    type="pf",
    param='t',
    date=date,
    time=time,
    levelist=850,
    target="/home/ekman/ssd/guido/ecmwf-ens/t_850.grib2",
    step=steps,
)
