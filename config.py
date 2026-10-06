


#Open this file and fix the paths before running anything else.


# ----------------------------------------------------------------------
# The study area - Nepal plus a bit of a buffer around it
# ----------------------------------------------------------------------
LAT_MIN, LAT_MAX = 26.3, 30.5
LON_MIN, LON_MAX = 80.0, 88.5

# Grid resolution everything gets binned to (~10 km), matched to
# TROPOMI's own NO2 grid so the fire grid and the gas grid line up cell
# for cell.
GRID_RES_DEG = 0.02197265625

# Which years we're covering
STUDY_YEARS = [2021, 2022, 2023, 2024]

# Pre-monsoon / fire season - this is when almost all the fire activity
# happens, so it's the window used for the hotspot detection and the
# seasonal stats
PRE_MONSOON_MONTHS = [3, 4, 5]

# Jan-Feb counts as "before the fires start" - used as the quiet
# baseline that fire-season NO2/CO gets compared against
BASELINE_MONTHS = [1, 2]

# A grid cell counts as a hotspot if it's in the top 10% of fire
# activity for the year. (Earlier versions of this analysis tried 95th
# percentile too, before settling on 90th.)
HOTSPOT_PERCENTILE = 0.90

# Needed for turning a cluster's lat/lon extent into an actual area in km^2
EARTH_RADIUS_KM = 6371.0

# ----------------------------------------------------------------------
# Paths - these are placeholders, change them to match your own machine.
# ----------------------------------------------------------------------
VIIRS_RAW_DIR = r"S:\viirs\VNP14IMG_002-REPLACE_ME"          # one year of raw VNP14IMG swaths
VIIRS_GRIDDED_DIR = r"S:\viirs\gridalligned_{year}_VIIRS_daily_gridded_0.021_nc"  # {year} is filled in per year
TROPOMI_NO2_DIR = r"S:\viirs\{year}_tropomi_NO2"
TROPOMI_CO_DIR = r"S:\viirs\{year}_tropomi_COT"
NEPAL_BOUNDARY_SHP = r"C:\Users\ACER\Downloads\boundary.shp"
NEPAL_DISTRICTS_SHP = r"C:\Users\ACER\Downloads\districts0___2026_May_31_09_55_56\districts0\districts0.shp"

# Any one TROPOMI file works here - we just need its exact lat/lon grid
# centers so the VIIRS fire grid can be built on the same grid instead
# of a slightly-offset one of its own.
TROPOMI_REFERENCE_FILE = r"C:\Users\ACER\Downloads\April1_s5p-no2-cropped.nc"

# Nepal's physiographic zones (Terai, Siwalik, Hill, Lesser Himalaya,
# Higher Himalaya) - used for the zones map and for picking out the
# Himalaya region when we look at trace gases up there. Hosted on
# GitHub, see DATA_SOURCES.md for details.
PHYSIOGRAPHIC_ZONES_URL = (
    "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/"
    "main/geojson_files/physiography_nepal_updated.geojson"
)

# ----------------------------------------------------------------------
# The top-3 hotspot cluster boxes for each year, straight from
# re-running the hotspot detection once per year and copying the
# results in here so every other script can just look them up instead
# of recomputing them every time.
# ----------------------------------------------------------------------
CLUSTER_BBOXES_BY_YEAR = {
    2021: {
        1: {"lat_min": 27.938232421875, "lat_max": 28.839111328125, "lon_min": 81.243896484375, "lon_max": 82.342529296875},
        2: {"lat_min": 28.795166015625, "lat_max": 29.278564453125, "lon_min": 80.233154296875, "lon_max": 80.914306640625},
        3: {"lat_min": 27.169189453125, "lat_max": 27.586669921875, "lon_min": 84.298095703125, "lon_max": 85.067138671875},
    },
    2022: {
        1: {"lat_min": 27.674560546875, "lat_max": 29.168701171875, "lon_min": 80.233154296875, "lon_max": 83.089599609375},
        2: {"lat_min": 29.168701171875, "lat_max": 29.520263671875, "lon_min": 80.233154296875, "lon_max": 80.870361328125},
        3: {"lat_min": 27.059326171875, "lat_max": 27.432861328125, "lon_min": 84.715576171875, "lon_max": 85.155029296875},
    },
    2023: {
        1: {"lat_min": 27.630615234375, "lat_max": 28.026123046875, "lon_min": 82.144775390625, "lon_max": 83.529052734375},
        2: {"lat_min": 27.916259765625, "lat_max": 28.707275390625, "lon_min": 81.331787109375, "lon_max": 82.474365234375},
        3: {"lat_min": 27.103271484375, "lat_max": 27.784423828125, "lon_min": 84.254150390625, "lon_max": 85.155029296875},
    },
    2024: {
        1: {"lat_min": 27.674560546875, "lat_max": 28.773193359375, "lon_min": 81.265869140625, "lon_max": 82.760009765625},
        2: {"lat_min": 27.191162109375, "lat_max": 27.564697265625, "lon_min": 84.232177734375, "lon_max": 85.089111328125},
        3: {"lat_min": 28.817138671875, "lat_max": 29.322509765625, "lon_min": 80.233154296875, "lon_max": 80.782470703125},
    },
}

# How many of the 4 years each district showed up in a top-3 hotspot
# cluster - this was tallied by hand after looking at each year's
# cluster map, not computed automatically.
DISTRICT_HOTSPOT_PERSISTENCE = {
    "District": [
        "Bardiya", "Banke", "Dang", "Surkhet", "Parsa", "Bara",
        "Kailali", "Dadeldhura", "Chitwan", "Salyan", "Kanchanpur",
        "Arghakhanchi", "Baitadi", "Rupandehi", "Palpa", "Kapilbastu", "Makwanpur",
    ],
    "Years_Present": [4, 4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1],
}
