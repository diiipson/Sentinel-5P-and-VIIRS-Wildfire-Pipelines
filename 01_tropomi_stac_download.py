"""
Downloads daily TROPOMI NO2/CO data for Nepal from the S5P-PAL STAC API.

Goes through the whole collection for a given gas and year, keeps only
the granules that actually overlap the Nepal bounding box, crops them
down, and deletes the full global file afterward so we're not eating
disk space for no reason. Safe to re-run - it skips anything it's
already downloaded and cropped.

Set GAS to "no2-tropospheric" or "co" below and run it once per gas.
"""

import os
import time
import requests
from tqdm import tqdm
import xarray as xr

from config import LAT_MIN, LAT_MAX, LON_MIN, LON_MAX

# =====================================================
# SETTINGS - edit per gas/year before running
# =====================================================
GAS = "no2-tropospheric"  # or "co"
YEAR = 2024
COLLECTION_URL = f"https://data-portal.s5p-pal.com/api/s5p-l3/{GAS}/day/{YEAR}"
DOWNLOAD_DIR = rf"S:\viirs\{YEAR}_tropomi_{GAS.upper()}"
HEADERS = {"Accept": "application/json"}

NEPAL_BBOX = [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX]  # [min_lon, min_lat, max_lon, max_lat]

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def intersects(bbox1, bbox2):
    return not (
        bbox1[2] < bbox2[0] or
        bbox1[0] > bbox2[2] or
        bbox1[3] < bbox2[1] or
        bbox1[1] > bbox2[3]
    )


def download_file(url, filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        with open(filepath, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=filename
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
    return filepath


def main():
    print(f"Loading {YEAR} {GAS} collection...")
    collection = requests.get(COLLECTION_URL, headers=HEADERS).json()
    item_links = [link["href"] for link in collection["links"] if link["rel"] == "item"]
    print(f"Found {len(item_links)} daily items")

    for item_url in item_links:
        try:
            item = requests.get(item_url, headers=HEADERS, timeout=60).json()
            item_bbox = item.get("bbox", [-180, -90, 180, 90])

            if not intersects(item_bbox, NEPAL_BBOX):
                continue

            assets = item.get("assets", {})
            if "product" not in assets:
                continue

            url = assets["product"]["href"]
            orig_filename = assets["product"]["file:local_path"]

            cropped_filename = f"nepal_{orig_filename}"
            cropped_path = os.path.join(DOWNLOAD_DIR, cropped_filename)

            if os.path.exists(cropped_path):
                print(f"Skipping existing: {cropped_filename}")
                continue

            global_file = download_file(url, orig_filename)

            with xr.open_dataset(global_file) as ds:
                ds_nepal = ds.sel(
                    latitude=slice(NEPAL_BBOX[1], NEPAL_BBOX[3]),
                    longitude=slice(NEPAL_BBOX[0], NEPAL_BBOX[2]),
                )
                ds_nepal.to_netcdf(cropped_path)

            print(f"Saved cropped file: {cropped_path}")
            os.remove(global_file)
            time.sleep(2)  # avoid server throttling

        except Exception as e:
            print(f"Failed on item: {item_url}\n   Reason: {e}")
            continue

    print("All possible files processed")


if __name__ == "__main__":
    main()
