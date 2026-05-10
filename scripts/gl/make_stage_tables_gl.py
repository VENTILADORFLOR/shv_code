import pandas as pd
import numpy as np
from pathlib import Path

# =========================================================
# 1. File paths
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "outputs" / "gl" / "merged" / "gl_merged_ntl_s2.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_STAGE_MEAN  = OUTPUT_DIR / "gl_stage_stats.csv"
OUT_STAGE_DELTA = OUTPUT_DIR / "gl_stage_changes.csv"

# =========================================================
# 2. Load data
# =========================================================
df = pd.read_csv(INPUT_FILE)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

# is_low_quality may be read as object type from CSV; cast to bool
df["is_low_quality"] = df["is_low_quality"].map(
    {True: True, False: False, "True": True, "False": False}
).fillna(True).astype(bool)

# =========================================================
# 3. Two sample sets
#    df_ntl: full period, used for nighttime light statistics (includes interpolated months)
#    df_s2: Sentinel-2 high-quality months, used for NDVI/NDBI statistics
#           Uses is_low_quality==False, consistent with the common_period logic
#           image_count>0 is not used because months with image_count=1 are already flagged as low-quality
# =========================================================
df_ntl = df.copy()
df_s2  = df[(df["is_low_quality"] == False) & (df["date"] >= "2017-02-01")].copy()

print(f"NTL full-period sample count: {len(df_ntl)}")
print(f"S2 high-quality sample count:  {len(df_s2)}")
print(f"S2 Date range:      {df_s2['date'].min().date()} ~ {df_s2['date'].max().date()}")

# =========================================================
# 4. Stage definitions
#    Exactly consistent with the assign_stage function in analyze_gl.py
#    Second Boom extended to 2025-10-14, covering all months in 2025
# =========================================================
stages = [
    ("Gambling_Boom",  "2017-01-01", "2019-08-17"),
    ("Post_818",       "2019-08-18", "2021-06-30"),
    ("Second_Boom",    "2021-07-01", "2025-10-14"),
    ("Post_sanctions", "2025-10-15", "2026-03-31"),
]

# =========================================================
# 5. Stage means, medians, and standard deviations
# =========================================================
ntl_cols = ["STL_Trend", "Intensity_Mean", "SOL_Sum", "Index_2017", "YoY_pct"]
s2_cols  = ["NDVI_mean", "NDBI_mean", "NDVI_interp", "NDBI_interp"]

rows = []

for name, s, e in stages:
    sub_ntl = df_ntl[(df_ntl["date"] >= s) & (df_ntl["date"] <= e)].copy()
    sub_s2  = df_s2[ (df_s2["date"]  >= s) & (df_s2["date"]  <= e)].copy()

    row = {
        "Stage":  name,
        "Start":  s,
        "End":    e,
        "N_ntl":  len(sub_ntl),
        "N_s2":   len(sub_s2),
    }

    for col in ntl_cols:
        if col in sub_ntl.columns:
            row[f"{col}_mean"]   = sub_ntl[col].mean()
            row[f"{col}_median"] = sub_ntl[col].median()
            row[f"{col}_std"]    = sub_ntl[col].std()

    for col in s2_cols:
        if col in sub_s2.columns:
            row[f"{col}_mean"]   = sub_s2[col].mean()
            row[f"{col}_median"] = sub_s2[col].median()
            row[f"{col}_std"]    = sub_s2[col].std()

    rows.append(row)

stage_stats = pd.DataFrame(rows)
stage_stats.to_csv(OUT_STAGE_MEAN, index=False, encoding="utf-8-sig")

print("\n========== Stage statistics ==========")
print(stage_stats.to_string(index=False))

# =========================================================
# 6. Inter-stage changes (each stage vs the preceding one)
# =========================================================
compare_cols = [
    "STL_Trend_mean",
    "Intensity_Mean_mean",
    "SOL_Sum_mean",
    "Index_2017_mean",
    "NDVI_mean_mean",
    "NDBI_mean_mean",
    "NDVI_interp_mean",
    "NDBI_interp_mean",
]

change_rows = []

for i in range(1, len(stage_stats)):
    prev_row = stage_stats.iloc[i - 1]
    curr_row = stage_stats.iloc[i]

    out = {
        "From_Stage": prev_row["Stage"],
        "To_Stage":   curr_row["Stage"],
    }

    for col in compare_cols:
        if col not in stage_stats.columns:
            continue
        prev_val = prev_row[col]
        curr_val = curr_row[col]

        if pd.notna(prev_val) and pd.notna(curr_val):
            out[f"{col}_abs_change"] = curr_val - prev_val
            out[f"{col}_pct_change"] = (
                (curr_val - prev_val) / abs(prev_val) * 100
                if prev_val != 0 else np.nan
            )
        else:
            out[f"{col}_abs_change"] = np.nan
            out[f"{col}_pct_change"] = np.nan

    change_rows.append(out)

stage_changes = pd.DataFrame(change_rows)
stage_changes.to_csv(OUT_STAGE_DELTA, index=False, encoding="utf-8-sig")

print("\n========== Stage changes ==========")
print(stage_changes.to_string(index=False))

# =========================================================
# 7. Console summary (paper citation format)
# =========================================================
print("\n========== Paper citation summary ==========")
for _, row in stage_stats.iterrows():
    print(f"\n[{row['Stage']}] ({row['Start']} ~ {row['End']})")
    print(f"  NTL STL Trend mean:  {row.get('STL_Trend_mean', np.nan):.2f}")
    print(f"  Index_2017 mean:     {row.get('Index_2017_mean', np.nan):.1f}")
    ntl_n  = int(row["N_ntl"])
    s2_n   = int(row["N_s2"])
    print(f"  NTL month count: {ntl_n}  |  S2 high-quality month count: {s2_n}")
    if s2_n > 0:
        print(f"  NDBI mean: {row.get('NDBI_mean_mean', np.nan):.4f}  "
              f"NDVI mean: {row.get('NDVI_mean_mean', np.nan):.4f}")

print("\n========== Output complete ==========")
print(f"Stage statistics table: {OUT_STAGE_MEAN}")
print(f"Stage change table: {OUT_STAGE_DELTA}")
