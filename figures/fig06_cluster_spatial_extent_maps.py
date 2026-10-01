"""
Fig. 6 - Spatial extent of the three largest contiguous wildfire hotspot
clusters across Nepal for each year, 2021-2024 (4 panels).

SOURCE: methodology2.py, lines 145-170 (hotspot + annual-fire-count
background map with cyan bounding boxes around the top 3 clusters).
Same underlying detection as Figs. 3/4 (see
03_hotspot_detection_clustering.py) but shown as one subplot per year
rather than a single-year full map + zoomed panels.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Wrapped in a loop over config.STUDY_YEARS producing a 2x2 figure,
    instead of one standalone plot per manually-edited run.
"""

import os
import sys
from importlib import import_module

import matplotlib.pyplot as plt
import geopandas as gpd

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import NEPAL_BOUNDARY_SHP, VIIRS_GRIDDED_DIR, STUDY_YEARS

detect_hotspot_clusters = import_module("03_hotspot_detection_clustering").detect_hotspot_clusters


def plot_year_panel(ax, year, nepal):
    data_dir = VIIRS_GRIDDED_DIR.format(year=year)
    fire_annual, hotspot, labeled_da, top3 = detect_hotspot_clusters(data_dir, nepal)

    fire_annual.plot(ax=ax, cmap="Greys", alpha=0.6, add_colorbar=False)
    hotspot.plot(ax=ax, cmap="Reds", alpha=0.6, add_colorbar=False)
    nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.2)

    for rank, r in enumerate(top3, start=1):
        ax.plot(
            [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
            [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
            color="cyan", linewidth=2,
        )
        ax.text(
            (r["lon_min"] + r["lon_max"]) / 2,
            (r["lat_min"] + r["lat_max"]) / 2,
            str(rank), color="black", fontsize=9, ha="center", va="center",
        )

    ax.set_title(str(year))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")


def main():
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))

    for ax, year in zip(axes.flatten(), STUDY_YEARS):
        print(f"Plotting {year}...")
        plot_year_panel(ax, year, nepal)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
