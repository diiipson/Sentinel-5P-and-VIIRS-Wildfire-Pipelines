"""
Fig. 11 - Seasonal and Episodic Variability of Tropospheric NO2 and CO
over the Himalayan Zone (2021-2024): 2x2 heatmap grid (rows: Metric
A/Metric B; columns: NO2/CO), years x fire-season months.

SOURCE: C:\\Users\\ACER\\Downloads\\himalaya_analysis_improved.py,
"ORIGINAL PLOT 2" section (found outside this repository - see
EXTRACTION_LOG.md "Gaps, resolved"). This is the only script found
anywhere (inside or outside this repo) that produces this exact figure.

Depends on 09_himalaya_correlation_analysis.py for the monthly_df and
episodic_df inputs (Metric A and B per year/month for the Himalaya
zone).

CHANGED FROM SOURCE (non-functional cleanup only):
  - Takes monthly_df/episodic_df as parameters instead of reading them
    back from CSV files the original script had just written.
"""

import os
import sys

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS

MONTHS = [3, 4, 5]
MONTH_NAMES = ["Mar", "Apr", "May"]


def build_matrix(df, value_col):
    matrix = np.full((len(STUDY_YEARS), len(MONTHS)), np.nan)
    for i, year in enumerate(STUDY_YEARS):
        for j, month in enumerate(MONTHS):
            row = df[(df["year"] == year) & (df["month"] == month)]
            if len(row):
                matrix[i, j] = row[value_col].values[0]
    return matrix


def main(monthly_df, episodic_df):
    matrix_no2_A = build_matrix(monthly_df, "NO2_enhancement_pct")
    matrix_co_A = build_matrix(monthly_df, "CO_enhancement_pct")
    matrix_no2_B = build_matrix(episodic_df, "NO2_amplitude_pct")
    matrix_co_B = build_matrix(episodic_df, "CO_amplitude_pct")

    fig, axes = plt.subplots(2, 2, figsize=(8, 6), facecolor="white",
                              gridspec_kw={"wspace": 0.45, "hspace": 0.55})
    panels = [
        (axes[0, 0], matrix_no2_A, "[A] NO2 Seasonal Enhancement", "RdYlGn", True),
        (axes[0, 1], matrix_co_A, "[A] CO Seasonal Enhancement", "RdYlGn", True),
        (axes[1, 0], matrix_no2_B, "[B] NO2 Episodic Amplitude", "YlOrRd", False),
        (axes[1, 1], matrix_co_B, "[B] CO Episodic Amplitude", "YlOrRd", False),
    ]

    for ax, matrix, title, cmap, diverging in panels:
        if diverging:
            vmax = np.nanmax(np.abs(matrix)) * 1.05
            norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
        else:
            norm = mcolors.Normalize(vmin=0, vmax=np.nanmax(matrix))

        im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
        for i in range(len(STUDY_YEARS)):
            for j in range(len(MONTHS)):
                val = matrix[i, j]
                if not np.isnan(val):
                    rgba = plt.get_cmap(cmap)(norm(val))
                    brightness = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
                    text_color = "white" if brightness < 0.5 else "black"
                    ax.text(j, i, f"{val:+.0f}%" if diverging else f"{val:.0f}%",
                            ha="center", va="center", fontsize=9, fontweight="bold", color=text_color)

        ax.set_xticks(range(len(MONTHS)))
        ax.set_xticklabels(MONTH_NAMES, fontsize=8)
        ax.set_yticks(range(len(STUDY_YEARS)))
        ax.set_yticklabels(STUDY_YEARS, fontsize=8)
        ax.set_title(title, fontsize=8.5, fontweight="bold", pad=8)
        ax.tick_params(length=0)
        for i in range(len(STUDY_YEARS) + 1):
            ax.axhline(i - 0.5, color="white", linewidth=1.2, zorder=3)
        for j in range(len(MONTHS) + 1):
            ax.axvline(j - 0.5, color="white", linewidth=1.2, zorder=3)
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=7)
        cbar.set_label("%", fontsize=7, labelpad=4)

    for row_idx, row_label in enumerate(["Metric A\n(Seasonal)", "Metric B\n(Episodic)"]):
        axes[row_idx, 0].set_ylabel(row_label, fontsize=8, fontweight="bold", labelpad=10, rotation=90)

    plt.show()


if __name__ == "__main__":
    from importlib import import_module

    m09 = import_module("09_himalaya_correlation_analysis")
    results = m09.main()
    main(results["monthly_df"], results["episodic_df"])
