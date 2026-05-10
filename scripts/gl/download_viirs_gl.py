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
# 1. Initialization
# =========================================================
ee.Initialize(project=GEE_PROJECT_ID)

# =========================================================
# 2. Path configuration
# =========================================================
SHP_PATH = PROJECT_ROOT / "data" / "gl" / "shp" / "gl.shp"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "gee"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "gl_viirs_monthly_raw.csv"

# =========================================================
# 3. Load local shapefile and convert to GEE Geometry
#    The ROI was manually digitized from Sentinel-2 imagery; ocean areas were manually excluded;
#    coastal zones are retained to capture nearshore commercial lighting; no additional water mask is required.
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
    raise ValueError(
        "gl.shp has no valid features. Please check that .shp/.dbf/.shx/.prj are all present and that the layer contains polygon features."
    )

if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs("EPSG:4326")

print(f"Valid features: {len(gdf)}")
print(f"Bounding box: {gdf.total_bounds}")

union_geom = gdf.geometry.union_all()
gl_roi = ee.Geometry(union_geom.__geo_interface__).simplify(maxError=1)

area_m2  = gl_roi.area().getInfo()
area_km2 = area_m2 / 1e6
print(f"GL ROI area: {area_m2:.0f} m² ({area_km2:.4f} km²)")

if area_km2 < 1e-4:
    raise ValueError(
        f"Area is abnormally small（{area_km2:.6f} km²），Please verify that the gl.shp coordinate system is correct."
    )

# =========================================================
# 4. VIIRS monthly nighttime light imagery
# =========================================================
ntl_col = (
    ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    .filterBounds(gl_roi)
    .filterDate("2014-01-01", "2026-03-31")
    .select("avg_rad", "cf_cvg")
)

count = ntl_col.size().getInfo()
print(f"VIIRS image count: {count}")

if count == 0:
    raise ValueError("No matching VIIRS images found. Please check that gl_roi is valid.")

# =========================================================
# 5. Extract monthly Intensity Mean, SOL Sum, and cf_cvg
#    Primary metric: Intensity_Mean (radiance density, suitable for a fixed small ROI)
#    Supplementary metric: SOL_Sum (total radiance, for cross-validation)
#    gt(0) excludes zero and negative noise; ocean areas were manually excluded from the ROI so no water mask is needed
# =========================================================
def extract_gl_stats(img):
    date = img.date().format("YYYY-MM-dd")

    rad = img.select("avg_rad")
    cvg = img.select("cf_cvg")

    img_masked = rad.updateMask(rad.gt(0))

    stats = img_masked.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.sum(),
            sharedInputs=True
        ),
        geometry=gl_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    cvg_stats = cvg.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=gl_roi,
        scale=463.83,
        bestEffort=True,
        maxPixels=1e10
    )

    # Preserve null so downstream code can distinguish missing (NaN) from genuinely low values
    return ee.Feature(None, {
        "date":           date,
        "Intensity_Mean": stats.get("avg_rad_mean"),
        "SOL_Sum":        stats.get("avg_rad_sum"),
        "avg_cvg":        cvg_stats.get("cf_cvg"),
    })

# =========================================================
# 6. Extract data
# =========================================================
print("Extracting GL monthly nighttime light series from GEE...")
results = ntl_col.map(extract_gl_stats).getInfo()

if not results["features"]:
    raise ValueError("GEE returned an empty result. Please check that gl.shp covers a valid area.")

# =========================================================
# 7. Construct data table
# =========================================================
data = [f["properties"] for f in results["features"]]
df = pd.DataFrame(data)

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

df["Mean_raw"] = df["Intensity_Mean"].copy()
df["Sum_raw"]  = df["SOL_Sum"].copy()

# Flag only genuine NaN; do not conflate with true zero values
df["is_cloud_gap"] = df["Mean_raw"].isna()

# is_low_cvg: marks months as low-quality when avg_cvg < 1
# Verified that missing months have avg_cvg=0 and are fully covered by <1; is_low_cvg is a superset of both
# fillna(0) serves as a defensive fallback in case GEE returns NaN values for avg_cvg
# Flags are exported directly to CSV to ensure consistent threshold application across pipeline stages
df["is_low_cvg"] = df["avg_cvg"].fillna(0) < 1

# =========================================================
# 8. Data quality check
# =========================================================
print("\n--- Descriptive statistics for quality indicator (cf_cvg) ---")
print(df["avg_cvg"].describe())

print(f"\nTotal fully missing months: {df['is_cloud_gap'].sum()}")
print(df[df["is_cloud_gap"]][["date", "avg_cvg", "Intensity_Mean"]])

print(f"\nTotal low-quality months (avg_cvg < 1, including missing): {int(df['is_low_cvg'].sum())}")

# =========================================================
# 9. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n========== Download complete ==========")
print(f"Input shapefile:  {SHP_PATH}")
print(f"Output CSV:  {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows:   {len(df)}")
print(df.head())
