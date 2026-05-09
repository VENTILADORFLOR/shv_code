utf-8import sys
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd

                                                           
           
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

                                                           
                     
                                                           
ee.Initialize(project=GEE_PROJECT_ID)

                                                           
       
                                                           
SHP_PATH = PROJECT_ROOT / "data" / "shv" / "roi" / "shv.shp"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shv" / "gee"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "shv_viirs_monthly_raw.csv"

                                                           
                            
                                                           
gdf = gpd.read_file(SHP_PATH)

print(f"原始读取要素数: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry类型: {gdf.geom_type.unique().tolist()}")

gdf = gdf[~gdf.geometry.isna()].copy()
gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    print("尝试用 buffer(0) 修复无效几何...")
    gdf_raw = gpd.read_file(SHP_PATH)
    gdf_raw["geometry"] = gdf_raw.geometry.buffer(0)
    gdf = gdf_raw[~gdf_raw.geometry.isna()].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

if len(gdf) == 0:
    raise ValueError("shv.shp 无有效要素，请检查 shp/dbf/shx/prj 是否齐全。")

if gdf.crs is None:
    print("警告：SHP 无 CRS，强制设为 EPSG:4326")
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_epsg() != 4326:
    print(f"CRS转换: {gdf.crs} -> EPSG:4326")
    gdf = gdf.to_crs("EPSG:4326")

print(f"经纬度范围: {gdf.total_bounds}")

union_geom = gdf.geometry.union_all()
geom_json = union_geom.__geo_interface__
province_roi = ee.Geometry(geom_json).simplify(maxError=1)

area_km2 = province_roi.area().divide(1e6).getInfo()
print(f"SHV 边界面积: {area_km2:.2f} km²")

                                                           
                 
                        
                                  
                                                           
                                     
land_mask = ee.Image("MODIS/006/MOD44W/2015_01_01").select("water_mask")

                         
                                   
land_only = land_mask.eq(0)

                                                           
               
                                                           
ntl_col = (
    ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    .filterBounds(province_roi)
    .filterDate("2014-01-01", "2026-03-31")
    .select("avg_rad", "cf_cvg")
)

count = ntl_col.size().getInfo()
print(f"VIIRS影像数量: {count}")

if count == 0:
    raise ValueError("没有找到符合条件的 VIIRS 影像。")

                                                           
         
                                                           
def extract_province_sol(img):
    date = img.date().format("YYYY-MM-dd")

    rad = img.select("avg_rad")
    cvg = img.select("cf_cvg")

                              
                                
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

                              
    return ee.Feature(None, {
              : date,
             : stats.get("avg_rad"),
                 : cvg_stats.get("cf_cvg")
    })

                                                           
         
                                                           
print("正在提取 SHV 月度 SOL 时序...")
results = ntl_col.map(extract_province_sol).getInfo()

if not results["features"]:
    raise ValueError("GEE 返回空结果，请检查 province_roi 是否有效。")

data = [f["properties"] for f in results["features"]]
df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

df["SOL_raw"] = df["SOL"].copy()

                         
df["is_cloud_gap"] = df["SOL_raw"].isna()

                                                           
                
                                                           
print("\n--- 质量指标 (cf_cvg) 统计描述 ---")
                                    
print(df["avg_cvg"].describe()) 

                                     
low_cvg_count = (df["avg_cvg"] < 1).sum()
print(f"低质量月份数量 (avg_cvg < 1): {low_cvg_count}")

                                                           
       
                                                           
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n========== 下载完成 ==========")
print(f"输入 shp: {SHP_PATH}")
print(f"输出 csv: {OUTPUT_CSV}")
print(f"时间范围: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"总行数: {len(df)}")
print(f"缺测月份: {df['is_cloud_gap'].sum()}")
print(df.head())