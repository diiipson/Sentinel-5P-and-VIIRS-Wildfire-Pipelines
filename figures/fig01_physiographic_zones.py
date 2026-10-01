"""
Fig. 1 - Physiographic zones of Nepal (Terai, Siwalik, Hill, Lesser
Himalaya, Higher Himalaya).

SOURCE: gridoutburst.py, lines 604-773 (the second, final "combine"
block - reprojects to Web Mercator, adds a proper legend and lat/lon
tick labels). An earlier, simpler draft of the same plot is at
gridoutburst.py lines 548-563 (just `gdf.plot(column='DESCRIPTIO', ...)`
with no custom colors/legend) - superseded by this version.

CHANGED FROM SOURCE: none functionally; only path/constant imports from
config.py and removal of an accidental duplicate copy of this entire
block that appeared twice in a row in the original file.
"""

import os
import sys

import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import pyproj
from shapely.geometry import box
from matplotlib.patches import Patch

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import PHYSIOGRAPHIC_ZONES_URL, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX

ZONE_MAPPING = {
    "High Mountain": "Higher Himalaya",
    "Middle Mountain": "Lesser Himalaya",
    "Hill": "Hill",
    "Siwalik": "Siwalik",
    "Tarai": "Terai",
}

ZONE_COLORS = {
    "Higher Himalaya": "#8B4513",
    "Lesser Himalaya": "#228B22",
    "Hill": "#7CFC00",
    "Siwalik": "#FFD700",
    "Terai": "#F0E68C",
}


def main():
    gdf = gpd.read_file(PHYSIOGRAPHIC_ZONES_URL)
    gdf["Zone_Label"] = gdf["DESCRIPTIO"].map(ZONE_MAPPING)
    gdf["color"] = gdf["Zone_Label"].map(ZONE_COLORS)

    gdf = gdf.to_crs(epsg=3857)
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    minx_m, miny_m = project.transform(LON_MIN, LAT_MIN)
    maxx_m, maxy_m = project.transform(LON_MAX, LAT_MAX)
    bbox = box(minx_m, miny_m, maxx_m, maxy_m)
    gdf = gdf[gdf.intersects(bbox)]

    fig, ax = plt.subplots(figsize=(7, 8))
    gdf.plot(color=gdf["color"], edgecolor="black", linewidth=0.8, alpha=0.7, ax=ax)
    gdf.dissolve().boundary.plot(ax=ax, color="black", linewidth=1.5)

    legend_elements = [
        Patch(facecolor=color, edgecolor="black", label=label)
        for label, color in ZONE_COLORS.items()
    ]
    ax.legend(handles=legend_elements, title="Physiographic Zones")

    lon_ticks = np.arange(int(LON_MIN), int(LON_MAX) + 1, 1)
    lat_ticks = np.arange(int(LAT_MIN), int(LAT_MAX) + 1, 1)
    xticks = [project.transform(lon, LAT_MIN)[0] for lon in lon_ticks]
    yticks = [project.transform(LON_MIN, lat)[1] for lat in lat_ticks]
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.set_xticklabels([f"{lon}°E" for lon in lon_ticks])
    ax.set_yticklabels([f"{lat}°N" for lat in lat_ticks])

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()
    plt.savefig(r"S:\viirs\pictures\aoi\nepal_physio_zones_corrected.png", dpi=300)
    plt.show()


if __name__ == "__main__":
    main()
