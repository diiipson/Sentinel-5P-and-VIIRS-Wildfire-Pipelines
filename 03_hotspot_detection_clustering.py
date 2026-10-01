"""
Finds the wildfire hotspots and groups them into clusters.

For each year, this aggregates fire count and FRP over the fire season,
flags any grid cell that's in the top 10% for either one as a hotspot,
then groups neighboring hotspot cells together using connected-component
labeling (basically: if two hotspot cells touch, they're the same
cluster). The three biggest clusters each year are what get reported.

Also works out each cluster's area in km^2, using two different
approaches:
  - `compute_cluster_area_km2_bbox`: just treats the cluster as its
    rectangular lat/lon bounding box and converts that to km^2.
  - `compute_cluster_area_km2_per_pixel`: adds up the actual area of
    only the hotspot cells themselves, ignoring the empty space inside
    the bounding box. More accurate, and - this is worth knowing - it's
    the one that actually matches the areas reported in the paper
    (2,232 km^2 for the 2021 cluster 1, etc.). The simpler bounding-box
    version gives a very different number, so don't mix the two up if
    you're trying to reproduce the paper's numbers.

Runs once per year instead of being hand-edited and re-run each time.
"""

import glob
import os

import numpy as np
import pandas as pd
import rioxarray  # noqa: F401 - registers the .rio accessor
import xarray as xr
import geopandas as gpd
from scipy.ndimage import label

from config import (
    STUDY_YEARS, PRE_MONSOON_MONTHS, HOTSPOT_PERCENTILE, EARTH_RADIUS_KM,
    VIIRS_GRIDDED_DIR, NEPAL_BOUNDARY_SHP,
)

STRUCTURE_4_CONNECTED = np.array([[0, 1, 0],
                                   [1, 1, 1],
                                   [0, 1, 0]])


def detect_hotspot_clusters(data_dir, nepal):
    """Returns (fire_annual, hotspot, labeled_da, top3) for one year."""
    files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
    if not files:
        raise FileNotFoundError(f"No NetCDF files found in {data_dir}")

    fire_annual = frp_annual = nepal_mask = None

    for f in files:
        ds = xr.open_dataset(f)
        fire = ds["fire_count"].astype("float32")
        frp = ds["frp_sum"].astype("float32")
        date = pd.to_datetime(ds["time"].values[0])

        if date.month in PRE_MONSOON_MONTHS:
            fire = fire.rio.write_crs("EPSG:4326")
            frp = frp.rio.write_crs("EPSG:4326")

            if nepal_mask is None:
                tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
                nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

            fire_clip = fire.where(nepal_mask == 1)
            frp_clip = frp.where(nepal_mask == 1)

            if fire_annual is None:
                fire_annual, frp_annual = fire_clip.copy(), frp_clip.copy()
            else:
                fire_annual += fire_clip
                frp_annual += frp_clip
        ds.close()

    # a cell counts as a hotspot if it's in the top 10% for fire count
    # OR for FRP (within Nepal only)
    fire_thresh = fire_annual.where(nepal_mask == 1).quantile(HOTSPOT_PERCENTILE).item()
    frp_thresh = frp_annual.where(nepal_mask == 1).quantile(HOTSPOT_PERCENTILE).item()
    hotspot = ((fire_annual >= fire_thresh) | (frp_annual >= frp_thresh)) & (nepal_mask == 1)

    # group touching hotspot cells into clusters
    binary = hotspot.fillna(0).astype(int)
    labeled, n_clusters = label(binary.values, structure=STRUCTURE_4_CONNECTED)
    labeled_da = xr.DataArray(
        labeled, coords=hotspot.coords, dims=hotspot.dims, name="hotspot_clusters"
    ).where(nepal_mask == 1)

    regions = []
    for cid in range(1, n_clusters + 1):
        mask = labeled == cid
        if mask.sum() == 0:
            continue
        lat_idx, lon_idx = np.where(mask)
        regions.append({
            "cluster": cid,
            "size": int(mask.sum()),
            "lat_min": float(hotspot.lat.values[lat_idx].min()),
            "lat_max": float(hotspot.lat.values[lat_idx].max()),
            "lon_min": float(hotspot.lon.values[lon_idx].min()),
            "lon_max": float(hotspot.lon.values[lon_idx].max()),
        })

    regions = sorted(regions, key=lambda x: x["size"], reverse=True)
    top3 = regions[:3]
    return fire_annual, hotspot, labeled_da, top3


