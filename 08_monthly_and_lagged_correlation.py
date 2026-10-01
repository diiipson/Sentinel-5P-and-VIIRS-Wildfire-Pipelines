"""
This is where the actual fire-vs-gas correlation numbers come from -
the ones that show fire activity really is driving the NO2/CO spikes,
not just coinciding with them.

Three checks, in order:
  1. Monthly: does a cluster's total fire count for the month correlate
     with how much its NO2/CO went up that month (Metric A) and how
     spiky it got (Metric B)? Uses Spearman correlation since fire
     counts are heavily skewed (lots of quiet days, occasional huge
     spikes).
  2. Lagged daily (raw): same idea but day by day - does fire on day X
     line up with gas levels on day X, X+1, X+2, X+3? Checks whether the
     smoke takes a day or two to show up at the satellite overpass time.
  3. Lagged daily (anomaly): same as above, but using the gas anomaly
     (value minus its Jan-Feb baseline) instead of the raw value.

One thing worth flagging: steps 2 and 3 come out identical. That's not
a bug - subtracting a constant baseline from a cluster-year's values
doesn't change how they rank against each other, and Spearman
correlation only cares about rank order. So baseline-subtracting before
a per-group Spearman correlation can never change the result.
"""

import glob
import os

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

from config import STUDY_YEARS, PRE_MONSOON_MONTHS, VIIRS_GRIDDED_DIR, CLUSTER_BBOXES_BY_YEAR

import importlib
m07 = importlib.import_module("07_seasonal_and_episodic_metrics")


def extract_daily_fire_counts():
    """Daily fire count per (year, cluster), fire-season months only."""
    records = []
    for year in STUDY_YEARS:
        fire_dir = VIIRS_GRIDDED_DIR.format(year=year)
        fire_files = sorted(glob.glob(os.path.join(fire_dir, "*.nc")))
        for cluster_id, bbox in CLUSTER_BBOXES_BY_YEAR[year].items():
            for f in fire_files:
                try:
                    ds = xr.open_dataset(f)
                    date = pd.to_datetime(ds["time"].values[0])
                    if date.month not in PRE_MONSOON_MONTHS:
                        ds.close()
                        continue
                    fc = ds["fire_count"].sel(
                        lat=slice(bbox["lat_min"], bbox["lat_max"]),
                        lon=slice(bbox["lon_min"], bbox["lon_max"]),
                    )
                    daily_total = fc.sum(skipna=True).item()
                    ds.close()
                except Exception:
                    continue
                records.append({
                    "date": pd.Timestamp(date).normalize(), "year": year,
                    "month": date.month, "cluster": cluster_id,
                    "fire_count_daily": daily_total,
                })
    return pd.DataFrame(records).sort_values(["year", "cluster", "date"]).reset_index(drop=True)


def monthly_spearman(monthly_df, fire_daily_df):
    """9a: fire count vs Metric A and Metric B, pooled across all
    cluster-year-month combinations."""
    fire_monthly = (
        fire_daily_df.groupby(["year", "cluster", "month"])["fire_count_daily"]
        .sum().reset_index().rename(columns={"fire_count_daily": "fire_count_total"})
    )
    corr_df = monthly_df.merge(fire_monthly, on=["year", "cluster", "month"])
    if len(corr_df) < 6:
        return np.nan, np.nan, np.nan, np.nan, corr_df

    rho_A, p_A = stats.spearmanr(corr_df["fire_count_total"], corr_df["seasonal_enhancement_pct"])
    rho_B, p_B = stats.spearmanr(corr_df["fire_count_total"], corr_df["intra_monthly_amplitude_pct"])
    return rho_A, p_A, rho_B, p_B, corr_df


