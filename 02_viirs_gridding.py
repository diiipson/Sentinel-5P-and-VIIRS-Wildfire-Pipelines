"""
Turns raw VIIRS fire swaths into a daily fire grid over Nepal.

For each day, this groups together all the satellite passes, keeps only
the fire pixels flagged nominal/high-confidence (fire mask 8 or 9), and
bins them into a grid cell that lines up exactly with the TROPOMI grid
(it reads the grid centers from a real TROPOMI file rather than just
making up its own, so the two datasets line up cell-for-cell later on).

Each daily file ends up with fire count, FRP sum/max, and day vs. night
fire counts per cell - everything downstream depends on having all of
these, which is why this version (not one of the earlier, incomplete
regridding attempts) is the one used throughout the rest of the
pipeline.

Runs once per year instead of needing to be hand-edited and re-run for
each one.
"""

import os
import re
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr

from config import (
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX,
    STUDY_YEARS, TROPOMI_REFERENCE_FILE, VIIRS_GRIDDED_DIR,
)

# EDIT: one raw VNP14IMG swath directory per year you are processing.
VIIRS_RAW_DIR_BY_YEAR = {
    year: rf"S:\viirs\VNP14IMG_002-REPLACE_ME_{year}" for year in STUDY_YEARS
}


def build_tropomi_aligned_grid(reference_file):
    """Read grid-cell centers from a real TROPOMI file so the VIIRS grid
    lines up exactly with the TROPOMI grid used in every downstream step."""
    tr = xr.open_dataset(reference_file)
    lat_centers = tr.latitude.values
    lon_centers = tr.longitude.values
    res_lat = float(lat_centers[1] - lat_centers[0])
    res_lon = float(lon_centers[1] - lon_centers[0])

    lat_bins = np.concatenate([lat_centers - res_lat / 2, [lat_centers[-1] + res_lat / 2]])
    lon_bins = np.concatenate([lon_centers - res_lon / 2, [lon_centers[-1] + res_lon / 2]])
    tr.close()
    return lat_centers, lon_centers, lat_bins, lon_bins, res_lat