def compute_cluster_area_km2_bbox(cluster):
    """Treats the cluster as a rectangle (its lat/lon bounding box) and
    works out that rectangle's area on a sphere."""
    lat_min_rad = np.deg2rad(cluster["lat_min"])
    lat_max_rad = np.deg2rad(cluster["lat_max"])
    lon_min_rad = np.deg2rad(cluster["lon_min"])
    lon_max_rad = np.deg2rad(cluster["lon_max"])
    return (
        EARTH_RADIUS_KM ** 2
        * (lon_max_rad - lon_min_rad)
        * (np.sin(lat_max_rad) - np.sin(lat_min_rad))
    )


def compute_cluster_area_km2_per_pixel(labeled_da, cluster):
    """Adds up the real area of just the hotspot cells in this cluster,
    skipping any empty cells inside the bounding box. More accurate than
    the bbox version above, and the one that matches the paper's
    published area numbers."""
    cluster_id = cluster["cluster"]
    zoom = labeled_da.sel(
        lat=slice(cluster["lat_min"], cluster["lat_max"]),
        lon=slice(cluster["lon_min"], cluster["lon_max"]),
    )
    mask = zoom.values == cluster_id
    lat, lon = zoom.lat.values, zoom.lon.values

    lat_edges = np.zeros(len(lat) + 1)
    lon_edges = np.zeros(len(lon) + 1)
    lat_edges[1:-1] = (lat[:-1] + lat[1:]) / 2
    lat_edges[0] = lat[0] - (lat[1] - lat[0]) / 2
    lat_edges[-1] = lat[-1] + (lat[-1] - lat[-2]) / 2
    lon_edges[1:-1] = (lon[:-1] + lon[1:]) / 2
    lon_edges[0] = lon[0] - (lon[1] - lon[0]) / 2
    lon_edges[-1] = lon[-1] + (lon[-1] - lon[-2]) / 2

    lat_edges_rad = np.deg2rad(lat_edges)
    lon_edges_rad = np.deg2rad(lon_edges)
    dlon = lon_edges_rad[1:] - lon_edges_rad[:-1]
    sin_dlat = np.sin(lat_edges_rad[1:]) - np.sin(lat_edges_rad[:-1])
    pixel_area = EARTH_RADIUS_KM ** 2 * sin_dlat[:, None] * dlon[None, :]

    return pixel_area[mask].sum()


def main():
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")

    for year in STUDY_YEARS:
        data_dir = VIIRS_GRIDDED_DIR.format(year=year)
        print(f"\n--- {year} ---")
        fire_annual, hotspot, labeled_da, top3 = detect_hotspot_clusters(data_dir, nepal)

        for rank, cluster in enumerate(top3, start=1):
            area_bbox = compute_cluster_area_km2_bbox(cluster)
            area_px = compute_cluster_area_km2_per_pixel(labeled_da, cluster)
            print(
                f"Cluster rank {rank} (ID {cluster['cluster']}): "
                f"size={cluster['size']} cells, "
                f"bbox area={area_bbox:.2f} km^2, "
                f"per-pixel area={area_px:.2f} km^2, "
                f"lat=[{cluster['lat_min']:.3f},{cluster['lat_max']:.3f}], "
                f"lon=[{cluster['lon_min']:.3f},{cluster['lon_max']:.3f}]"
            )


if __name__ == "__main__":
    main()
