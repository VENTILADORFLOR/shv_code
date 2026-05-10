import sys
from pathlib import Path

import ee
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

# =========================================================
# 0. Load project configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config.gee_config import GEE_PROJECT_ID

# =========================================================
# 1. Initialize Earth Engine
# =========================================================
ee.Initialize(project=GEE_PROJECT_ID)

# =========================================================
# 2. Output paths
# =========================================================

OUTPUT_DIR = PROJECT_ROOT / "data" / "shv" / "roi"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASENAME = "shv"
OUTPUT_SHP = OUTPUT_DIR / f"{BASENAME}.shp"

# =========================================================
# 3. Retrieve Preah Sihanouk provincial boundary from GEE
# =========================================================
province_roi = (
    ee.FeatureCollection("FAO/GAUL/2015/level1")
    .filter(ee.Filter.eq("ADM1_NAME", "Preah Sihanouk"))
    .geometry()
)

# =========================================================
# 4. Convert GEE geometry to Shapely geometry
# =========================================================
geom_info = province_roi.getInfo()
geom = shape(geom_info)

# =========================================================
# 5. Clean GeometryCollection
#    Retain only Polygon and MultiPolygon components.
# =========================================================
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
    raise ValueError("No Polygon or MultiPolygon geometries could be extracted; shapefile output is not possible.")

# Dissolve into a single geometry
merged = unary_union(polygons)

# Promote to MultiPolygon if necessary, for consistent shapefile output
if isinstance(merged, Polygon):
    merged = MultiPolygon([merged])

# =========================================================
# 6. Construct GeoDataFrame
# =========================================================
gdf = gpd.GeoDataFrame(
    [{
        "name": "Preah Sihanouk",
        "adm_level": "province",
        "geometry": merged
    }],
    crs="EPSG:4326"
)

# =========================================================
# 7. Remove existing sidecar files to prevent overwrite errors
# =========================================================
for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
    f = OUTPUT_DIR / f"{BASENAME}{ext}"
    if f.exists():
        f.unlink()

# =========================================================
# 8. Export shapefile
# =========================================================
gdf.to_file(OUTPUT_SHP, driver="ESRI Shapefile", encoding="utf-8")

# =========================================================
# 9. Output summary
# =========================================================
print("SHV provincial ROI shapefile written to:")
print(OUTPUT_SHP)
print(f"Feature count: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Geometry type: {gdf.geom_type.tolist()}")