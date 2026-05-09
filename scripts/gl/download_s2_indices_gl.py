utf-8import sys
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd

                                                           
           
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

                                                           
        
                                                           
ee.Initialize(project=GEE_PROJECT_ID)

                                                           
         
                                                           
SHP_PATH = PROJECT_ROOT / "data" / "gl" / "shp" / "gl.shp"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "sentinel_indices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "gl_s2_indices_monthly.csv"

                                                           
           
                                                           
gdf = gpd.read_file(SHP_PATH)

print(f"原始读取要素数: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry类型: {gdf.geom_type.unique().tolist()}")

gdf = gdf[~gdf.geometry.isna()].copy()
gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    print("尝试 buffer(0) 修复无效几何...")
    gdf_raw = gpd.read_file(SHP_PATH)
    gdf_raw["geometry"] = gdf_raw.geometry.buffer(0)
    gdf = gdf_raw[~gdf_raw.geometry.isna()].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    raise ValueError("SHP 文件无有效要素。")

if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs("EPSG:4326")

print(f"有效要素数: {len(gdf)}")
print(f"经纬度范围: {gdf.total_bounds}")

union_geom = gdf.geometry.union_all()
gl_roi = ee.Geometry(union_geom.__geo_interface__).simplify(maxError=1)

area_m2  = gl_roi.area().getInfo()
area_km2 = area_m2 / 1e6
print(f"\n研究区面积: {area_m2:.0f} m² ({area_km2:.4f} km²)")

                                                           
         
                                                           
START_DATE = "2015-07-01"
END_DATE   = "2026-03-31"

                                                           
               
                                
                                                   
                                        
                                                           
def mask_s2_sr(image):
    scl = image.select("SCL")

                         
    valid = (
        scl.neq(0)            
        .And(scl.neq(1))                         
        .And(scl.neq(3))                
        .And(scl.neq(8))                            
        .And(scl.neq(9))                          
        .And(scl.neq(10))              
    )

    scaled = image.select(["B4", "B8", "B11"]).multiply(0.0001)
    return scaled.updateMask(valid).copyProperties(image, ["system:time_start"])

                                                           
                   
                                           
                                    
                                                           
s2_col = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(gl_roi)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
    .map(mask_s2_sr)
)

print(f"S2 影像数量: {s2_col.size().getInfo()}")

                                                           
        
                                                           
def make_month_starts(start_date, end_date):
    month_starts = pd.date_range(start=start_date, end=end_date, freq="MS")
    return [d.strftime("%Y-%m-%d") for d in month_starts]

month_starts = make_month_starts(START_DATE, END_DATE)
print(f"月份数量: {len(month_starts)}")

                                                           
         
                                                           
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
                  :        start.format("YYYY-MM-dd"),
                         : count,
                       :   stats.get("NDVI"),
                       :   stats.get("NDBI"),
        })

    def empty_stats():
        return ee.Feature(None, {
                  :        start.format("YYYY-MM-dd"),
                         : count,
                       :   None,
                       :   None,
        })

    return ee.Feature(ee.Algorithms.If(count.gt(0), compute_stats(), empty_stats()))

print("正在从 GEE 提取月度 NDVI / NDBI 时序...")
fc      = ee.FeatureCollection([monthly_indices(m) for m in month_starts])
results = fc.getInfo()

if not results["features"]:
    raise ValueError("GEE 返回空结果，请检查 ROI 或 Sentinel-2 数据可用性。")

                                                           
                 
                                                           
data = [f["properties"] for f in results["features"]]
df   = pd.DataFrame(data)

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

for col in ["image_count", "NDVI_mean", "NDBI_mean"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

                         
df["is_empty_month"] = df["image_count"].fillna(0) == 0

                                          
                                                 
df["is_low_quality"] = (df["image_count"].fillna(0) < 2) | df["NDVI_mean"].isna()

                            
df["NDVI_interp"] = df["NDVI_mean"].interpolate(method="linear", limit_direction="both")
df["NDBI_interp"] = df["NDBI_mean"].interpolate(method="linear", limit_direction="both")

print(f"\n数据行数: {len(df)}")
print(f"空月份数量 (image_count=0): {df['is_empty_month'].sum()}")
print(f"低质量月份数量 (image_count<2 或 NDVI缺失): {df['is_low_quality'].sum()}")
print(df.tail(12).to_string(index=False))

                                                           
        
                                                           
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n========== 完成 ==========")
print(f"输出文件: {OUTPUT_FILE}")
print(f"时间范围: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"有影像月份: {(df['image_count'] > 0).sum()} / {len(df)}")
