"""
Checks whether smoke from the lowland fires is actually reaching the
Himalaya, using the same Metric A/B approach as the Terai clusters, plus
a direct comparison between the two regions.

What it works out:
  1. Jan-Feb baseline and fire-season monthly mean for the Himalaya zone.
  2. Metric A and Metric B for the Himalaya zone, both gases - this is
     the data behind the Himalaya heatmap figure.
  3. Monthly correlation between the Terai clusters' enhancement and the
     Himalaya zone's enhancement.
  4. The same correlation again, but with the shared seasonal cycle
     (month) partialled out, so we're not just picking up "everything is
     higher in April everywhere."
  5. A day-by-day version: average the NO2 anomaly across all three
     Terai clusters, then check if it correlates with the Himalaya's
     same-day NO2 anomaly, both pooled across all years and year by
     year.
"""

import os
import sys
from importlib import import_module

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from numpy.linalg import lstsq

_PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS, PRE_MONSOON_MONTHS, BASELINE_MONTHS, CLUSTER_BBOXES_BY_YEAR

m06 = import_module("06_himalaya_zone_timeseries")
m07 = import_module("07_seasonal_and_episodic_metrics")


def himalaya_baseline_and_metrics(mountain_region):
    """Jan-Feb baseline, then Metric A/B per year/month for the Himalaya
    zone, for both NO2 and CO."""
    baseline_rows, monthly_rows, episodic_rows = [], [], []

    for year in STUDY_YEARS:
        df = m06.himalaya_daily_series(year, mountain_region)
        df["month"] = df["date"].dt.month

        no2_baseline = df.loc[df["month"].isin(BASELINE_MONTHS), "tropospheric_NO2_column_number_density"].mean()
        co_baseline = df.loc[df["month"].isin(BASELINE_MONTHS), "CO_column_number_density"].mean()
        baseline_rows.append({"year": year, "NO2_baseline": no2_baseline, "CO_baseline": co_baseline})

        fire_df = df[df["month"].isin(PRE_MONSOON_MONTHS)]
        for month, group in fire_df.groupby("month"):
            group = group.sort_values("date")
            no2_mean, co_mean = group["tropospheric_NO2_column_number_density"].mean(), group["CO_column_number_density"].mean()
            monthly_rows.append({
                "year": year, "month": month,
                "NO2_enhancement_pct": (no2_mean - no2_baseline) / no2_baseline * 100,
                "CO_enhancement_pct": (co_mean - co_baseline) / co_baseline * 100,
            })

            no2_max, no2_min = group["tropospheric_NO2_column_number_density"].max(), group["tropospheric_NO2_column_number_density"].min()
            co_max, co_min = group["CO_column_number_density"].max(), group["CO_column_number_density"].min()
            episodic_rows.append({
                "year": year, "month": month,
                "NO2_amplitude_pct": (no2_max - no2_min) / no2_min * 100 if no2_min > 0 else np.nan,
                "CO_amplitude_pct": (co_max - co_min) / co_min * 100 if co_min > 0 else np.nan,
            })

    return pd.DataFrame(baseline_rows), pd.DataFrame(monthly_rows), pd.DataFrame(episodic_rows)


def partial_spearman(df, x_col, y_col, control_col):
    """Spearman correlation between x and y after removing the linear
    effect of control_col from both (rank-based partial correlation)."""
    x = rankdata(df[x_col].values).astype(float)
    y = rankdata(df[y_col].values).astype(float)
    z = rankdata(df[control_col].values).astype(float)
    Z = np.column_stack([np.ones(len(z)), z])
    x_res = x - Z @ lstsq(Z, x, rcond=None)[0]
    y_res = y - Z @ lstsq(Z, y, rcond=None)[0]
    return spearmanr(x_res, y_res)


def terai_himalaya_same_day_transport(mountain_region, himalaya_baseline):
    """Daily NO2 anomaly averaged across the 3 Terai clusters vs. daily
    Himalaya NO2 anomaly, same day, pooled across all years."""
    transport_records = []

    for year in STUDY_YEARS:
        cluster_anoms = []
        for cluster_id in sorted(CLUSTER_BBOXES_BY_YEAR[year]):
            daily_df, monthly_df = m07.compute_both_metrics("NO2", year, cluster_id)
            if daily_df.empty or monthly_df.empty:
                continue
            baseline_mean = monthly_df["baseline_mean"].iloc[0]
            fire_daily = daily_df[daily_df["month"].isin(PRE_MONSOON_MONTHS)].copy()
            if len(fire_daily) < 5:
                continue
            fire_daily["date"] = pd.to_datetime(fire_daily["date"]).dt.normalize()
            anom = (fire_daily.set_index("date")["value"] - baseline_mean).rename(f"C{cluster_id}")
            cluster_anoms.append(anom)

        if not cluster_anoms:
            continue
        terai_avg_anom = pd.concat(cluster_anoms, axis=1).mean(axis=1).rename("terai_avg_anom")

        himal_bl = himalaya_baseline.loc[himalaya_baseline["year"] == year, "NO2_baseline"]
        if himal_bl.empty:
            continue
        himal_df = m06.himalaya_daily_series(year, mountain_region)
        himal_df["month"] = himal_df["date"].dt.month
        himal_df = himal_df[himal_df["month"].isin(PRE_MONSOON_MONTHS)].copy()
        himal_df["date"] = pd.to_datetime(himal_df["date"]).dt.normalize()
        himal_anom = (himal_df.set_index("date")["tropospheric_NO2_column_number_density"] - himal_bl.values[0]).rename("himal_anom")

        combined = pd.concat([terai_avg_anom, himal_anom], axis=1).dropna()
        for date, row in combined.iterrows():
            transport_records.append({"date": date, "year": year, "terai_avg_anom": row["terai_avg_anom"], "himal_anom": row["himal_anom"]})

    transport_df = pd.DataFrame(transport_records)
    if transport_df.empty:
        return transport_df, np.nan, np.nan, pd.DataFrame()

    rho_pool, p_pool = spearmanr(transport_df["terai_avg_anom"], transport_df["himal_anom"])

    yr_results = []
    for year in STUDY_YEARS:
        yr_df = transport_df[transport_df["year"] == year]
        if len(yr_df) < 10:
            continue
        rho_yr, p_yr = spearmanr(yr_df["terai_avg_anom"], yr_df["himal_anom"])
        yr_results.append({"year": year, "n": len(yr_df), "rho": rho_yr, "pval": p_yr})

    return transport_df, rho_pool, p_pool, pd.DataFrame(yr_results)


def main():
    mountain_region = m06.load_mountain_region()

    print("Computing Himalaya baseline and Metric A/B...")
    baseline_df, monthly_df, episodic_df = himalaya_baseline_and_metrics(mountain_region)
    print(baseline_df)

    print("\nComputing Terai-Himalaya same-day transport correlation...")
    transport_df, rho_pool, p_pool, yr_results = terai_himalaya_same_day_transport(mountain_region, baseline_df)
    print(f"Pooled Spearman: rho={rho_pool:.3f}, p={p_pool:.4f}, n={len(transport_df)}")
    print(yr_results)

    return {
        "baseline_df": baseline_df, "monthly_df": monthly_df, "episodic_df": episodic_df,
        "transport_df": transport_df, "rho_pool": rho_pool, "p_pool": p_pool, "yr_results": yr_results,
    }


if __name__ == "__main__":
    main()