def grid_one_year(data_dir, out_dir, lat_centers, lon_centers, lat_bins, lon_bins, res_lat):
    os.makedirs(out_dir, exist_ok=True)
    nlat, nlon = len(lat_centers), len(lon_centers)

    files = sorted(
        os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".nc")
    )

    files_by_day = defaultdict(list)
    for f in files:
        m = re.search(r"A(\d{7})", os.path.basename(f))
        if m:
            files_by_day[m.group(1)].append(f)

    for day, day_files in sorted(files_by_day.items()):
        daily_dfs = []
        obs_date = None

        for file_path in day_files:
            ds = xr.open_dataset(file_path)

            fire = ds[["FP_latitude", "FP_longitude", "FP_power",
                       "FP_line", "FP_sample", "FP_day"]]
            df = fire.to_dataframe().dropna().reset_index(drop=True)

            mask = ds["fire mask"].values
            df["mask"] = mask[df["FP_line"], df["FP_sample"]]
            # keep only nominal and high-confidence fire pixels (mask 8/9)
            df = df[df["mask"].isin([8, 9])]

            df = df[
                (df.FP_latitude >= LAT_MIN) & (df.FP_latitude <= LAT_MAX) &
                (df.FP_longitude >= LON_MIN) & (df.FP_longitude <= LON_MAX)
            ]

            if not df.empty:
                daily_dfs.append(df)
            if obs_date is None:
                obs_date = ds.attrs.get("RangeBeginningDate")
            ds.close()

        fire_count = np.zeros((nlat, nlon), dtype=np.int32)
        frp_sum = np.zeros((nlat, nlon), dtype=np.float32)
        frp_max = np.full((nlat, nlon), np.nan, dtype=np.float32)
        day_count = np.zeros((nlat, nlon), dtype=np.int32)
        night_count = np.zeros((nlat, nlon), dtype=np.int32)
        day_night_mode = np.full((nlat, nlon), np.nan, dtype=np.float32)

        if daily_dfs:
            df_day = pd.concat(daily_dfs, ignore_index=True)
            df_day["ilat"] = np.digitize(df_day.FP_latitude, lat_bins) - 1
            df_day["ilon"] = np.digitize(df_day.FP_longitude, lon_bins) - 1

            for (i, j), group in df_day.groupby(["ilat", "ilon"]):
                if 0 <= i < nlat and 0 <= j < nlon:
                    fire_count[i, j] = len(group)
                    frp_sum[i, j] = group.FP_power.sum()
                    frp_max[i, j] = group.FP_power.max()
                    day_count[i, j] = (group.FP_day == 1).sum()
                    night_count[i, j] = (group.FP_day == 0).sum()
                    day_night_mode[i, j] = int(group.FP_day.mode()[0])

        if obs_date is None:
            obs_date = datetime.strptime(day[1:], "%Y%j")
        obs_date = pd.to_datetime(obs_date)

        lat_bnds = np.vstack([lat_bins[:-1], lat_bins[1:]]).T
        lon_bnds = np.vstack([lon_bins[:-1], lon_bins[1:]]).T

        ds_out = xr.Dataset(
            data_vars=dict(
                fire_count=(["lat", "lon"], fire_count),
                frp_sum=(["lat", "lon"], frp_sum),
                frp_max=(["lat", "lon"], frp_max),
                day_count=(["lat", "lon"], day_count),
                night_count=(["lat", "lon"], night_count),
                day_night_mode=(["lat", "lon"], day_night_mode),
            ),
            coords=dict(
                lat=("lat", lat_centers),
                lon=("lon", lon_centers),
                time=("time", [obs_date]),
            ),
            attrs=dict(
                title="VIIRS Daily Fire Gridded Product (Nepal)",
                source="VNP14IMG",
                Conventions="CF-1.10",
                grid_resolution=f"{res_lat} degree",
                spatial_extent="Nepal",
                filtering="fire mask values 8 and 9 only",
                geospatial_lat_min=LAT_MIN, geospatial_lat_max=LAT_MAX,
                geospatial_lon_min=LON_MIN, geospatial_lon_max=LON_MAX,
                geospatial_lat_units="degrees_north",
                geospatial_lon_units="degrees_east",
                time_coverage_start=str(obs_date),
                time_coverage_end=str(obs_date),
            ),
        )

        ds_out["lat"].attrs = {"standard_name": "latitude", "long_name": "latitude",
                                "units": "degrees_north", "axis": "Y", "bounds": "lat_bnds"}
        ds_out["lon"].attrs = {"standard_name": "longitude", "long_name": "longitude",
                                "units": "degrees_east", "axis": "X", "bounds": "lon_bnds"}
        ds_out["time"].attrs = {"standard_name": "time", "long_name": "time of observation"}
        ds_out["lat_bnds"] = (("lat", "bnds"), lat_bnds)
        ds_out["lon_bnds"] = (("lon", "bnds"), lon_bnds)

        ds_out["fire_count"].attrs = {"long_name": "number of fire detections per grid cell", "units": "1"}
        ds_out["frp_sum"].attrs = {"long_name": "sum of fire radiative power", "units": "MW"}
        ds_out["frp_max"].attrs = {"long_name": "maximum fire radiative power", "units": "MW"}
        ds_out["day_count"].attrs = {"long_name": "number of daytime fire detections", "units": "1"}
        ds_out["night_count"].attrs = {"long_name": "number of nighttime fire detections", "units": "1"}
        ds_out["day_night_mode"].attrs = {
            "long_name": "dominant fire detection time (day=1, night=0)",
            "units": "1", "flag_values": [0, 1], "flag_meanings": "night day",
        }

        encoding = {"frp_max": {"_FillValue": np.nan}, "day_night_mode": {"_FillValue": np.nan}}
        out_file = os.path.join(out_dir, f"VIIRS_FIRE_NEPAL_{obs_date.strftime('%Y%m%d')}.nc")
        ds_out.to_netcdf(out_file, encoding=encoding)
        print(f"Saved: {out_file} | Total fires: {fire_count.sum()}")


def main():
    lat_centers, lon_centers, lat_bins, lon_bins, res_lat = build_tropomi_aligned_grid(
        TROPOMI_REFERENCE_FILE
    )
    for year in STUDY_YEARS:
        data_dir = VIIRS_RAW_DIR_BY_YEAR[year]
        out_dir = VIIRS_GRIDDED_DIR.format(year=year)
        print(f"--- Gridding {year}: {data_dir} -> {out_dir} ---")
        grid_one_year(data_dir, out_dir, lat_centers, lon_centers, lat_bins, lon_bins, res_lat)


if __name__ == "__main__":
    main()
