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

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "gee"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "gl_viirs_monthly_raw.csv"

                                                           
                             
                                      
                               
                                                           
gdf = gpd.read_file(SHP_PATH)

print(f"原始读取要素数: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry 类型: {gdf.geom_type.unique().tolist()}")

gdf = gdf[~gdf.geometry.isna()].copy()
gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    print("尝试 buffer(0) 修复无效几何...")
    gdf_raw = gpd.read_file(SHP_PATH)
    gdf_raw["geometry"] = gdf_raw.geometry.buffer(0)
    gdf = gdf_raw[~gdf_raw.geometry.isna()].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    raise ValueError(
                                                               
    )

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
print(f"GL ROI 面积: {area_m2:.0f} m² ({area_km2:.4f} km²)")

if area_km2 < 1e-4:
    raise ValueError(
                                                        
    )

                                                           
                 
                                                           
ntl_col = (
    ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    .filterBounds(gl_roi)
    .filterDate("2014-01-01", "2026-03-31")
    .select("avg_rad", "cf_cvg")
)

count = ntl_col.size().getInfo()
print(f"VIIRS 影像数量: {count}")

if count == 0:
    raise ValueError("没有找到符合条件的 VIIRS 影像，请检查 gl_roi 是否有效。")

                                                           
                                         
                                      
                           
                                       
                                                           
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

                              
    return ee.Feature(None, {
              :           date,
                        : stats.get("avg_rad_mean"),
                 :        stats.get("avg_rad_sum"),
                 :        cvg_stats.get("cf_cvg"),
    })

                                                           
         
                                                           
print("正在从 GEE 提取 GL 月度夜光序列...")
results = ntl_col.map(extract_gl_stats).getInfo()

if not results["features"]:
    raise ValueError("GEE 返回空结果，请检查 gl.shp 是否覆盖了有效区域。")

                                                           
         
                                                           
data = [f["properties"] for f in results["features"]]
df = pd.DataFrame(data)

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

df["Mean_raw"] = df["Intensity_Mean"].copy()
df["Sum_raw"]  = df["SOL_Sum"].copy()

                    
df["is_cloud_gap"] = df["Mean_raw"].isna()

                                
                                                
                                         
                                             
df["is_low_cvg"] = df["avg_cvg"].fillna(0) < 1

                                                           
           
                                                           
print("\n--- 质量指标 (cf_cvg) 统计描述 ---")
print(df["avg_cvg"].describe())

print(f"\n完全缺测月份总数: {df['is_cloud_gap'].sum()}")
print(df[df["is_cloud_gap"]][["date", "avg_cvg", "Intensity_Mean"]])

print(f"\n低质量月份总数 (avg_cvg < 1, 含缺测): {int(df['is_low_cvg'].sum())}")

                                                           
       
                                                           
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n========== 下载完成 ==========")
print(f"输入 shp:  {SHP_PATH}")
print(f"输出 csv:  {OUTPUT_CSV}")
print(f"时间范围: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"总行数:   {len(df)}")
print(df.head())
