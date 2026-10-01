"""
Pulls daily NO2/CO averaged over the Himalaya zone (the High Mountain
and Middle Mountain physiographic regions), the same way
04_cluster_trace_gas_timeseries.py does it for the Terai clusters, just
for a mountain region instead of a cluster bounding box.

For each daily file, every pixel gets spatially joined against the
mountain-zone polygons, and we average whatever falls inside. Missing
days get filled in by linear interpolation so the series stays
continuous.

09_himalaya_correlation_analysis.py builds on top of this to get the
actual Metric A/B values and the Terai-vs-Himalaya correlation.
"""

import glob
import os
import re

import geopandas as gpd
import pandas as pd
import xarray as xr
from shapely.geometry import Point

from config import PHYSIOGRAPHIC_ZONES_URL, STUDY_YEARS, TROPOMI_NO2_DIR, TROPOMI_CO_DIR

MOUNTAIN_ZONE_NAMES = ["High Mountain", "Middle Mountain"]


def load_mountain_region():
    zones = gpd.read_file(PHYSIOGRAPHIC_ZONES_URL)
    return zones[zones["DESCRIPTIO"].isin(MOUNTAIN_ZONE_NAMES)]


def compute_daily_mean(nc_files, var_name, mountain_region):
    daily = []
    for f in nc_files:
        try:
            date_match = re.search(r"(\d{8})", os.path.basename(f))
            if not date_match:
                continue
            date = pd.to_datetime(date_match.group(1), format="%Y%m%d")

            ds = xr.open_dataset(f, engine="netcdf4")
            lat_name = [c for c in ds.coords if "lat" in c.lower()][0]
            lon_name = [c for c in ds.coords if "lon" in c.lower()][0]

            df = ds[[var_name]].to_dataframe().reset_index().dropna()
            gdf = gpd.GeoDataFrame(
                df,
                geometry=[Point(xy) for xy in zip(df[lon_name], df[lat_name])],
                crs="EPSG:4326",
            ).to_crs(mountain_region.crs)

            joined = gpd.sjoin(gdf, mountain_region, predicate="within")
            daily.append({"date": date, var_name: joined[var_name].mean()})
            ds.close()
        except Exception as e:
            print(f"Skipped {os.path.basename(f)} -> {e}")

    return pd.DataFrame(daily)


def himalaya_daily_series(year, mountain_region):
    no2_files = sorted(glob.glob(os.path.join(TROPOMI_NO2_DIR.format(year=year), "*.nc")))
    co_files = sorted(glob.glob(os.path.join(TROPOMI_CO_DIR.format(year=year), "*.nc")))

    daily_no2 = compute_daily_mean(no2_files, "tropospheric_NO2_column_number_density", mountain_region)
    daily_co = compute_daily_mean(co_files, "CO_column_number_density", mountain_region)

    daily_df = pd.merge(daily_no2, daily_co, on="date", how="outer").sort_values("date")
    daily_df = daily_df.set_index("date")

    full_range = pd.date_range(start=daily_df.index.min(), end=daily_df.index.max(), freq="D")
    daily_df = daily_df.reindex(full_range)
    daily_df["tropospheric_NO2_column_number_density"] = daily_df["tropospheric_NO2_column_number_density"].interpolate()
    daily_df["CO_column_number_density"] = daily_df["CO_column_number_density"].interpolate()
    daily_df["NO2_mmol"] = daily_df["tropospheric_NO2_column_number_density"] / 1000

    return daily_df.reset_index().rename(columns={"index": "date"})


def main():
    mountain_region = load_mountain_region()
    series_by_year = {}
    for year in STUDY_YEARS:
        print(f"Processing Himalaya zone series for {year}...")
        series_by_year[year] = himalaya_daily_series(year, mountain_region)
    return series_by_year


if __name__ == "__main__":
    main()
