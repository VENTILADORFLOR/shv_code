utf-8import sys
from pathlib import Path

import ee
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

                                                           
           
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

                                                           
                     
                                                           
ee.Initialize(project=GEE_PROJECT_ID)

                                                           
         
                                                           

OUTPUT_DIR = PROJECT_ROOT / "data" / "shv" / "roi"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASENAME = "shv"
OUTPUT_SHP = OUTPUT_DIR / f"{BASENAME}.shp"

                                                           
                                 
                                                           
province_roi = (
    ee.FeatureCollection("FAO/GAUL/2015/level1")
    .filter(ee.Filter.eq("ADM1_NAME", "Preah Sihanouk"))
    .geometry()
)

                                                           
                       
                                                           
geom_info = province_roi.getInfo()
geom = shape(geom_info)

                                                           
                          
                               
                                                           
def extract_polygons(g):
    polys = []

    if isinstance(g, Polygon):
        polys.append(g)

    elif isinstance(g, MultiPolygon):
        polys.extend(list(g.geoms))

    elif isinstance(g, GeometryCollection):
        for part in g.geoms:
            polys.extend(extract_polygons(part))

    return polys

polygons = extract_polygons(geom)

if not polygons:
    raise ValueError("未提取到任何 Polygon / MultiPolygon，无法输出为 shp。")

         
merged = unary_union(polygons)

                                              
if isinstance(merged, Polygon):
    merged = MultiPolygon([merged])

                                                           
                    
                                                           
gdf = gpd.GeoDataFrame(
    [{
              : "Preah Sihanouk",
                   : "province",
                  : merged
    }],
    crs="EPSG:4326"
)

                                                           
                 
                                                           
for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
    f = OUTPUT_DIR / f"{BASENAME}{ext}"
    if f.exists():
        f.unlink()

                                                           
           
                                                           
gdf.to_file(OUTPUT_SHP, driver="ESRI Shapefile", encoding="utf-8")

                                                           
         
                                                           
print("SHV province roi 已输出：")
print(OUTPUT_SHP)
print(f"要素数: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry 类型: {gdf.geom_type.tolist()}")