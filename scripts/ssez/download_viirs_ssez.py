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
SHP_PATH = PROJECT_ROOT / "data" / "ssez" / "roi" / "ssez.shp"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ssez" / "gee"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "ssez_viirs_monthly_raw.csv"

# =========================================================
# 3. Load shapefile
#    SSEZ is an inland site; ocean pixel contamination is not an issue and no water mask is needed
# =========================================================
gdf = gpd.read_file(SHP_PATH)

print(f"Features read from file: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry types: {gdf.geom_type.unique().tolist()}")

gdf = gdf[~gdf.geometry.isna()].copy()
gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    raise ValueError("ssez.shp has no valid features. Please check that shp/dbf/shx/prj are all present.")

if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs("EPSG:4326")

print(f"Valid features: {len(gdf)}")
print(f"Bounding box: {gdf.total_bounds}")

geom_json = gdf.geometry.union_all().__geo_interface__
ssez_roi  = ee.Geometry(geom_json).simplify(maxError=1)

area_km2 = ssez_roi.area().divide(1e6).getInfo()
print(f"SSEZ ROI area: {area_km2:.4f} km²")

# =========================================================
# 4. VIIRS monthly nighttime light
# =========================================================
ntl_col = (
    ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    .filterDate("2014-01-01", "2026-03-31")
    .filterBounds(ssez_roi)
    .select("avg_rad", "cf_cvg")
)

count = ntl_col.size().getInfo()
print(f"VIIRS image count: {count}")

if count == 0:
    raise ValueError("No matching VIIRS images found.")

# =========================================================
# 5. Extraction function
#    SSEZ is an inland ROI; gt(0) excludes zero and negative noise; no water mask required
#    Primary metric: SOL_Sum (preferred for spatial expansion analysis)
#    Supplementary: Intensity_Mean (for cross-validation)
# =========================================================
def extract_ssez_stats(img):
    date = img.date().format("YYYY-MM-dd")

    rad = img.select("avg_rad")
    cvg = img.select("cf_cvg")

    img_masked = rad.updateMask(rad.gt(0))

    stats = img_masked.reduceRegion(
        reducer=ee.Reducer.sum().combine(
            reducer2=ee.Reducer.mean(),
            sharedInputs=True
        ),
        geometry=ssez_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    cvg_stats = cvg.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=ssez_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    # Preserve null so downstream code can distinguish missing (NaN) from genuinely low values
    return ee.Feature(None, {
        "date":           date,
        "SOL_Sum":        stats.get("avg_rad_sum"),
        "Intensity_Mean": stats.get("avg_rad_mean"),
        "avg_cvg":        cvg_stats.get("cf_cvg"),
    })

# =========================================================
# 6. Extract data
# =========================================================
print("Extracting SSEZ monthly nighttime light series from GEE...")
results = ntl_col.map(extract_ssez_stats).getInfo()

if not results["features"]:
    raise ValueError("GEE returned an empty result. Please check that the ROI is valid.")

# =========================================================
# 7. Construct data table
# =========================================================
data = [f["properties"] for f in results["features"]]
df   = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

df["SOL_Sum_raw"]        = df["SOL_Sum"].copy()
df["Intensity_Mean_raw"] = df["Intensity_Mean"].copy()

# Flag only genuine NaN; do not conflate with true zero values
df["is_cloud_gap"] = df["SOL_Sum_raw"].isna()

# is_low_cvg: marks low-quality months when avg_cvg < 1 (includes missing months where avg_cvg=0)
# Flags are exported directly to CSV to ensure consistent threshold application across pipeline stages
df["is_low_cvg"] = df["avg_cvg"].fillna(0) < 1

# =========================================================
# 8. Data quality check
# =========================================================
print("\n--- Descriptive statistics for quality indicator (cf_cvg) ---")
print(df["avg_cvg"].describe())

print(f"\nTotal fully missing months: {df['is_cloud_gap'].sum()}")
print(df[df["is_cloud_gap"]][["date", "avg_cvg", "SOL_Sum"]])

print(f"\nTotal low-quality months (avg_cvg < 1, including missing): {int(df['is_low_cvg'].sum())}")

# =========================================================
# 9. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n========== Download complete ==========")
print(f"Input shapefile: {SHP_PATH}")
print(f"Output CSV: {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows: {len(df)}")
print(df.head())
