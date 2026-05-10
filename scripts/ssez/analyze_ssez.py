import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.seasonal import STL

# =========================================================
# 1. Paths
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "ssez" / "gee" / "ssez_viirs_monthly_raw.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ssez" / "stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "ssez_boundary_stats.csv"

# =========================================================
# 2. Load data
# =========================================================
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])

# Force alignment to month start to fix occasional non-standard GEE timestamps (e.g. 2024-06-04)
df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

df = df.sort_values("date").reset_index(drop=True)

required_cols = ["date", "SOL_Sum", "Intensity_Mean", "is_low_cvg", "is_cloud_gap"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Input CSV is missing required columns: {missing_cols}")

# =========================================================
# 3. Temporal fields
# =========================================================
df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

# =========================================================
# 4. Data cleaning
#    is_low_cvg is read directly from the download script; no need to recompute
#    Low-quality months and missing values are both set to NaN before interpolation
# =========================================================
df["SOL_Sum_raw"]        = df["SOL_Sum"].copy()
df["Intensity_Mean_raw"] = df["Intensity_Mean"].copy()

df.loc[df["is_low_cvg"], "SOL_Sum"]        = np.nan
df.loc[df["is_low_cvg"], "Intensity_Mean"] = np.nan

# Statistics: is_cloud_gap is the reference count for missing observations
cloud_gap_count = int(df["is_cloud_gap"].sum())
monsoon_gap     = int(df.loc[df["is_cloud_gap"] & df["is_monsoon"], "date"].count())
low_cvg_total   = int(df["is_low_cvg"].sum())

# Log low-quality observation months to console
print("\n--- Low-quality observation months (avg_cvg < 1) ---")
print(df[df["is_low_cvg"]][["date", "SOL_Sum_raw", "avg_cvg", "is_monsoon"]])
print("-" * 40)

# =========================================================
# 5. Interpolation (for STL decomposition only)
# =========================================================
df["SOL_Sum_interp"]        = df["SOL_Sum"].interpolate(
    method="linear", limit_direction="both"
)
df["Intensity_Mean_interp"] = df["Intensity_Mean"].interpolate(
    method="linear", limit_direction="both"
)

# =========================================================
# 6. STL decomposition (main metric: SOL_Sum)
# =========================================================
stl_result = STL(df["SOL_Sum_interp"], period=12, robust=True).fit()

df["STL_Trend"]    = stl_result.trend
df["STL_Seasonal"] = stl_result.seasonal
df["STL_Resid"]    = stl_result.resid

df["YoY_pct"] = df["STL_Trend"].pct_change(12) * 100

# =========================================================
# 7. Normalized index (2017 = 100)
# =========================================================
base_mask = (df["date"] >= "2017-01-01") & (df["date"] <= "2017-12-31")
base_val  = df.loc[base_mask, "STL_Trend"].mean()

if pd.isna(base_val) or base_val == 0:
    raise ValueError("2017 base-period mean is invalid; cannot compute Index_2017.")

df["Index_2017"] = df["STL_Trend"] / base_val * 100

# =========================================================
# 8. Stage labels
#    Industrial Expansion extended to 2025-10-14, covering all months in 2025
# =========================================================
def assign_stage(dt):
    if pd.Timestamp("2014-01-01") <= dt <= pd.Timestamp("2016-12-31"):
        return "Pre-development"
    elif pd.Timestamp("2017-01-01") <= dt <= pd.Timestamp("2019-08-17"):
        return "Gambling Boom"
    elif pd.Timestamp("2019-08-18") <= dt <= pd.Timestamp("2021-06-30"):
        return "Post-818 Trough"
    elif pd.Timestamp("2021-07-01") <= dt <= pd.Timestamp("2025-10-14"):
        return "Industrial Expansion"
    elif pd.Timestamp("2025-10-15") <= dt <= pd.Timestamp("2026-03-31"):
        return "Post-sanctions"
    else:
        return "Other"

df["stage"] = df["date"].apply(assign_stage)

# =========================================================
# 9. Key statistics
#    Note: the SSEZ STL trend shows no distinct trough after 818 (industrial zone continuously expanding);
#    post818_trough_val is merely the minimum within the window and carries no economic interpretation;
#    the field is retained for output completeness; it is not used in the manuscript
# =========================================================
pre818 = df[
    (df["date"] >= "2019-02-01") &
    (df["date"] <= "2019-08-17")
]["STL_Trend"].mean()

trough_mask = (df["date"] >= "2019-08-18") & (df["date"] <= "2021-12-31")
trough_val  = df.loc[trough_mask, "STL_Trend"].min()
trough_dt   = df.loc[df.loc[trough_mask, "STL_Trend"].idxmin(), "date"]

df["base_2017_mean"]      = base_val
df["pre818_mean"]         = pre818
# The following two columns are for reference only; the SSEZ trend is monotonically increasing and the trough has no economic interpretation
df["post818_trough_val"]  = trough_val
df["post818_trough_date"] = trough_dt.strftime("%Y-%m")

# =========================================================
# 10. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# =========================================================
# 11. Console output
# =========================================================
print("\n========== SSEZ analysis complete ==========")
print(f"Input file: {INPUT_CSV}")
print(f"Output file: {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows: {len(df)}")
print(f"Fully missing months (is_cloud_gap): {cloud_gap_count}")
print(f"    of which monsoon months: {monsoon_gap}")
print(f"Low-quality months (avg_cvg < 1, including missing): {low_cvg_total}")
print(f"2017 base-period mean: {base_val:.2f}")
print(f"Pre-818 mean (2019-02 to 2019-08): {pre818:.2f}")
print(
    f"Lowest value in post-818 window: {trough_val:.2f} @ {trough_dt.strftime('%Y-%m')}"
    f"  ← This is only the window minimum; the SSEZ trend is monotonically increasing and carries no trough interpretation"
)

print("\nStage means (based on STL_Trend):")
stage_order = [
    "Pre-development", "Gambling Boom", "Post-818 Trough",
    "Industrial Expansion", "Post-sanctions", "Other"
]
stage_summary = (
    df.groupby("stage", dropna=False)["STL_Trend"]
    .mean()
    .reindex(stage_order)
    .dropna()
    .reset_index()
)
print(stage_summary.to_string(index=False))
