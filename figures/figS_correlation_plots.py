"""
Supplementary figures S2-S7 (correlation scatter/bar plots referenced in
the paper's Results section 3.3-3.5 but not given their own main-text
figure number):
  - Fig. S2/S4: scatter of monthly fire count vs. Metric A, + bar chart
    of mean lagged daily correlation (0-3 days).
  - Fig. S3/S5: per-year, per-lag scatter of daily fire count vs. gas
    column density.
  - Fig. S6: scatter of averaged Terai NO2 anomaly vs. Himalaya NO2
    anomaly, same day, colored by year.
  - Fig. S7: year-by-year bar chart of the Terai-Himalaya transport
    Spearman rho.

SOURCE: C:\\Users\\ACER\\Downloads\\no2_stat_both_metrics.py sections
11-14, C:\\Users\\ACER\\Downloads\\co_stat_both_metrics.py sections
11-14 (same plots, CO instead of NO2), and
C:\\Users\\ACER\\Downloads\\himalaya_analysis_improved.py "NEW PLOT 2"
and "NEW PLOT 3" sections (all found outside this repository - see
EXTRACTION_LOG.md "Gaps, resolved"). Each function below corresponds to
one of those sections, consolidated into one file instead of being
duplicated per gas.

NOT INCLUDED: "NEW PLOT 1" (partial Spearman bar chart comparing raw vs
partial correlation) is implemented in
09_himalaya_correlation_analysis.py's `partial_spearman()` function but
not plotted here - add a simple bar chart if you need that exact figure
reproduced; the numbers themselves are already computed.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Each plot takes its data as parameters instead of relying on module-
    level variables left over from a top-to-bottom notebook-style script.
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import STUDY_YEARS

YEAR_COLORS = {2021: "#e41a1c", 2022: "#377eb8", 2023: "#4daf4a", 2024: "#984ea3"}
CLUSTER_MARKERS = {1: "o", 2: "s", 3: "^"}


def sig_stars(p):
    if p < 0.001:
        return "p < 0.001"
    if p < 0.01:
        return "p < 0.01"
    if p < 0.05:
        return "p < 0.05"
    return "p >= 0.05 (ns)"


def fig_s2_s4_fire_vs_metric_a(corr_df, rho_A, p_A, gas_label="NO2"):
    """Fig. S2 (NO2) / S4 (CO) left panel: scatter of monthly fire count
    total vs. Metric A, colored by year, marker by cluster."""
    fig, ax = plt.subplots(figsize=(6, 5))
    for _, row in corr_df.iterrows():
        ax.scatter(
            row["fire_count_total"], row["seasonal_enhancement_pct"],
            color=YEAR_COLORS.get(int(row["year"]), "gray"),
            marker=CLUSTER_MARKERS.get(int(row["cluster"]), "o"),
            s=45, edgecolors="k", linewidths=0.4, zorder=3,
        )
    x, y = corr_df["fire_count_total"].values, corr_df["seasonal_enhancement_pct"].values
    m, b = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, m * x_line + b, "k--", linewidth=1, alpha=0.6)
    ax.set_xlabel("Monthly Fire Count Total")
    ax.set_ylabel(f"Seasonal Enhancement % ({gas_label}, Metric A)")
    ax.set_title(f"Fire vs Metric A\nrho = {rho_A:.3f}  {sig_stars(p_A)}")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.show()


def fig_s2_s4_lag_bar(lag_summary, gas_label="NO2"):
    """Fig. S2 (NO2) / S4 (CO) right panel: mean lagged daily
    correlation bar chart, lags 0-3 days."""
    fig, ax = plt.subplots(figsize=(5, 4.5))
    lags = [0, 1, 2, 3]
    rhos = [lag_summary.loc[lag_summary["lag"] == l, "mean_rho"].values[0] if l in lag_summary["lag"].values else 0.0 for l in lags]
    ax.bar(np.arange(len(lags)), rhos, color="steelblue", alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(np.arange(len(lags)))
    ax.set_xticklabels([f"Lag {l}d" for l in lags])
    ax.set_ylabel("Mean Spearman rho")
    ax.set_title(f"Lagged Daily Correlations ({gas_label} Anomaly)")
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.show()


def fig_s3_s5_lagged_scatter_by_year(daily_by_cluster_year, fire_daily_df, gas_label="NO2", lags_to_show=(0, 1, 2)):
    """Fig. S3 (NO2) / S5 (CO): 4 rows (years) x 3 cols (lags 0/1/2),
    daily fire count vs. gas column density, colored by cluster."""
    fig, axes = plt.subplots(len(STUDY_YEARS), len(lags_to_show), figsize=(13, 3.5 * len(STUDY_YEARS)))
    cluster_colors = {1: "#e41a1c", 2: "#377eb8", 3: "#4daf4a"}

    for row, year in enumerate(STUDY_YEARS):
        for col, lag in enumerate(lags_to_show):
            ax = axes[row, col]
            all_fc, all_gas = [], []

            for (y, cluster_id), gas_daily in daily_by_cluster_year.items():
                if y != year or gas_daily.empty:
                    continue
                gas_sub = gas_daily.set_index("date")["value"].sort_index()
                fc_sub = fire_daily_df[
                    (fire_daily_df["year"] == year) & (fire_daily_df["cluster"] == cluster_id)
                ].set_index("date")["fire_count_daily"].sort_index()
                common = fc_sub.index.intersection(gas_sub.index)
                if len(common) < 5:
                    continue
                if lag == 0:
                    fc_vals, gas_vals = fc_sub.loc[common].values, gas_sub.loc[common].values
                else:
                    fc_vals, gas_vals = fc_sub.loc[common].values[:-lag], gas_sub.loc[common].values[lag:]
                ax.scatter(fc_vals, gas_vals, color=cluster_colors.get(cluster_id, "gray"), s=18, alpha=0.65, label=f"C{cluster_id}")
                all_fc.extend(fc_vals)
                all_gas.extend(gas_vals)

            if len(all_fc) >= 6:
                all_fc, all_gas = np.array(all_fc), np.array(all_gas)
                rho_yr, p_yr = stats.spearmanr(all_fc, all_gas)
                m_yr, b_yr = np.polyfit(all_fc, all_gas, 1)
                x_line = np.linspace(all_fc.min(), all_fc.max(), 200)
                ax.plot(x_line, m_yr * x_line + b_yr, "k--", linewidth=1.2, alpha=0.7)
                ax.annotate(f"rho = {rho_yr:.3f}  {sig_stars(p_yr)}", xy=(0.97, 0.04), xycoords="axes fraction", ha="right", va="bottom", fontsize=7.5)

            ax.set_title(f"{year} - lag {lag}d")
            ax.set_xlabel("Daily Fire Count")
            ax.set_ylabel(f"{gas_label} Column")
            if row == 0 and col == 0:
                ax.legend(fontsize=7)

    plt.tight_layout()
    plt.show()


def fig_s6_terai_himalaya_scatter(transport_df, rho_pool, p_pool):
    """Fig. S6: averaged Terai NO2 anomaly vs. Himalaya NO2 anomaly,
    same day, all years pooled, colored by year."""
    fig, ax = plt.subplots(figsize=(7, 6))
    for year in STUDY_YEARS:
        yr_df = transport_df[transport_df["year"] == year]
        if yr_df.empty:
            continue
        ax.scatter(yr_df["terai_avg_anom"], yr_df["himal_anom"], color=YEAR_COLORS[year], alpha=0.35, s=18, label=str(year))

    x_all, y_all = transport_df["terai_avg_anom"].values, transport_df["himal_anom"].values
    mask = ~np.isnan(x_all) & ~np.isnan(y_all)
    m, b = np.polyfit(x_all[mask], y_all[mask], 1)
    x_line = np.linspace(x_all[mask].min(), x_all[mask].max(), 200)
    ax.plot(x_line, m * x_line + b, color="black", linewidth=1.5, linestyle="--", alpha=0.7)

    ax.axhline(0, color="lightgray", linewidth=0.8, linestyle=":")
    ax.axvline(0, color="lightgray", linewidth=0.8, linestyle=":")
    ax.text(0.05, 0.95, f"Spearman rho = {rho_pool:.3f}\np = {p_pool:.4f}\nn = {len(transport_df)}",
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.85))
    ax.legend(title="Year", fontsize=8)
    ax.set_xlabel("Averaged Terai NO2 Anomaly of 3 clusters (umol m-2)")
    ax.set_ylabel("Himalayan Zone NO2 Anomaly (umol m-2)")
    ax.grid(alpha=0.15)
    plt.tight_layout()
    plt.show()


def fig_s7_yearly_transport_rho_bar(yr_results, rho_pool):
    """Fig. S7: year-by-year Spearman rho for the Terai-Himalaya
    transport correlation, with the pooled rho as a reference line."""
    fig, ax = plt.subplots(figsize=(6, 5))
    bar_cols = [YEAR_COLORS[y] for y in yr_results["year"]]
    bars = ax.bar(yr_results["year"].astype(str), yr_results["rho"], color=bar_cols, alpha=0.8, width=0.5)
    for bar, row in zip(bars, yr_results.itertuples()):
        sig_star = "*" if row.pval < 0.05 else ""
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.008, f"rho={row.rho:.3f}{sig_star}", ha="center", va="bottom", fontsize=8)
    ax.axhline(rho_pool, color="black", linewidth=1.2, linestyle="--", label=f"Pooled rho = {rho_pool:.3f}")
    ax.set_ylabel("Spearman rho")
    ax.set_xlabel("Year")
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.show()
