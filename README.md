# Multi-Node Nighttime Light (NTL) Analysis Pipeline

A Python pipeline for extracting, processing, and comparing VIIRS/DNB monthly nighttime-light time series across multiple spatially fixed regions of interest (ROIs), with Sentinel-2 built-environment cross-validation and STL-based trend decomposition.

---

## Overview

This pipeline monitors spatially heterogeneous urban economic activity using satellite-derived nighttime-light radiance. Three nodes are analysed in parallel:

| Node | Abbreviation | Area | NTL Metric | Description |
|---|---|---|---|---| 
| Golden Lions roundabout buffer | GL | 2.94 km² | Intensity Mean | Dense commercial service node; 1 km circular buffer, sea surface clipped |
| Sihanoukville Special Economic Zone | SSEZ | 9.30 km² | SOL Sum | Formal industrial zone; manually digitised boundary |
| Preah Sihanouk Province | SHV | 1,605 km² | SOL Sum | Administrative macro-scale baseline; FAO GAUL 2015 level-1 |

Each node maintains a fixed boundary over the full 147-month analysis window (January 2014–March 2026). The pipeline produces STL-decomposed trend series, normalised indices (2017 = 100), year-on-year (YoY) growth rates, policy shock metrics, and cross-node comparison outputs.

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

Install:

```bash
pip install earthengine-api geopandas rasterio pandas numpy statsmodels matplotlib scipy
earthengine authenticate
```

