"""
Fig. 3 - full-domain map of all hotspot clusters (distinct colors per
cluster, cyan bounding boxes on the top 3).
Fig. 4 - zoomed-in per-pixel views of the top 3 clusters, panels (a/b/c).

SOURCE: methodology1.py, lines 390-529 (the "SAME COLOR" section near
the end of the file - the third and final visualization attempt in that
script). This exact code (with its hardcoded output path
`S:\\viirs\\pictures\\Clusters\\2021\\new_cluster{i}.png`) produced the
`Cluster1.png` / `Cluster2.png` images already committed under
`Picture samples/` in this repo.

Earlier attempts in the same file (plain `tab20` coloring without a
fixed BoundaryNorm, at methodology1.py lines ~198-343) are superseded by
this version, which fixes the color-to-cluster-ID mapping so the same
cluster ID always gets the same color across the full map and the
zoomed panels.

Depends on detect_hotspot_clusters() from
03_hotspot_detection_clustering.py for `labeled_da` and `top3`.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Wrapped in functions; year/output path are parameters instead of
    being hand-edited per run.
"""

import os
import sys
from importlib import import_module

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import NEPAL_BOUNDARY_SHP, VIIRS_GRIDDED_DIR

detect_hotspot_clusters = import_module("03_hotspot_detection_clustering").detect_hotspot_clusters


def fig3_full_cluster_map(labeled_da, top3, nepal, out_path=None):
    cluster_values = labeled_da.values
    cluster_ids = np.unique(cluster_values[~np.isnan(cluster_values)])
    all_ids = np.insert(cluster_ids, 0, 0) if 0 not in cluster_ids else cluster_ids

    cmap = plt.get_cmap("tab20", len(all_ids))
    bounds = np.arange(all_ids.min(), all_ids.max() + 2) - 0.5
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.pcolormesh(
        *np.meshgrid(labeled_da.lon.values, labeled_da.lat.values),
        cluster_values, cmap=cmap, norm=norm, edgecolor="black", linewidth=0.2,
    )

    for r in top3:
        ax.plot(
            [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
            [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
            color="cyan", linewidth=2, zorder=10,
        )

    nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.2, zorder=11)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.show()
    return cmap, norm


def fig4_zoomed_cluster_panels(labeled_da, top3, cmap, norm, out_dir=None):
    for i, r in enumerate(top3, start=1):
        zoom = labeled_da.sel(
            lat=slice(r["lat_min"], r["lat_max"]),
            lon=slice(r["lon_min"], r["lon_max"]),
        )
        fig, ax = plt.subplots(figsize=(3.6, 3.6))
        ax.pcolormesh(
            *np.meshgrid(zoom.lon.values, zoom.lat.values),
            zoom.values, cmap=cmap, norm=norm, edgecolor="black", linewidth=0.2,
        )
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        plt.tight_layout()
        if out_dir:
            plt.savefig(f"{out_dir}\\new_cluster{i}.png", dpi=1000, bbox_inches="tight")
        plt.show()


def main(year=2021):
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")
    data_dir = VIIRS_GRIDDED_DIR.format(year=year)
    _, _, labeled_da, top3 = detect_hotspot_clusters(data_dir, nepal)

    cmap, norm = fig3_full_cluster_map(labeled_da, top3, nepal)
    fig4_zoomed_cluster_panels(labeled_da, top3, cmap, norm, out_dir=rf"S:\viirs\pictures\Clusters\{year}")


if __name__ == "__main__":
    main()
