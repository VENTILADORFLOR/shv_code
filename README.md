# SHV Multi-Node NTL Analysis — Scripts

Analysis code for the paper:

> Li, Y. "Functional Zone Divergence Under Successive Policy Shocks in a Rapidly Urbanizing Coastal City: Evidence from Multi-Node Nighttime-Light Monitoring, Sihanoukville, Cambodia (2014–2026)." *Journal of Urban Planning and Development* (submitted).

All satellite data are accessed via [Google Earth Engine](https://earthengine.google.com/). A GEE account is required to run the download scripts.

---

## Requirements

```
Python >= 3.9
earthengine-api
geopandas
rasterio
pandas
numpy
statsmodels
matplotlib
scipy
```

Install dependencies:

```bash
pip install earthengine-api geopandas rasterio pandas numpy statsmodels matplotlib scipy
earthengine authenticate
```

---

## Repository Structure

```
scripts/
├── gl/                          # Golden Lions commercial service node (ROI: 2.94 km²)
│   ├── make_gl_point_buffer.py  # Generate 1 km circular buffer from roundabout centroid; clip sea surface
│   ├── download_viirs_gl.py         # Extract monthly VIIRS/DNB avg_rad (VCMSLCFG) for GL ROI via GEE
│   ├── download_s2_indices_gl.py    # Extract monthly Sentinel-2 NDBI and NDVI for GL ROI via GEE
│   ├── analyze_gl.py                # STL decomposition, normalised index (2017=100), YoY rates
│   ├── merge_ntl_s2_gl.py           # Merge NTL and Sentinel-2 time series into cross-validation dataset
│   ├── make_stage_tables_gl.py      # Compute phase-average statistics across four policy phases
│   ├── plot_gl.py                   # Plot NTL trend, normalised index, and YoY growth panels
│   └── plot_ntl_vs_s2_gl.py         # NTL–NDBI/NDVI correlation plots and NTL/NDBI ratio analysis
│
├── ssez/                        # Sihanoukville Special Economic Zone (ROI: 9.30 km²)
│   ├── download_viirs_ssez.py       # Extract monthly VIIRS/DNB SOL Sum for SSEZ boundary via GEE
│   ├── check_quality.py     # VIIRS monthly coverage QA: flag low-coverage and monsoon-gap months for SSEZ
│   ├── analyze_ssez.py              # STL decomposition, normalised index, shock response metrics
│   └── plot_ssez.py                 # Plot NTL trend, normalised index, and YoY growth panels
│
├── shv/                         # Preah Sihanouk Province administrative baseline (1,605 km²)
│   ├── make_shv_roi.py              # Extract provincial boundary from FAO GAUL 2015 level-1 via GEE
│   ├── download_viirs_shv.py        # Extract monthly VIIRS/DNB SOL Sum for provincial ROI via GEE
│   ├── analyze_shv.py               # STL decomposition, normalised index, provincial trend analysis
│   └── plot_shv.py                  # Plot provincial NTL trend and STL decomposition panels
│
└── integrated/                  # Cross-node comparison
    ├── compare_vitality.py          # Three-node normalised index overlay, YoY correlation, shock response comparison
    └── make_integrated_tables.py    # Generate Tables 2–5 from the paper (phase averages, correlations, sanctions signal)
```

---

## Data Sources

| Dataset | GEE ID | Resolution | Period |
|---|---|---|---|
| VIIRS/DNB Monthly (stray-light corrected) | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` | 500 m | Jan 2014–Mar 2026 |
| Sentinel-2 SR Harmonised | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Jul 2015–Mar 2026 |
| FAO GAUL 2015 Level-1 | `FAO/GAUL/2015/level1` | — | — |
| MODIS MOD44W Water Mask | `MODIS/006/MOD44W` | 250 m | 2015 |

---

## Suggested Run Order

```
# 1. Define ROIs
shv/make_shv_roi.py
gl/make_gl_point_buffer.py

# 2. Download satellite data
shv/download_viirs_shv.py
gl/download_viirs_gl.py
gl/download_s2_indices_gl.py
ssez/download_viirs_ssez.py
ssez/check_quality.py

# 3. Analyse each node
shv/analyze_shv.py
gl/analyze_gl.py
gl/merge_ntl_s2_gl.py
ssez/analyze_ssez.py

# 4. Generate outputs
shv/plot_shv.py
gl/make_stage_tables_gl.py
gl/plot_gl.py
gl/plot_ntl_vs_s2_gl.py
ssez/plot_ssez.py

# 5. Cross-node comparison
integrated/compare_vitality.py
integrated/make_integrated_tables.py
```

---

## Citation

If you use this code, please cite:

```
Li, Y. "Functional Zone Divergence Under Successive Policy Shocks in a Rapidly Urbanizing
Coastal City: Evidence from Multi-Node Nighttime-Light Monitoring, Sihanoukville, Cambodia
(2014–2026)." Journal of Urban Planning and Development (submitted).
```

Scripts will be archived on Zenodo upon formal acceptance.

---

## License

MIT License. See `LICENSE` for details.
