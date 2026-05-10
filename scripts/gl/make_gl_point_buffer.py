# -*- coding: utf-8 -*-
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

# =========================================================
# 1. Coordinates of the Golden Lions Roundabout centroid
# =========================================================
lon, lat = 103.5236958225137, 10.610864542594356

# =========================================================
# 2. Project root and output directories
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_SHP_DIR = PROJECT_ROOT / "data" / "gl" / "shp"
POINT_DIR = BASE_SHP_DIR / "point"
BUFFER_DIR = BASE_SHP_DIR / "1km_buffer"

POINT_DIR.mkdir(parents=True, exist_ok=True)
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

POINT_FILE = POINT_DIR / "gl_center_point.shp"
BUFFER_FILE = BUFFER_DIR / "gl_1km_buffer.shp"

# =========================================================
# 3. Create point
# =========================================================
point_geom = Point(lon, lat)

point_gdf = gpd.GeoDataFrame(
    {
        "name": ["golden_lions_center"],
        "lon": [lon],
        "lat": [lat]
    },
    geometry=[point_geom],
    crs="EPSG:4326"
)

# =========================================================
# 4. Export point shapefile
# =========================================================
point_gdf.to_file(POINT_FILE, encoding="utf-8")

# =========================================================
# 5. Generate 1 km buffer
#    Project to UTM Zone 48N (EPSG:32648) for metric buffering,
#    then reproject back to WGS84 (EPSG:4326) for output.
# =========================================================
point_gdf_utm = point_gdf.to_crs(epsg=32648)

buffer_gdf_utm = point_gdf_utm.copy()
buffer_gdf_utm["geometry"] = point_gdf_utm.buffer(1000)
buffer_gdf_utm["buffer_m"] = 1000

# Reproject buffer to WGS84
buffer_gdf = buffer_gdf_utm.to_crs(epsg=4326)

# =========================================================
# 6. Export buffer shapefile
# =========================================================
buffer_gdf.to_file(BUFFER_FILE, encoding="utf-8")

# =========================================================
# 7. Output summary
# =========================================================
print(f"Point shapefile written to:  {POINT_FILE}")
print(f"Buffer shapefile written to: {BUFFER_FILE}")
print("Verify that each shapefile directory contains all required sidecar files: .shp, .shx, .dbf, .prj, .cpg")
