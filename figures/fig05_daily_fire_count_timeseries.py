"""
Fig. 5 - Daily VIIRS fire counts over Nepal for the full year, one panel
per year (a) 2021, (b) 2022, (c) 2023, (d) 2024.

SOURCE: methodology2.py, lines 30-80 (whole-year accumulation loop,
`daily_fire_counts_all` / `dates_all`) and lines 183-196 (the "whole
year plot" block itself). In the original file this was manually
re-run four times by editing `data_dir` and the output path comment;
here it is one function called once per year.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Generalized into a function taking `year` and producing one panel;
    call it once per year to reproduce the 2x2 figure.
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray  # noqa: F401
import xarray as xr
import geopandas as gpd

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS, VIIRS_GRIDDED_DIR, NEPAL_BOUNDARY_SHP


def whole_year_daily_fire_counts(year, nepal):
    data_dir = VIIRS_GRIDDED_DIR.format(year=year)
    files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
    if not files:
        raise FileNotFoundError(f"No NetCDF files found in {data_dir}")

    dates_all, daily_fire_counts_all = [], []
    nepal_mask = None

    for f in files:
        ds = xr.open_dataset(f)
        fire = ds["fire_count"].astype("float32")
        date = pd.to_datetime(ds["time"].values[0])
        fire = fire.rio.write_crs("EPSG:4326")

        if nepal_mask is None:
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
            nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

        fire_clip = fire.where(nepal_mask == 1)
        dates_all.append(date)
        daily_fire_counts_all.append(fire_clip.sum(dim=["lat", "lon"]).item())
        ds.close()

    return dates_all, daily_fire_counts_all


def main():
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=False)

    for ax, year in zip(axes.flatten(), STUDY_YEARS):
        dates, counts = whole_year_daily_fire_counts(year, nepal)
        ax.plot(dates, counts, color="firebrick", lw=1)
        ax.set_title(str(year))
        ax.set_xlabel("Date")
        ax.set_ylabel("Fire Count")
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
