"""
Fig. 7 - District map of Nepal showing districts at risk based on the
number of times each one appeared in the Top-3 wildfire hotspot
footprint during 2021-2024.

SOURCE: nepalshape.py, lines 116-218 (the final version, with a
horizontal colorbar and district-name annotations; an earlier vertical-
colorbar draft at lines 49-114 is superseded by this one).

The underlying "how many years did district X appear in a top-3
cluster" table is NOT computed automatically anywhere in the 27
scripts - it was manually compiled (presumably by reading off the
district names visible in each year's PROVINCEAREA.py-style cluster
map, see 03_hotspot_detection_clustering.py and the districts/area
printout) into the `DISTRICT_HOTSPOT_PERSISTENCE` dict, now in
config.py. See EXTRACTION_LOG.md.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Persistence table and shapefile path now come from config.py.
"""

import os
import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import NEPAL_DISTRICTS_SHP, DISTRICT_HOTSPOT_PERSISTENCE


def main():
    nepal_gdf = gpd.read_file(NEPAL_DISTRICTS_SHP)
    persistence_df = pd.DataFrame(DISTRICT_HOTSPOT_PERSISTENCE)

    nepal_gdf["DISTRICT_clean"] = nepal_gdf["DISTRICT"].str.strip().str.upper()
    persistence_df["District_clean"] = persistence_df["District"].str.strip().str.upper()

    merged_gdf = nepal_gdf.merge(
        persistence_df[["District_clean", "Years_Present"]],
        left_on="DISTRICT_clean", right_on="District_clean", how="left",
    )
    merged_gdf["Years_Present"] = merged_gdf["Years_Present"].fillna(0).astype(int)

    colors_list = ["#d9d9d9", "#ffffb2", "#fecc5c", "#fd8d3c", "#e31a1c"]
    cmap = mcolors.ListedColormap(colors_list)
    norm = mcolors.BoundaryNorm([0, 1, 2, 3, 4, 5], cmap.N)

    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    merged_gdf.plot(
        column="Years_Present", cmap=cmap, norm=norm,
        linewidth=0.7, edgecolor="0.3", legend=True,
        legend_kwds={
            "label": "Times District Appeared in Top-3 Wildfire Hotspots (2021-2024)",
            "orientation": "horizontal", "shrink": 0.3, "aspect": 45, "pad": 0.04,
        },
        ax=ax,
    )

    for _, row in merged_gdf.iterrows():
        if row["Years_Present"] > 0:
            centroid = row["geometry"].centroid
            ax.text(
                centroid.x, centroid.y, row["DISTRICT"].title(),
                ha="center", va="center", fontsize=5.5, fontweight="semibold", color="black",
            )

    ax.axis("off")
    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.08)
    fig.savefig(r"S:\viirs\pictures\District\NEWMAP.png", dpi=1000, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
