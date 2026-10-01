"""
Fig. 8 - Daily tropospheric NO2 and fire counts for the three largest
wildfire clusters in Nepal (Jan-Jun, 2021-2024): 4 years x 3 cluster
ranks = 12 panels.
Fig. 9 - same layout, for total CO instead of NO2.

SOURCE: FILECHECK.py, lines 7-189. That script hardcoded ONE
cluster/year/gas combination (2024, cluster rank 1, CO - despite
variable names throughout the file saying "NO2") and plotted it as a
single dual-axis time series. The committed sample image
`Picture samples/Figure_8.jpg` is a 12-panel grid built by running this
exact plotting pattern once per (year, cluster) and arranging the
results into a 4x3 grid - that full loop is what this file reconstructs.

Depends on extract_cluster_timeseries() from
04_cluster_trace_gas_timeseries.py.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Looped over all years x cluster ranks into one 4x3 subplot grid
    instead of 12 separate manually-run single plots.
  - Fixed FILECHECK.py's variable-name mismatch (it labeled a CO series
    "NO2_avg" throughout) by using the correct gas name passed in.
"""

import os
import sys
from importlib import import_module

import matplotlib.pyplot as plt

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS, CLUSTER_BBOXES_BY_YEAR, VIIRS_GRIDDED_DIR, TROPOMI_NO2_DIR, TROPOMI_CO_DIR

_cluster_ts_module = import_module("04_cluster_trace_gas_timeseries")
extract_cluster_timeseries = _cluster_ts_module.extract_cluster_timeseries
GAS_CONFIG = _cluster_ts_module.GAS_CONFIG


def plot_gas_vs_fire_grid(gas, limit_months=(1, 2, 3, 4, 5, 6)):
    gas_cfg = GAS_CONFIG[gas]
    fig, axes = plt.subplots(len(STUDY_YEARS), 3, figsize=(15, 4 * len(STUDY_YEARS)))

    for row, year in enumerate(STUDY_YEARS):
        fire_dir = VIIRS_GRIDDED_DIR.format(year=year)
        gas_dir = gas_cfg["dir_template"].format(year=year)

        for col, cluster_id in enumerate(sorted(CLUSTER_BBOXES_BY_YEAR[year])):
            bbox = CLUSTER_BBOXES_BY_YEAR[year][cluster_id]
            df = extract_cluster_timeseries(gas_dir, gas_cfg["variable"], fire_dir, bbox)
            df = df[df.index.month.isin(limit_months)]

            ax1 = axes[row, col]
            ax1.plot(df.index, df[f"{gas_cfg['variable']}_avg"], color="darkgreen", linewidth=1.3)
            ax1.set_ylabel(f"Tropospheric {gas}", color="darkgreen", fontsize=8)
            ax1.tick_params(axis="y", labelcolor="darkgreen", labelsize=7)

            ax2 = ax1.twinx()
            ax2.plot(df.index, df["fire_count"], color="firebrick", linewidth=1.1, alpha=0.7)
            ax2.set_ylabel("Fire Count", color="firebrick", fontsize=8)
            ax2.tick_params(axis="y", labelcolor="firebrick", labelsize=7)

            ax1.set_title(f"{year} - cluster {cluster_id}", fontsize=9)
            ax1.set_xlabel("Month", fontsize=8)
            ax1.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_gas_vs_fire_grid("NO2")  # Fig. 8
    plot_gas_vs_fire_grid("CO")   # Fig. 9
