"""
Computes both metrics used in the paper, for whichever gas you ask for:

  Metric A - how much higher NO2/CO is during a fire-season month
             compared to the quiet Jan-Feb baseline
  Metric B - how big the swing is between the highest and lowest day
             within that same month (captures the short, sharp spikes)

For each cluster and year, it reads the daily gas values on their own
(not tied to the fire data), figures out the Jan-Feb average as a
baseline, then works out both metrics for March, April, and May.

(An earlier version of this file only computed Metric B - removed once
this one covered everything it did and more.)
"""

import glob
import os

import numpy as np
import pandas as pd
import xarray as xr

from config import STUDY_YEARS, CLUSTER_BBOXES_BY_YEAR, TROPOMI_NO2_DIR, TROPOMI_CO_DIR, PRE_MONSOON_MONTHS, BASELINE_MONTHS

ALL_MONTHS = [1, 2, 3, 4, 5, 6]

GAS_CONFIG = {
    "NO2": {"dir_template": TROPOMI_NO2_DIR, "variable": "tropospheric_NO2_column_number_density", "unit": "umol m-2"},
    "CO": {"dir_template": TROPOMI_CO_DIR, "variable": "CO_column_number_density", "unit": "mmol m-2"},
}


def extract_daily_gas(gas_dir, gas_variable, bbox):
    """Independent daily mean extraction for one cluster bbox - does NOT
    assume gas files are date-aligned with any other file list."""
    files = sorted(glob.glob(os.path.join(gas_dir, "*.nc")))
    records = []
    for f in files:
        try:
            ds = xr.open_dataset(f)
            date = pd.to_datetime(ds["datetime_start"].values[0])
            val = ds[gas_variable].sel(
                latitude=slice(bbox["lat_min"], bbox["lat_max"]),
                longitude=slice(bbox["lon_min"], bbox["lon_max"]),
            ).mean(dim=["latitude", "longitude"], skipna=True).item()
            ds.close()
        except Exception:
            continue
        if date.month not in ALL_MONTHS or np.isnan(val):
            continue
        records.append({"date": date, "month": date.month, "value": val})
    return pd.DataFrame(records)


def compute_both_metrics(gas, year, cluster_id):
    """Returns (daily_df, monthly_df) for one gas/year/cluster, where
    monthly_df has one row per fire-season month with Metric A and B."""
    gas_cfg = GAS_CONFIG[gas]
    bbox = CLUSTER_BBOXES_BY_YEAR[year][cluster_id]
    gas_dir = gas_cfg["dir_template"].format(year=year)

    daily_df = extract_daily_gas(gas_dir, gas_cfg["variable"], bbox)
    if daily_df.empty:
        return daily_df, pd.DataFrame()

    baseline_mean = daily_df.loc[daily_df["month"].isin(BASELINE_MONTHS), "value"].mean()

    monthly_rows = []
    fire_df = daily_df[daily_df["month"].isin(PRE_MONSOON_MONTHS)]
    for month, group in fire_df.groupby("month"):
        group = group.sort_values("date")
        daily_max, daily_min = group["value"].max(), group["value"].min()
        amplitude_pct = (daily_max - daily_min) / daily_min * 100 if daily_min > 0 else np.nan
        seasonal_enhancement_pct = (group["value"].mean() - baseline_mean) / baseline_mean * 100

        monthly_rows.append({
            "year": year, "cluster": cluster_id, "month": month,
            "monthly_mean": group["value"].mean(),
            "monthly_se": group["value"].std() / np.sqrt(len(group)) if len(group) > 1 else np.nan,
            "baseline_mean": baseline_mean,
            "daily_max": daily_max, "daily_min": daily_min,
            "date_of_max": group.loc[group["value"].idxmax(), "date"],
            "seasonal_enhancement_pct": seasonal_enhancement_pct,  # Metric A
            "intra_monthly_amplitude_pct": amplitude_pct,          # Metric B
        })

    return daily_df, pd.DataFrame(monthly_rows)


def main(gas="NO2"):
    all_daily, all_monthly = {}, []
    for year in STUDY_YEARS:
        for cluster_id in sorted(CLUSTER_BBOXES_BY_YEAR[year]):
            print(f"Computing {gas} metrics for {year} cluster {cluster_id}...")
            daily_df, monthly_df = compute_both_metrics(gas, year, cluster_id)
            all_daily[(year, cluster_id)] = daily_df
            if not monthly_df.empty:
                all_monthly.append(monthly_df)

    monthly_all = pd.concat(all_monthly, ignore_index=True) if all_monthly else pd.DataFrame()
    return all_daily, monthly_all


if __name__ == "__main__":
    daily, monthly = main("NO2")
    print(monthly)