A [Google Earth Engine](https://earthengine.google.com/) account is required to run the download scripts.

---

## Repository Structure

```
scripts/
├── gl/                               # Golden Lions commercial service node
│   ├── make_gl_point_buffer.py       # Build 1 km circular ROI from roundabout centroid; clip sea surface via MODIS water mask
│   ├── download_viirs_gl.py          # GEE: extract monthly VIIRS/DNB Intensity Mean (VCMSLCFG) for GL ROI
│   ├── download_s2_indices_gl.py     # GEE: extract monthly Sentinel-2 NDBI and NDVI for GL ROI
│   ├── analyze_gl.py                 # QA filtering → linear interpolation → STL decomposition → Index (2017=100) → YoY rates
│   ├── merge_ntl_s2_gl.py            # Merge NTL and Sentinel-2 time series; flag common-period cross-validation months
│   ├── make_stage_tables_gl.py       # Compute per-phase descriptive statistics (mean, median, SD) for GL
│   ├── plot_gl.py                    # Three-panel figure: raw scatter + STL trend / normalised index / YoY growth rate
│   └── plot_ntl_vs_s2_gl.py          # NTL–NDBI/NDVI correlation plots; NTL/NDBI ratio time series; phase-stratified analysis
│
├── ssez/                             # Sihanoukville Special Economic Zone
│   ├── download_viirs_ssez.py        # GEE: extract monthly VIIRS/DNB SOL Sum for SSEZ boundary
│   ├── check_quality.py              # QA audit: flag low-coverage months (avg_cvg < 1) and monsoon cloud gaps for SSEZ
│   ├── analyze_ssez.py               # Interpolation → STL decomposition → Index → YoY rates → shock response metrics
│   └── plot_ssez.py                  # Three-panel figure: raw SOL scatter + trend / index / YoY growth rate
│
├── shv/                              # Preah Sihanouk Province administrative baseline
│   ├── make_shv_roi.py               # GEE: extract provincial boundary from FAO GAUL 2015 level-1
│   ├── download_viirs_shv.py         # GEE: extract monthly VIIRS/DNB SOL Sum for provincial ROI; apply MODIS land mask
│   ├── analyze_shv.py                # Interpolation → STL decomposition → Index → YoY rates
│   └── plot_shv.py                   # Two-panel figure: SOL trend + STL decomposition
│
└── integrated/                       # Cross-node comparison
    ├── compare_vitality.py           # Merge three-node series; compute YoY Pearson correlations (full period + per phase);
    │                                 # 818 shock and sanctions window response metrics; divergence visualisation
    └── make_integrated_tables.py     # Generate four summary CSV tables (phase averages, YoY correlations,
                                      # policy shock comparison, sanctions early-signal response)
```

---

## Data Sources

| Dataset | GEE Collection ID | Resolution | Coverage |
|---|---|---|---|
| VIIRS/DNB Monthly Stray-Light Corrected | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` | 500 m | Jan 2014–Mar 2026 |
| Sentinel-2 SR Harmonised | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Jul 2015–Mar 2026 |
| FAO GAUL 2015 Administrative Level 1 | `FAO/GAUL/2015/level1` | vector | — |
| MODIS MOD44W Annual Water Mask | `MODIS/006/MOD44W` | 250 m | 2015 |

---

## Processing Logic

### 1. Cloud-Gap Handling

Months with mean pixel coverage `avg_cvg < 1` are flagged as `is_low_cvg`; months with `avg_rad ≤ 0` after masking are flagged as `is_cloud_gap`. Both sets are set to `NaN` before STL input and replaced by linear interpolation (`limit_direction='both'`). At GL, 23 of 147 months (15.6%) are cloud-gap months, all falling within the May–October monsoon season.

### 2. STL Decomposition

STL (Cleveland et al. 1990) is applied with `period=12, robust=True` to separate each series into trend, seasonal, and residual components. The robust option down-weights cloud-contaminated residuals. All indices, YoY rates, and cross-node comparisons use the STL trend component.

### 3. Normalised Index

Each STL trend series is divided by the mean trend across calendar year 2017 and multiplied by 100 (`Index_2017`). Year 2017 is used as the common base year: post-sensor-calibration, pre-shock, and valid across all three nodes.

### 4. Sentinel-2 Cross-Validation (GL only)

Two tests assess whether GL luminosity growth is activity-driven or infrastructure-driven:

- **Baseline audit** — non-cloud-gap Intensity Mean values are compared between the pre-development period (2014–2016) and the post-818 trough period (Mar 2020–Jun 2021) to quantify infrastructure-elevated baseline; the pre-818 peak is compared to the trough to assess the activity-driven component above that baseline.
- **NDBI/NDVI correlation** — Pearson correlations between the STL trend and monthly NDBI/NDVI are computed over the full period and per policy phase. Low NDBI absolute values and weak NTL–NDBI coupling indicate activity-driven rather than construction-driven luminosity change.

### 5. Policy Phase Definitions

| Phase | Date Range |
|---|---|
| Pre-development | 2014-01-01 – 2016-12-31 |
| Gambling Boom | 2017-01-01 – 2019-08-17 |
| Post-818 | 2019-08-18 – 2021-06-30 |
| Expansion | 2021-07-01 – 2025-10-14 |
| Post-sanctions | 2025-10-15 – 2026-03-31 |

---

## Output Files

### Per-Node Statistics (`outputs/<node>/stats/`)

| File | Contents |
|---|---|
| `gl_boundary_stats.csv` | Monthly GL series: raw, interpolated, STL components, Index_2017, YoY_pct, stage label |
| `gl_merged_ntl_s2.csv` | GL NTL + Sentinel-2 merged; cross-validation flags (`common_period`, `has_ntl`, `has_ndvi`) |
| `gl_stage_stats.csv` | Per-phase descriptive statistics (mean, median, SD) for all GL metrics |
| `gl_stage_changes.csv` | Absolute and percentage changes between consecutive phases |
| `ssez_boundary_stats.csv` | Monthly SSEZ series: raw, interpolated, STL components, Index_2017, YoY_pct, stage label |
| `shv_boundary_stats.csv` | Monthly provincial series: raw, interpolated, STL components, Index_2017, YoY_pct |

### Cross-Node Outputs (`outputs/integrated/stats/`)

| File | Contents |
|---|---|
| `comparison_merged.csv` | Aligned three-node monthly table: STL trend, Index_2017, YoY_pct for GL / SSEZ / SHV |
| `table1_stage_means.csv` | Phase-average Index_2017 (mean, median, SD, N) for all three nodes |
| `table2_yoy_correlation.csv` | Pearson r, p-value, significance, n — full period + per phase, all node pairs |
| `table3_policy_shock.csv` | 818 shock metrics: pre-818 mean, post-818 trough value/date, trough drop (%), post-818 avg change (%) |
| `table4_sanctions_response.csv` | Sanctions window (Oct 2025–Mar 2026): pre/post index means, change (%), latest YoY |

### Figures (`outputs/<node>/figures/`, `outputs/integrated/figures/`)

| File | Contents |
|---|---|
| `gl_main.png` | GL three-panel: raw + STL trend / Index / YoY |
| `gl_stl_decomp.png` | GL STL four-panel decomposition |
| `gl_lighting_audit.png` | Activity vs infrastructure baseline audit |
| `gl_ntl_ndvi_ndbi_v2.png` | NTL–NDBI/NDVI cross-validation panel |
| `ssez_main.png` | SSEZ three-panel: raw + STL trend / Index / YoY |
| `ssez_stl_decomp.png` | SSEZ STL decomposition |
| `shv_main.png` | Provincial three-panel |
| `shv_stl_decomp.png` | Provincial STL decomposition |
| `comparison_vitality_main.png` | Three-node index overlay + YoY comparison + shock response bar chart |
| `comparison_structural_divergence.png` | Phase-average grouped bar chart + GL↔SSEZ YoY scatter |

---

## Suggested Run Order

```bash
# Step 1 — Define ROIs
python scripts/shv/make_shv_roi.py
python scripts/gl/make_gl_point_buffer.py

# Step 2 — Download satellite data (requires GEE authentication)
python scripts/shv/download_viirs_shv.py
python scripts/gl/download_viirs_gl.py
python scripts/gl/download_s2_indices_gl.py
python scripts/ssez/download_viirs_ssez.py
python scripts/ssez/check_quality.py

# Step 3 — Analyse each node
python scripts/shv/analyze_shv.py
python scripts/gl/analyze_gl.py
python scripts/gl/merge_ntl_s2_gl.py
python scripts/ssez/analyze_ssez.py

# Step 4 — Per-node outputs
python scripts/shv/plot_shv.py
python scripts/gl/make_stage_tables_gl.py
python scripts/gl/plot_gl.py
python scripts/gl/plot_ntl_vs_s2_gl.py
python scripts/ssez/plot_ssez.py

# Step 5 — Cross-node comparison
python scripts/integrated/compare_vitality.py
python scripts/integrated/make_integrated_tables.py
```

---

## Notes

- **STL end-of-series instability**: seasonal amplitude and trend estimates for the most recent 12–18 months carry elevated uncertainty due to STL boundary effects, particularly pronounced in the provincial series. Late-period results should be treated as indicative.
- **NDBI cross-validation sample**: 47 months with concurrent valid NTL and high-quality Sentinel-2 observations (Dec 2018–Mar 2026) form the cross-validation window. Phase-stratified correlations use subsets of this sample.
- **Coordinate system**: GL buffer generated in UTM Zone 48N (EPSG:32648); all GEE operations use native VIIRS/Sentinel-2 projections.
- **Water masking**: GL ROI clips sea surface via MODIS MOD44W (2015 reference); SHV provincial boundary applies the same mask to exclude coastal sea pixels from SOL Sum aggregation.

---

## License

MIT License. See `LICENSE` for details.
