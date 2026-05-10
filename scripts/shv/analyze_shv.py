import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.seasonal import STL

# =========================================================
# 1. Paths
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "shv" / "gee" / "shv_viirs_monthly_raw.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shv" / "stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "shv_boundary_stats.csv"

# =========================================================
# 2. Load data
# =========================================================
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

required_cols = ["date", "SOL"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Input CSV is missing required columns: {missing_cols}")

# =========================================================
# 3. Temporal fields
# =========================================================
df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

# =========================================================
# 4. Data cleaning
# =========================================================
df["SOL_raw"] = df["SOL"].copy()
df.loc[df["SOL"] <= 0, "SOL"] = np.nan

# avg_cvg is the observation count; < 1 means fewer than one cloud-free observation per pixel on average in that month
df["is_low_cvg"] = df["avg_cvg"] < 1

# Flag only genuine NaN; do not conflate with true zero values
df["is_cloud_gap"] = df["SOL_raw"].isna()

# Log low-quality observation months to console
print("\n--- Low-quality observation months (avg_cvg < 1) ---")
print(df[df["avg_cvg"] < 1][["date", "SOL", "avg_cvg", "is_monsoon"]])
print("-" * 40)

cloud_gap_count = int(df["is_cloud_gap"].sum())
monsoon_gap = int(df.loc[df["is_cloud_gap"], "month"].isin([5, 6, 7, 8, 9, 10]).sum())

# =========================================================
# 5. Interpolation (for STL decomposition only)
#    Low-quality months and genuine missing values are set to NaN, then linearly interpolated
# =========================================================
sol_for_stl = df["SOL"].copy().astype(float)
sol_for_stl[df["is_low_cvg"]] = np.nan
df["SOL_interp"] = sol_for_stl.interpolate(method="linear", limit_direction="both")

# =========================================================
# 6. STL decomposition
# =========================================================
stl_res = STL(df["SOL_interp"], period=12, robust=True).fit()

df["STL_Trend"]    = stl_res.trend
df["STL_Seasonal"] = stl_res.seasonal
df["STL_Resid"]    = stl_res.resid

# =========================================================
# 7. Normalized index and YoY
# =========================================================
base_mask = (df["date"] >= "2017-01-01") & (df["date"] <= "2017-12-31")
base_val  = df.loc[base_mask, "STL_Trend"].mean()

if pd.isna(base_val) or base_val == 0:
    raise ValueError("2017 base-period mean is invalid; cannot compute Index_2017.")

df["Index_2017"] = df["STL_Trend"] / base_val * 100
df["YoY_pct"]    = df["STL_Trend"].pct_change(12) * 100

# =========================================================
# 8. Stage labels
#    Note: Industrial Expansion extended to 2025-10-14, covering the full period
# =========================================================
def assign_stage(dt):
    if pd.Timestamp("2014-01-01") <= dt <= pd.Timestamp("2016-12-31"):
        return "Pre-development"
    elif pd.Timestamp("2017-01-01") <= dt <= pd.Timestamp("2019-08-17"):
        return "Gambling Boom"
    elif pd.Timestamp("2019-08-18") <= dt <= pd.Timestamp("2021-06-30"):
        return "Post-818"
    elif pd.Timestamp("2021-07-01") <= dt <= pd.Timestamp("2025-10-14"):
        return "Industrial Expansion"
    elif pd.Timestamp("2025-10-15") <= dt <= pd.Timestamp("2026-03-31"):
        return "Post-sanctions"
    else:
        return "Other"

df["stage"] = df["date"].apply(assign_stage)

# =========================================================
# 9. Key stage statistics
#    Note: the provincial STL trend shows no distinct trough after 818 (monotonically increasing throughout);
#    trough metrics are therefore omitted to avoid misleading statistics.
# =========================================================
pre818 = df[
    (df["date"] >= "2019-02-01") &
    (df["date"] <= "2019-08-17")
]["STL_Trend"].mean()

df["base_2017_mean"] = base_val
df["pre818_mean"]    = pre818

# =========================================================
# 10. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# =========================================================
# 11. Console output
# =========================================================
print("\n========== SHV analysis complete ==========")
print(f"Input file: {INPUT_CSV}")
print(f"Output file: {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows: {len(df)}")
print(f"Genuinely missing months (NaN): {cloud_gap_count}")
print(f"    of which monsoon months: {monsoon_gap}")
print(f"Low-quality observation months (avg_cvg < 1): {int(df['is_low_cvg'].sum())}")
print(f"2017 base-period mean: {base_val:.2f}")
print(f"Pre-818 mean (2019-02 to 2019-08): {pre818:.2f}")

print("\nStage means (based on STL_Trend):")
stage_order = [
    "Pre-development", "Gambling Boom", "Post-818",
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
