import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.seasonal import STL

# =========================================================
# 1. Path configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "gl" / "gee" / "gl_viirs_monthly_raw.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "gl_boundary_stats.csv"

# =========================================================
# 2. Load data
# =========================================================
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

required_cols = ["date", "Intensity_Mean", "SOL_Sum", "is_low_cvg", "is_cloud_gap"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Input CSV is missing required columns: {missing_cols}")

# =========================================================
# 3. Basic temporal fields
# =========================================================
df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

# =========================================================
# 4. Quality filtering: use is_low_cvg flags set by the download script
#    is_low_cvg (avg_cvg < 1) is a superset of is_cloud_gap (NaN);
#    both are set to NaN before interpolation to exclude cloud-contaminated months from STL
# =========================================================
df["Mean_raw"] = df["Intensity_Mean"].copy()
df["Sum_raw"]  = df["SOL_Sum"].copy()

df.loc[df["is_low_cvg"], "Intensity_Mean"] = np.nan
df.loc[df["is_low_cvg"], "SOL_Sum"]        = np.nan

# Statistics: is_cloud_gap is the reference count for missing observations; monsoon subset uses the same reference
cloud_n   = int(df["is_cloud_gap"].sum())
monsoon_n = int(df.loc[df["is_cloud_gap"] & df["is_monsoon"], "date"].count())
low_q_total = int(df["is_low_cvg"].sum())

# =========================================================
# 5. Linear interpolation (preparation for STL decomposition)
# =========================================================
df["Mean_interp"] = df["Intensity_Mean"].interpolate(method="linear", limit_direction="both")
df["Sum_interp"]  = df["SOL_Sum"].interpolate(method="linear", limit_direction="both")

# =========================================================
# 6. STL decomposition (main metric: Mean)
# =========================================================
stl_res = STL(df["Mean_interp"], period=12, robust=True).fit()

df["STL_Trend"]    = stl_res.trend
df["STL_Seasonal"] = stl_res.seasonal
df["STL_Resid"]    = stl_res.resid

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
# 8. Key stage statistics (based on raw values, excluding missing observations)
# =========================================================
trough_periods = {
    "2014": ("2014-01-01", "2014-12-31"),
    "2015": ("2015-01-01", "2015-12-31"),
    "2016": ("2016-01-01", "2016-12-31"),
    "2020": ("2020-03-01", "2020-12-31"),
    "2021": ("2021-01-01", "2021-06-30"),
}

trough_means = {}
for yr, (s, e) in trough_periods.items():
    sub = df[
        (df["date"] >= s) &
        (df["date"] <= e) &
        (~df["is_cloud_gap"])
    ]["Mean_raw"]
    trough_means[yr] = sub.mean()

base_2014_16 = np.mean([
    trough_means["2014"],
    trough_means["2015"],
    trough_means["2016"],
])

base_2020_21 = np.mean([
    trough_means["2020"],
    trough_means["2021"],
])

pre818 = df[
    (df["date"] >= "2019-06-01") &
    (df["date"] <= "2019-08-31") &
    (~df["is_cloud_gap"])
]["Mean_raw"].mean()

trough_818 = df[
    (df["date"] >= "2020-01-01") &
    (df["date"] <= "2021-06-30") &
    (~df["is_cloud_gap"])
]["Mean_raw"].mean()

df["base_2017_mean"]      = base_val
df["baseline_2014_16"]    = base_2014_16
df["baseline_2020_21"]    = base_2020_21
df["pre818_mean"]         = pre818
df["post818_trough_mean"] = trough_818

# =========================================================
# 9. Stage labels
#    Second Boom extended to 2025-10-14, covering all months in 2025
#    Prevents 2025-01 to 2025-10-14 from falling into 'Other'
# =========================================================
def assign_stage(dt):
    if pd.Timestamp("2014-01-01") <= dt <= pd.Timestamp("2016-12-31"):
        return "Pre-development"
    elif pd.Timestamp("2017-01-01") <= dt <= pd.Timestamp("2019-08-17"):
        return "Gambling Boom"
    elif pd.Timestamp("2019-08-18") <= dt <= pd.Timestamp("2021-06-30"):
        return "Post-818 Trough"
    elif pd.Timestamp("2021-07-01") <= dt <= pd.Timestamp("2025-10-14"):
        return "Second Boom"
    elif pd.Timestamp("2025-10-15") <= dt <= pd.Timestamp("2026-03-31"):
        return "Post-sanctions"
    else:
        return "Other"

df["stage"] = df["date"].apply(assign_stage)

# =========================================================
# 10. Export
# =========================================================
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# =========================================================
# 11. Console summary
# =========================================================
print("\n========== GL analysis complete ==========")
print(f"Input file: {INPUT_CSV}")
print(f"Output file: {OUTPUT_CSV}")
print(f"Date range: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"Total rows: {len(df)}")
print(f"Fully missing months (is_cloud_gap): {cloud_n}")
print(f"    of which monsoon months: {monsoon_n}")
print(f"Low-quality months (avg_cvg < 1, including missing): {low_q_total}")
print(f"2017 base-period mean (STL Trend): {base_val:.2f}")
print(f"2014-2016 baseline mean (Mean_raw): {base_2014_16:.2f}")
print(f"2019-06 to 2019-08 peak mean (Mean_raw): {pre818:.2f}")
print(f"2020-01 to 2021-06 trough mean (Mean_raw): {trough_818:.2f}")
print(f"2020-2021 trough mean (Mean_raw): {base_2020_21:.2f}")

print("\nStage means (based on STL_Trend):")
stage_order = [
    "Pre-development", "Gambling Boom", "Post-818 Trough",
    "Second Boom", "Post-sanctions", "Other"
]
stage_summary = (
    df.groupby("stage", dropna=False)["STL_Trend"]
    .mean()
    .reindex(stage_order)
    .dropna()
    .reset_index()
)
print(stage_summary.to_string(index=False))
