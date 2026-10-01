"""
Fig. 10 - Temporal variability of tropospheric NO2 and total CO column
densities averaged over the Lower and Higher Himalaya zones of Nepal,
one row per year (2021-2024), NO2 and CO side by side.

SOURCE: gridoutburst.py, lines 394-498 (the separate NO2/CO plotting
blocks with unit conversion) built on top of the daily-mean extraction
also at gridoutburst.py lines 266-389 and hiamalayaconc.py. The actual
daily-series computation is shared with
06_himalaya_zone_timeseries.py - this file only adds the paper's
specific plot layout (8 panels: 4 years x {NO2, CO}) with a
January-February baseline reference line, matching Fig. 10's caption.

NOTE: the paper's Fig. 10 panels show a shaded pre-monsoon band and a
dashed Jan-Feb baseline line; the source scripts plot the series but
compute the baseline value inline rather than storing it, so it's
recomputed here as the Jan-Feb mean per year.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Looped over config.STUDY_YEARS into one 4x2 figure instead of
    separate single-year/single-gas plots.
"""

import os
import sys
from importlib import import_module

import matplotlib.pyplot as plt

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS, BASELINE_MONTHS

_himalaya_module = import_module("06_himalaya_zone_timeseries")
himalaya_daily_series = _himalaya_module.himalaya_daily_series
load_mountain_region = _himalaya_module.load_mountain_region


def main():
    mountain_region = load_mountain_region()
    fig, axes = plt.subplots(len(STUDY_YEARS), 2, figsize=(12, 4 * len(STUDY_YEARS)))

    for row, year in enumerate(STUDY_YEARS):
        print(f"Building Fig. 10 panels for {year}...")
        df = himalaya_daily_series(year, mountain_region)
        baseline_mask = df["date"].dt.month.isin(BASELINE_MONTHS)

        ax_no2 = axes[row, 0]
        no2_baseline = df.loc[baseline_mask, "NO2_mmol"].mean()
        ax_no2.plot(df["date"], df["NO2_mmol"], color="green")
        ax_no2.axhline(no2_baseline, color="black", linestyle="--",
                        label=f"Jan-Feb baseline ({no2_baseline:.2f})")
        ax_no2.set_title(f"({year}) Tropospheric NO2")
        ax_no2.legend(fontsize=7)

        ax_co = axes[row, 1]
        co_baseline = df.loc[baseline_mask, "CO_column_number_density"].mean()
        ax_co.plot(df["date"], df["CO_column_number_density"], color="black")
        ax_co.axhline(co_baseline, color="black", linestyle="--",
                       label=f"Jan-Feb baseline ({co_baseline:.2f})")
        ax_co.set_title(f"({year}) Total CO Column")
        ax_co.legend(fontsize=7)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
