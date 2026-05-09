shv-gl-ssez

Remote sensing and spatial analysis of urban transformation in Sihanoukville, Cambodia, focusing on three functionally distinct nodes:

- Urban core (SHV)
- Commercial hub (Golden Lions)
- Industrial zone (SSEZ)

This project integrates VIIRS nighttime lights, Sentinel-2 indices, and spatial analysis to quantify uneven recovery, structural divergence, and policy shock responses in a data-scarce urban environment.


========================
Study Areas
========================

- Sihanoukville (SHV) — Urban baseline and macro dynamics  
- Golden Lions (GL) — High-density commercial and nightlife core  
- SSEZ — Industrial production and export-oriented zone  

This multi-node design enables comparison between consumption-driven, service-based, and production-based urban systems.


========================
Repository Structure
========================

data/            Boundary and ROI shapefiles  
scripts/         Python scripts for download, processing, analysis, and plotting  
outputs/         Generated CSV tables, statistics, figures, and selected results  
docs/            Manuscript and submission-related documents  
arcgisproject/   ArcGIS layout previews and project package  
large_files/     Local-only large files (ignored)  
config/          Local configuration (ignored)  
.github/         GitHub Actions workflow  


========================
Main Workflows
========================

[1] Sihanoukville

scripts/shv/
- make_shv_roi.py
- download_viirs_shv.py
- analyze_shv.py
- plot_shv.py

outputs/shv/
- gee/
- stats/
- figures/


[2] Golden Lions

scripts/gl/
- make_gl_point_buffer.py
- download_viirs_gl.py
- download_s2_indices_gl.py
- analyze_gl.py
- merge_ntl_s2_gl.py
- make_stage_tables_gl.py
- plot_gl.py
- plot_ntl_vs_s2_gl.py

outputs/gl/
- gee/
- sentinel_indices/
- merged/
- stats/
- tables/
- figures/


[3] SSEZ

scripts/ssez/
- download_viirs_ssez.py
- download_sentinel_ssez.py
- analyze_ssez.py
- plot_ssez.py

outputs/ssez/
- gee/
- sentinel/
- stats/
- figures/


[4] Integrated Analysis

scripts/integrated/
- compare_three_nodes.py
- compare_vitality.py
- make_integrated_tables.py

outputs/integrated/
- stats/
- tables/
- figures/


========================
Key Outputs
========================

Figures:
- outputs/integrated/figures/three_nodes_main.png
- outputs/integrated/figures/comparison_vitality_main.png
- outputs/integrated/figures/comparison_structural_divergence.png

Tables:
- outputs/integrated/tables/phase_average_indices.csv
- outputs/integrated/tables/table2_phase_average_indices.csv
- outputs/integrated/tables/table3_policy_shock_response.csv


========================
Documents
========================

docs/
- sihanoukville_rsase_final.docx
- GeoJournal_adaptation_draft.docx
- Declaration_of_interest.docx
- Ethical_statement.docx
- RSASE submission PDF


========================
Methodological Framework
========================

- VIIRS Nighttime Lights (NTL) — economic activity proxy  
- Sentinel-2 indices — NDVI, NDBI for built-environment dynamics  
- STL decomposition — trend and seasonal extraction  
- Comparative node analysis — structural divergence across urban functions  

Designed for data-scarce environments.


========================
Environment
========================

pip install -r requirements.txt

Main libraries:
- earthengine-api
- geemap
- geopandas
- pandas
- numpy
- matplotlib
- rasterio
- shapely


========================
Configuration
========================

config/gee_config.py

Example:
GEE_PROJECT_ID = "your-project-id"

(config folder is ignored in GitHub)


========================
Large Files Policy
========================

Ignored file types:
- *.psd
- *.tif
- *.tiff
- *.zip
- *.ppkx
- *.aux.xml
- __pycache__/

Local storage:
large_files/


========================
Suggested Workflow
========================

1. Prepare boundaries → data/
2. Download data → scripts/*/download_*.py
3. Run analysis → scripts/*/analyze_*.py
4. Generate figures → scripts/*/plot_*.py
5. Integrated comparison → scripts/integrated/


========================
Project Positioning
========================

- Research reproducibility package  
- Manuscript support material  
- Remote sensing workflow demonstration  
- Academic / portfolio project  

(Not intended for large raw datasets)


========================
License
========================

For academic and research use.