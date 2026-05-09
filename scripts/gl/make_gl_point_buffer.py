utf-8import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

                                                           
                               
                                                           
lon, lat = 103.5236958225137, 10.610864542594356

                                                           
               
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_SHP_DIR = PROJECT_ROOT / "data" / "gl" / "shp"
POINT_DIR = BASE_SHP_DIR / "point"
BUFFER_DIR = BASE_SHP_DIR / "1km_buffer"

POINT_DIR.mkdir(parents=True, exist_ok=True)
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

POINT_FILE = POINT_DIR / "gl_center_point.shp"
BUFFER_FILE = BUFFER_DIR / "gl_1km_buffer.shp"

                                                           
                 
                                                           
point_geom = Point(lon, lat)

point_gdf = gpd.GeoDataFrame(
    {
              : ["golden_lions_center"],
             : [lon],
             : [lat]
    },
    geometry=[point_geom],
    crs="EPSG:4326"
)

                                                           
                 
                                                           
point_gdf.to_file(POINT_FILE, encoding="utf-8")

                                                           
                              
                                                           
point_gdf_utm = point_gdf.to_crs(epsg=32648)

buffer_gdf_utm = point_gdf_utm.copy()
buffer_gdf_utm["geometry"] = point_gdf_utm.buffer(1000)
buffer_gdf_utm["buffer_m"] = 1000

          
buffer_gdf = buffer_gdf_utm.to_crs(epsg=4326)

                                                           
                      
                                                           
buffer_gdf.to_file(BUFFER_FILE, encoding="utf-8")

                                                           
         
                                                           
print(f"Point shp 已生成:  {POINT_FILE}")
print(f"Buffer shp 已生成: {BUFFER_FILE}")
print("请确保每个 shp 的 .shp / .shx / .dbf / .prj / .cpg 文件都保存在各自文件夹内。")