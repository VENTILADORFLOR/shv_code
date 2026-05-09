utf-8import ee
import sys
import os

                         
                                        
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

                         
if root_path not in sys.path:
    sys.path.append(root_path)

              
from config.gee_config import GEE_PROJECT_ID

                   
ee.Initialize(project=GEE_PROJECT_ID)

                      
col = ee.ImageCollection("MODIS/061/MOD44W").sort('system:time_start', False)

print(f"总影像数: {col.size().getInfo()}")

if col.size().getInfo() > 0:
    first_img = col.first()
    print("成功获取影像波段:")
    print(first_img.bandNames().getInfo())
else:
    print("依然没有找到影像，请尝试方案 B")

                             
                                                 