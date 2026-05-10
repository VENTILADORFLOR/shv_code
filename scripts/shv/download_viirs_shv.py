import sys
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd

# =========================================================
# 0. Load project configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

# =========================================================
# 1. Initialization Earth Engine
# =========================================================
ee.Initialize(project=GEE_PROJECT_ID)

# =========================================================
# 2. Paths
# =========================================================
SHP_PATH = PROJECT_ROOT / "data" / "shv" / "roi" / "shv.shp"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shv" / "gee"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "shv_viirs_monthly_raw.csv"

# =========================================================
# 3. Load local shapefile and convert to GEE Geometry
# =========================================================
gdf = gpd.read_file(SHP_PATH)

print(f"Features read from file: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry types: {gdf.geom_type.unique().tolist()}")

gdf = gdf[~gdf.geometry.isna()].copy()
gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    print("Attempting buffer(0) to repair invalid geometries...")
    gdf_raw = gpd.read_file(SHP_PATH)
    gdf_raw["geometry"] = gdf_raw.geometry.buffer(0)
    gdf = gdf_raw[~gdf_raw.geometry.isna()].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    raise ValueError("shv.shp has no valid features. Please check that shp/dbf/shx/prj are all present.")

if gdf.crs is None:
    print("Warning: shapefile has no CRS; forcing EPSG:4326")
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_epsg() != 4326:
    print(f"CRS conversion: {gdf.crs} -> EPSG:4326")
    gdf = gdf.to_crs("EPSG:4326")

print(f"Bounding box: {gdf.total_bounds}")

union_geom = gdf.geometry.union_all()
geom_json = union_geom.__geo_interface__
province_roi = ee.Geometry(geom_json).simplify(maxError=1)

area_km2 = province_roi.area().divide(1e6).getInfo()
print(f"SHV boundary area: {area_km2:.2f} km²")

# =========================================================
# 4. Water mask (MOD44W)
#    Purpose: exclude ocean pixels within the GAUL boundary
#    Limitation: baseline year 2015; reclaimed land is not captured, which is a known and documented limitation
# =========================================================
# Load a single image directly instead of using ImageCollection filtering
land_mask = ee.Image("MODIS/006/MOD44W/2015_01_01").select("water_mask")

# water_mask: 0=land, 1=water.
# Use .eq(0) to select land pixels (0=land becomes True, 1=water becomes False)
land_only = land_mask.eq(0)

# =========================================================
# 5. VIIRS monthly nighttime light
# =========================================================
ntl_col = (
    ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    .filterBounds(province_roi)
    .filterDate("2014-01-01", "2026-03-31")
    .select("avg_rad", "cf_cvg")
)

count = ntl_col.size().getInfo()
print(f"VIIRS image count: {count}")

if count == 0:
    raise ValueError("No matching VIIRS images found.")

# =========================================================
# 6. Extraction function
# =========================================================
def extract_province_sol(img):
    date = img.date().format("YYYY-MM-dd")

    rad = img.select("avg_rad")
    cvg = img.select("cf_cvg")

    # Land mask excludes ocean pixels; gt(0) excludes zero and negative noise
    # No brightness threshold is applied to avoid truncating dim provincial pixels which would bias the trend
    img_masked = rad.updateMask(land_only).updateMask(rad.gt(0))

    stats = img_masked.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=province_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    cvg_stats = cvg.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=province_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    # Preserve null so downstream code can distinguish missing (NaN) from genuinely low values
    return ee.Feature(None, {
        "date": date,
        "SOL": stats.get("avg_rad"),
        "avg_cvg": cvg_stats.get("cf_cvg")
    })

# =========================================================
# 7. Extract data
# =========================================================
print("Extracting SHV monthly SOL time series...")
results = ntl_col.map(extract_province_sol).getInfo()

if not results["features"]:
    raise ValueError("GEE returned an empty result. Please check that province_roi is valid.")

data = [f["properties"] for f in results["features"]]
df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

df["SOL_raw"] = df["SOL"].copy()

# Missing flag: mark only genuine NaN; do not conflate with true zero values
df["is_cloud_gap"] = df["SOL_raw"].isna()

# =========================================================
# 8. Data quality check
# =========================================================
print("\n--- Descriptive statistics for quality indicator (cf_cvg) ---")
# cf_cvg has been renamed avg_cvg in the DataFrame
print(df["avg_cvg"].describe()) 

# Quantify months with critically low cloud-free observation frequency (avg_cvg < 1)
low_cvg_count = (df["avg_cvg"] < 1).sum()
print(f"Low-quality month count (avg_cvg < 1): {low_cvg_count}")

# =========================================================
# 9. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n========== Download complete ==========")
print(f"Input shapefile: {SHP_PATH}")
print(f"Output CSV: {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows: {len(df)}")
print(f"Missing months: {df['is_cloud_gap'].sum()}")
print(df.head())