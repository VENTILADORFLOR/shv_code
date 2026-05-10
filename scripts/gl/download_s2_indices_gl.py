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

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "sentinel_indices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "gl_s2_indices_monthly.csv"

# =========================================================
# 3. Load shapefile
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
    raise ValueError("Shapefile contains no valid features.")

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
print(f"\nStudy area: {area_m2:.0f} m² ({area_km2:.4f} km²)")

# =========================================================
# 4. Time range configuration
# =========================================================
START_DATE = "2015-07-01"
END_DATE   = "2026-03-31"

# =========================================================
# 5. Cloud masking and band scaling
#    Excludes cloud, cloud shadow, and saturated pixels using SCL; retains valid land-surface pixels
#    SCL classes: 0=no data, 1=saturated/defective, 3=cloud shadow, 8=medium-probability cloud, 9=high-probability cloud, 10=thin cirrus
#    SCL is an integer classification band and is not scaled by multiply(0.0001)
# =========================================================
def mask_s2_sr(image):
    scl = image.select("SCL")

    # Exclude invalid pixels; retain all non-cloud and non-cloud-shadow classes
    valid = (
        scl.neq(0)   # no data
        .And(scl.neq(1))  # saturated / defective
        .And(scl.neq(3))  # cloud shadow
        .And(scl.neq(8))  # medium probability cloud
        .And(scl.neq(9))  # high probability cloud
        .And(scl.neq(10)) # thin cirrus
    )

    scaled = image.select(["B4", "B8", "B11"]).multiply(0.0001)
    return scaled.updateMask(valid).copyProperties(image, ["system:time_start"])

# =========================================================
# 6. Sentinel-2 dataset
#    Filter heavily cloud-covered scenes with CLOUDY_PIXEL_PERCENTAGE < 50
#    For a small ROI of ~3 km², 80% cloud cover leaves almost no valid pixels
# =========================================================
s2_col = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(gl_roi)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
    .map(mask_s2_sr)
)

print(f"S2 image count: {s2_col.size().getInfo()}")

# =========================================================
# 7. Monthly time series
# =========================================================
def make_month_starts(start_date, end_date):
    month_starts = pd.date_range(start=start_date, end=end_date, freq="MS")
    return [d.strftime("%Y-%m-%d") for d in month_starts]

month_starts = make_month_starts(START_DATE, END_DATE)
print(f"Month count: {len(month_starts)}")

# =========================================================
# 8. Monthly extraction
# =========================================================
def monthly_indices(month_start_str):
    start = ee.Date(month_start_str)
    end   = start.advance(1, "month")

    monthly = s2_col.filterDate(start, end)
    count   = monthly.size()

    def compute_stats():
        comp = monthly.median()

        ndvi = comp.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndbi = comp.normalizedDifference(["B11", "B8"]).rename("NDBI")

        img = ndvi.addBands(ndbi)

        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=gl_roi,
            scale=10,
            maxPixels=1e10,
            bestEffort=True
        )

        return ee.Feature(None, {
            "date":        start.format("YYYY-MM-dd"),
            "image_count": count,
            "NDVI_mean":   stats.get("NDVI"),
            "NDBI_mean":   stats.get("NDBI"),
        })

    def empty_stats():
        return ee.Feature(None, {
            "date":        start.format("YYYY-MM-dd"),
            "image_count": count,
            "NDVI_mean":   None,
            "NDBI_mean":   None,
        })

    return ee.Feature(ee.Algorithms.If(count.gt(0), compute_stats(), empty_stats()))

print("Extracting monthly NDVI / NDBI time series from GEE...")
fc      = ee.FeatureCollection([monthly_indices(m) for m in month_starts])
results = fc.getInfo()

if not results["features"]:
    raise ValueError("GEE returned an empty result. Please check ROI validity or Sentinel-2 data availability.")

# =========================================================
# 9. Construct DataFrame
# =========================================================
data = [f["properties"] for f in results["features"]]
df   = pd.DataFrame(data)

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

for col in ["image_count", "NDVI_mean", "NDBI_mean"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

# is_empty_month: no valid imagery at all for that month
df["is_empty_month"] = df["image_count"].fillna(0) == 0

# is_low_quality: image_count < 2 or NDVI is missing
# For a small ROI, composites from a single image are unreliable; mirrors the is_low_cvg logic in VIIRS
df["is_low_quality"] = (df["image_count"].fillna(0) < 2) | df["NDVI_mean"].isna()

# Interpolation (for downstream STL/merged analysis only; raw values are preserved)
df["NDVI_interp"] = df["NDVI_mean"].interpolate(method="linear", limit_direction="both")
df["NDBI_interp"] = df["NDBI_mean"].interpolate(method="linear", limit_direction="both")

print(f"\nData rows: {len(df)}")
print(f"Empty months (image_count=0): {df['is_empty_month'].sum()}")
print(f"Low-quality months (image_count<2 or NDVI missing): {df['is_low_quality'].sum()}")
print(df.tail(12).to_string(index=False))

# =========================================================
# 10. Export
# =========================================================
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n========== Done ==========")
print(f"Output file: {OUTPUT_FILE}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Months with imagery: {(df['image_count'] > 0).sum()} / {len(df)}")
