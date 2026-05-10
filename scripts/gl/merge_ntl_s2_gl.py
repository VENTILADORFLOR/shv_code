import pandas as pd
from pathlib import Path

# =========================================================
# 1. Input and output paths
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

S2_FILE  = PROJECT_ROOT / "outputs" / "gl" / "sentinel_indices" / "gl_s2_indices_monthly.csv"
NTL_FILE = PROJECT_ROOT / "outputs" / "gl" / "stats" / "gl_boundary_stats.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "merged"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "gl_merged_ntl_s2.csv"

# =========================================================
# 2. Load data
# =========================================================
df_s2  = pd.read_csv(S2_FILE)
df_ntl = pd.read_csv(NTL_FILE)

print("S2 column names:",   df_s2.columns.tolist())
print("NTL column names:", df_ntl.columns.tolist())

# =========================================================
# 3. Date handling: align all dates to month start
# =========================================================
for df_, name in [(df_s2, "S2"), (df_ntl, "NTL")]:
    if "date" not in df_.columns:
        raise ValueError(f"{name} file does not contain a 'date' column.")

df_s2["date"]  = pd.to_datetime(df_s2["date"]).dt.to_period("M").dt.to_timestamp()
df_ntl["date"] = pd.to_datetime(df_ntl["date"]).dt.to_period("M").dt.to_timestamp()

# =========================================================
# 4. Select key NTL fields
#    is_low_cvg / avg_cvg / Mean_interp / stage are fields introduced in the analysis stage
# =========================================================
ntl_keep_candidates = [
    "date",
    "Intensity_Mean",
    "SOL_Sum",
    "Mean_raw",
    "Sum_raw",
    "avg_cvg",
    "is_cloud_gap",
    "is_low_cvg",
    "Mean_interp",
    "STL_Trend",
    "STL_Seasonal",
    "STL_Resid",
    "YoY_pct",
    "Index_2017",
    "stage",
    "year",
    "month",
    "is_monsoon",
]

ntl_keep    = [c for c in ntl_keep_candidates if c in df_ntl.columns]
df_ntl_sub  = df_ntl[ntl_keep].copy()

# =========================================================
# 5. Select key S2 fields
#    is_low_quality is a field introduced by the Sentinel-2 download script
#    year/month/is_monsoon are retained from the NTL side and not duplicated from S2
# =========================================================
s2_keep_candidates = [
    "date",
    "image_count",
    "NDVI_mean",
    "NDBI_mean",
    "NDVI_interp",
    "NDBI_interp",
    "is_empty_month",
    "is_low_quality",
]

s2_keep    = [c for c in s2_keep_candidates if c in df_s2.columns]
df_s2_sub  = df_s2[s2_keep].copy()

# =========================================================
# 6. Merge
# =========================================================
df_merge = pd.merge(
    df_ntl_sub,
    df_s2_sub,
    on="date",
    how="outer",
    sort=True,
)

# =========================================================
# 7. Common-period flag
#    common_period: both NTL and S2 have data and pass quality thresholds
# =========================================================
df_merge["has_ntl"]  = df_merge["Intensity_Mean"].notna() if "Intensity_Mean" in df_merge.columns else False
df_merge["has_ndvi"] = df_merge["NDVI_mean"].notna()      if "NDVI_mean"       in df_merge.columns else False
df_merge["has_ndbi"] = df_merge["NDBI_mean"].notna()      if "NDBI_mean"       in df_merge.columns else False

# Quality criterion: NTL not low-quality AND S2 not low-quality
ntl_ok = ~df_merge["is_low_cvg"].fillna(False)     if "is_low_cvg"     in df_merge.columns else True
s2_ok  = ~df_merge["is_low_quality"].fillna(False) if "is_low_quality" in df_merge.columns else True

df_merge["common_period"] = (
    df_merge["has_ntl"] &
    df_merge["has_ndvi"] &
    ntl_ok &
    s2_ok
)

common_df = df_merge[df_merge["common_period"]].copy()

# =========================================================
# 8. Export
# =========================================================
df_merge.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n========== Merge complete ==========")
print(f"Output file: {OUTPUT_FILE}")
print(f"Total rows: {len(df_merge)}")

if len(common_df) > 0:
    print(f"High-quality common-period rows: {len(common_df)}")
    print(f"Common date range: {common_df['date'].min().date()} ~ {common_df['date'].max().date()}")
else:
    print("No high-quality common period found. Please check date format or data quality flags.")

print("\nMerged column names:")
print(df_merge.columns.tolist())

print("\nLast 12 rows preview:")
print(df_merge.tail(12).to_string(index=False))