def lagged_daily_spearman(daily_by_cluster_year, fire_daily_df, baseline_by_cluster_year=None, max_lag=3):
    """9b (baseline_by_cluster_year=None, raw gas value) or 9c
    (baseline_by_cluster_year given, gas anomaly) lagged daily Spearman.
    `daily_by_cluster_year`: {(year, cluster): daily_df from 07.extract_daily_gas}."""
    lag_results = []

    for (year, cluster_id), gas_daily in daily_by_cluster_year.items():
        if gas_daily.empty:
            continue
        gas_daily = gas_daily[gas_daily["month"].isin(PRE_MONSOON_MONTHS)].copy()
        gas_daily["date"] = pd.to_datetime(gas_daily["date"]).dt.normalize()

        value_col = "value"
        if baseline_by_cluster_year is not None:
            baseline_mean = baseline_by_cluster_year.get((year, cluster_id), np.nan)
            gas_daily["anomaly"] = gas_daily["value"] - baseline_mean
            value_col = "anomaly"

        gas_sub = gas_daily.set_index("date")[value_col].sort_index()

        fc_sub = fire_daily_df[
            (fire_daily_df["year"] == year) & (fire_daily_df["cluster"] == cluster_id)
        ].set_index("date")["fire_count_daily"].sort_index()

        if len(fc_sub) < 10 or len(gas_sub) < 10:
            continue
        common = fc_sub.index.intersection(gas_sub.index)
        if len(common) < 10:
            continue

        fc_aligned, gas_aligned = fc_sub.loc[common], gas_sub.loc[common]

        rho_0, p_0 = stats.spearmanr(fc_aligned, gas_aligned)
        lag_results.append({"cluster": cluster_id, "year": year, "lag": 0, "rho": rho_0, "pval": p_0})

        for lag in range(1, max_lag + 1):
            fc_lag, gas_lag = fc_aligned.values[:-lag], gas_aligned.values[lag:]
            if len(fc_lag) < 10:
                continue
            rho_lag, p_lag = stats.spearmanr(fc_lag, gas_lag)
            lag_results.append({"cluster": cluster_id, "year": year, "lag": lag, "rho": rho_lag, "pval": p_lag})

    lag_df = pd.DataFrame(lag_results)
    if lag_df.empty:
        return lag_df, pd.DataFrame()

    lag_summary = (
        lag_df.groupby("lag").agg(mean_rho=("rho", "mean"), mean_p=("pval", "mean"), n=("rho", "count")).reset_index()
    )
    return lag_df, lag_summary


def main(gas="NO2"):
    daily_by_cluster_year, monthly_list, baseline_by_cluster_year = {}, [], {}

    for year in STUDY_YEARS:
        for cluster_id in sorted(CLUSTER_BBOXES_BY_YEAR[year]):
            print(f"Extracting {gas} for {year} cluster {cluster_id}...")
            daily_df, monthly_df = m07.compute_both_metrics(gas, year, cluster_id)
            daily_by_cluster_year[(year, cluster_id)] = daily_df
            if not daily_df.empty:
                baseline_by_cluster_year[(year, cluster_id)] = monthly_df["baseline_mean"].iloc[0] if not monthly_df.empty else np.nan
            if not monthly_df.empty:
                monthly_list.append(monthly_df)

    monthly_df_all = pd.concat(monthly_list, ignore_index=True)
    fire_daily_df = extract_daily_fire_counts()

    rho_A, p_A, rho_B, p_B, corr_df = monthly_spearman(monthly_df_all, fire_daily_df)
    print(f"\n9a. Monthly Spearman ({gas}): fire vs Metric A: rho={rho_A:.3f}, p={p_A:.4f}")
    print(f"                        fire vs Metric B: rho={rho_B:.3f}, p={p_B:.4f}")

    lag_df_raw, lag_summary_raw = lagged_daily_spearman(daily_by_cluster_year, fire_daily_df)
    print(f"\n9b. Lagged daily Spearman ({gas}, raw value):")
    print(lag_summary_raw)

    lag_df_anom, lag_summary_anom = lagged_daily_spearman(daily_by_cluster_year, fire_daily_df, baseline_by_cluster_year)
    print(f"\n9c. Lagged daily Spearman ({gas}, anomaly / Metric B proxy):")
    print(lag_summary_anom)

    return {
        "monthly_df": monthly_df_all, "rho_A": rho_A, "p_A": p_A, "rho_B": rho_B, "p_B": p_B,
        "lag_summary_raw": lag_summary_raw, "lag_summary_anom": lag_summary_anom,
    }


if __name__ == "__main__":
    main("NO2")
