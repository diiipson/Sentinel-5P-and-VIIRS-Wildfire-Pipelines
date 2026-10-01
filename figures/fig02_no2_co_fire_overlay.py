"""
Fig. 2 / Fig. S1 - Seven-day mean (1-7 April 2021) tropospheric NO2 (Fig.
2) and total CO (Fig. S1) column density overlaid with VIIRS-derived
fire variables: (a) fire count, (b) FRP sum, (c) FRP max, (d) daytime
fire count, (e) nighttime fire count.

SOURCE: fig2.py (full file, 372 lines). This is the final/refined
version: it uses PowerNorm(gamma=0.4) to stretch low fire counts apart
for better contrast, handles the case where the fire and gas grids
don't exactly match, and masks outside-Nepal pixels for both grids
independently.

An earlier draft of the NO2 panel exists at methodology.py lines
150-301, without the PowerNorm contrast adjustment or the fire/NO2 grid
mismatch handling - superseded by this version.

NOT INCLUDED: fig2.py's final section (lines 325-373), a "normal
distribution of daily fire count by year" histogram, is unrelated
exploratory analysis that does not correspond to any paper figure -
left out of this extraction. See EXTRACTION_LOG.md.

CHANGED FROM SOURCE (non-functional cleanup only):
  - Pulled the Nepal boundary path from config.py.
  - Split into functions for the NO2 panel (Fig. 2) and CO panel
    (Fig. S1), each independently callable.
"""

import glob
import os
import sys

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import rioxarray  # noqa: F401
import xarray as xr

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from config import NEPAL_BOUNDARY_SHP

FIRE_VARS = ["fire_count", "frp_sum", "frp_max", "day_count", "night_count"]
FIRE_TITLES = {
    "fire_count": "Fire Count (7 days)",
    "frp_sum": "FRP Sum (MW, 7 days)",
    "frp_max": "FRP Max (MW, 7 days)",
    "day_count": "Day Count (7 days)",
    "night_count": "Night Count (7 days)",
}


def _apply_mask(da, mask):
    data = da.values.copy().astype(float)
    data[~mask] = np.nan
    return xr.DataArray(data, coords=da.coords, dims=da.dims)


def _plot_fire_overlay(background, background_lat, background_lon, background_cmap,
                        background_label, fire_vars_7d, fire_ref, nepal, out_path):
    n_vars = len(fire_vars_7d)
    n_cols, n_rows = 2, (n_vars + 1) // 2
    fire_cmap = plt.cm.get_cmap("Reds").copy()
    fire_cmap.set_bad(color="none")

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(10, n_rows * 3))
    fig.patch.set_facecolor("white")
    axes_flat = axes.flatten()

    for i, var in enumerate(fire_vars_7d):
        ax = axes_flat[i]
        im_bg = ax.pcolormesh(background_lon, background_lat, background, shading="auto", cmap=background_cmap)

        fire_data = fire_vars_7d[var].values.copy().astype(float)
        fire_data[fire_data == 0] = np.nan
        fire_masked = np.ma.masked_invalid(fire_data)

        if np.ma.count(fire_masked) > 0:
            vmin = float(fire_masked.compressed().min())
            vmax = float(fire_masked.compressed().max())
            norm = mcolors.PowerNorm(gamma=0.4, vmin=vmin, vmax=vmax)
            im_fire = ax.pcolormesh(
                fire_ref["lon"], fire_ref["lat"], fire_masked,
                shading="auto", cmap=fire_cmap, norm=norm, alpha=0.95,
            )
            cbar_fire = fig.colorbar(im_fire, ax=ax, orientation="vertical", fraction=0.025, pad=0.1)
            cbar_fire.set_label(FIRE_TITLES[var], fontsize=7, rotation=90, labelpad=8, va="bottom")
            norm_positions = np.linspace(0, 1, 5)
            data_values = norm.inverse(norm_positions)
            cbar_fire.set_ticks(data_values)
            fmt = (lambda v: f"{v:.1f}") if vmax <= 10 else (lambda v: f"{int(round(v))}")
            cbar_fire.set_ticklabels([fmt(v) for v in data_values])

        cbar_bg = fig.colorbar(im_bg, ax=ax, orientation="vertical", fraction=0.025, pad=0.04)
        cbar_bg.set_label(background_label, fontsize=7, rotation=90, labelpad=8, va="bottom")
        nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=0.6)
        ax.set_xlabel("Longitude", fontsize=7)
        ax.set_ylabel("Latitude", fontsize=7)
        ax.tick_params(axis="both", which="major", labelsize=7)

    if n_vars % 2 != 0:
        axes_flat[-1].set_visible(False)

    plt.tight_layout()
    plt.savefig(out_path, dpi=1000, bbox_inches="tight")
    plt.show()


