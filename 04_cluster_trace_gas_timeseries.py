"""
Pulls daily NO2/CO averaged over each hotspot cluster, alongside the
matching daily fire count - this is the data both the metrics (Metric A
and B) and the NO2/CO-vs-fire figures are built from.

Just loops over every year and every one of that year's three clusters,
reading the gridded gas and fire files in lockstep and averaging each
one over the cluster's bounding box.
"""

import glob
import os

import pandas as pd
import xarray as xr

from config import STUDY_YEARS, CLUSTER_BBOXES_BY_YEAR, TROPOMI_NO2_DIR, TROPOMI_CO_DIR, VIIRS_GRIDDED_DIR

GAS_CONFIG = {
    "NO2": {"dir_template": TROPOMI_NO2_DIR, "variable": "tropospheric_NO2_column_number_density"},
    "CO": {"dir_template": TROPOMI_CO_DIR, "variable": "CO_column_number_density"},
}


def extract_cluster_timeseries(gas_dir, gas_variable, fire_dir, bbox):
    """For one year/cluster/gas: daily cluster-mean gas column density
    and daily fire count within the same bounding box."""
    gas_files = sorted(glob.glob(os.path.join(gas_dir, "*.nc")))
    fire_files = sorted(glob.glob(os.path.join(fire_dir, "*.nc")))
    if not gas_files or not fire_files:
        raise FileNotFoundError(f"No files found in {gas_dir} or {fire_dir}")

    dates, gas_avg_list, fire_count_list = [], [], []

    for gas_f, fire_f in zip(gas_files, fire_files):
        ds_gas = xr.open_dataset(gas_f)
        date = pd.to_datetime(ds_gas["datetime_start"].values[0])
        gas_region = ds_gas[gas_variable].sel(
            latitude=slice(bbox["lat_min"], bbox["lat_max"]),
            longitude=slice(bbox["lon_min"], bbox["lon_max"]),
        )
        gas_avg = gas_region.mean(dim=["latitude", "longitude"], skipna=True).item()
        ds_gas.close()

        ds_fire = xr.open_dataset(fire_f)
        fire_region = ds_fire["fire_count"].sel(
            lat=slice(bbox["lat_min"], bbox["lat_max"]),
            lon=slice(bbox["lon_min"], bbox["lon_max"]),
        )
        fire_sum = fire_region.sum(dim=["lat", "lon"], skipna=True).item()
        ds_fire.close()

        dates.append(date)
        gas_avg_list.append(gas_avg)
        fire_count_list.append(fire_sum)

    df = pd.DataFrame({"date": dates, f"{gas_variable}_avg": gas_avg_list, "fire_count": fire_count_list})
    df = df.set_index("date").dropna()
    return df


def main():
    results = {}
    for year in STUDY_YEARS:
        fire_dir = VIIRS_GRIDDED_DIR.format(year=year)
        for cluster_id, bbox in CLUSTER_BBOXES_BY_YEAR[year].items():
            for gas, gas_cfg in GAS_CONFIG.items():
                gas_dir = gas_cfg["dir_template"].format(year=year)
                print(f"Extracting {gas} for {year} cluster {cluster_id}...")
                df = extract_cluster_timeseries(
                    gas_dir, gas_cfg["variable"], fire_dir, bbox
                )
                results[(year, cluster_id, gas)] = df

    return results


if __name__ == "__main__":
    main()
