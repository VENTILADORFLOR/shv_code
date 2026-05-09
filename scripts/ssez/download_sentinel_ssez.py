utf-8import sys
from pathlib import Path

import ee
import geemap

                                                           
           
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

                                                           
                     
                                                           
ee.Initialize(project=GEE_PROJECT_ID)

                                                           
         
                                                           

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ssez" / "sentinel"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_TIF = OUTPUT_DIR / "ssez_s2_rgb_2025-11_2026-03.tif"

                                                           
                      
                
                                                           
lon, lat = 103.634477, 10.634500
buffer_m = 4000

roi = ee.Geometry.Point([lon, lat]).buffer(buffer_m)

print(f"SSEZ point: ({lon}, {lat})")
print(f"Buffer radius: {buffer_m} m")

                                                           
                    
                                                           
s2_col = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(roi)
    .filterDate("2025-11-01", "2026-03-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
)

count = s2_col.size().getInfo()
print(f"符合条件的 Sentinel-2 影像数量: {count}")

if count == 0:
    raise ValueError("没有找到符合条件的影像，请检查时间范围或云量阈值。")

dates = s2_col.aggregate_array("system:time_start").map(
    lambda d: ee.Date(d).format("YYYY-MM-dd")
).getInfo()

print("影像日期如下：")
print(dates)

                                                           
             
                                                           
s2_img = s2_col.median().clip(roi)
s2_rgb = s2_img.select(["B4", "B3", "B2"])

                                                           
       
                                                           
print(f"\n开始导出到: {OUTPUT_TIF}")

geemap.ee_export_image(
    s2_rgb,
    filename=str(OUTPUT_TIF),
    scale=10,
    region=roi,
    file_per_band=False
)

if OUTPUT_TIF.exists():
    print(f"下载成功: {OUTPUT_TIF}")
else:
    print("导出命令已执行，但本地未检测到文件，请检查网络、权限或 GEE 配额。")