def load_7day_fire_and_no2(merged_dir, pattern):
    """merged_dir/pattern should point at 7 daily *_VIIRS_TROPOMI.nc files."""
    merged_files = sorted(glob.glob(f"{merged_dir}\\{pattern}"))[:7]
    datasets = [xr.open_dataset(f) for f in merged_files]

    no2_stack = xr.concat([ds["tropospheric_NO2_column_number_density"].squeeze() for ds in datasets], dim="time")
    no2_mean = no2_stack.mean(dim="time")

    fire_ref = datasets[0]["fire_count"]
    fire_vars_7d = {
        "fire_count": sum(ds["fire_count"] for ds in datasets),
        "frp_sum": sum(ds["frp_sum"] for ds in datasets),
        "day_count": sum(ds["day_count"] for ds in datasets),
        "night_count": sum(ds["night_count"] for ds in datasets),
        "frp_max": xr.concat([ds["frp_max"] for ds in datasets], dim="time").max(dim="time"),
    }
    return no2_mean, fire_ref, fire_vars_7d


def fig2_no2_overlay(merged_dir="S:\\viirs\\merged_2021", pattern="202104*_VIIRS_TROPOMI.nc"):
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")
    no2_mean, fire_ref, fire_vars_7d = load_7day_fire_and_no2(merged_dir, pattern)

    ref_clipped = no2_mean.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326")
    mask_no2 = ~np.isnan(ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False).values)

    mask_fire = mask_no2  # fire and NO2 grids match after 02_viirs_gridding.py's TROPOMI alignment
    fire_vars_7d = {k: _apply_mask(v, mask_fire) for k, v in fire_vars_7d.items()}

    no2_masked = no2_mean.values.copy().astype(float)
    no2_masked[~mask_no2] = np.nan
    no2_cmap = plt.cm.get_cmap("viridis").copy()
    no2_cmap.set_bad(color="white")

    _plot_fire_overlay(
        no2_masked, no2_mean["lat"], no2_mean["lon"], no2_cmap, "NO2 (umol/m2)",
        fire_vars_7d, fire_ref, nepal,
        r"S:\viirs\pictures\sample\fire_on_no2_background.png",
    )


def fig_s1_co_overlay(co_dir="S:\\viirs\\2021_tropomi_COT", merged_dir="S:\\viirs\\merged_2021",
                       pattern="202104*_VIIRS_TROPOMI.nc"):
    nepal = gpd.read_file(NEPAL_BOUNDARY_SHP).to_crs("EPSG:4326")
    _, fire_ref, fire_vars_7d = load_7day_fire_and_no2(merged_dir, pattern)

    co_dates = [f"2021040{d}" for d in range(1, 8)]
    co_files = sorted(f for f in glob.glob(f"{co_dir}\\*.nc") if any(d in f for d in co_dates))
    co_datasets = [xr.open_dataset(f) for f in co_files]
    co_mean = xr.concat([ds["CO_column_number_density"].squeeze() for ds in co_datasets], dim="time").mean(dim="time")

    co_ref_clipped = co_mean.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude").rio.write_crs("EPSG:4326")
    mask_co = ~np.isnan(co_ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False).values)
    co_masked = co_mean.values.copy().astype(float)
    co_masked[~mask_co] = np.nan

    co_cmap = plt.cm.get_cmap("plasma").copy()
    co_cmap.set_bad(color="white")

    _plot_fire_overlay(
        co_masked, co_mean["latitude"], co_mean["longitude"], co_cmap, "CO (mol m-2)",
        fire_vars_7d, fire_ref, nepal,
        r"S:\viirs\pictures\sample\fire_on_co_background.png",
    )


if __name__ == "__main__":
    fig2_no2_overlay()
    fig_s1_co_overlay()
