import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

# =========================================================
# 1. Path configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

MERGED_FILE = PROJECT_ROOT / "outputs" / "integrated" / "stats" / "comparison_merged.csv"

GL_FILE   = PROJECT_ROOT / "outputs" / "gl"   / "stats" / "gl_boundary_stats.csv"
SSEZ_FILE = PROJECT_ROOT / "outputs" / "ssez" / "stats" / "ssez_boundary_stats.csv"
SHV_FILE  = PROJECT_ROOT / "outputs" / "shv"  / "stats" / "shv_boundary_stats.csv"

OUT_DIR = PROJECT_ROOT / "outputs" / "integrated" / "stats"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_T1 = OUT_DIR / "table1_stage_means.csv"
OUT_T2 = OUT_DIR / "table2_yoy_correlation.csv"
OUT_T3 = OUT_DIR / "table3_policy_shock.csv"
OUT_T4 = OUT_DIR / "table4_sanctions_response.csv"

# =========================================================
# 2. Load data
# =========================================================
def load(path):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df.sort_values("date").reset_index(drop=True)

df = load(MERGED_FILE)

# Individual node statistics files (used to supplement metadata such as is_low_cvg)
gl   = load(GL_FILE)
ssez = load(SSEZ_FILE)
shv  = load(SHV_FILE)

print(f"Merged data: {len(df)} rows, {df['date'].min().date()} ~ {df['date'].max().date()}")

# =========================================================
# 3. Stage definitions
# =========================================================
stages = [
    ("Pre-development", "2014-01-01", "2016-12-31"),
    ("Gambling Boom",   "2017-01-01", "2019-08-17"),
    ("Post-818",        "2019-08-18", "2021-06-30"),
    ("Expansion",       "2021-07-01", "2025-10-14"),
    ("Post-sanctions",  "2025-10-15", "2026-03-31"),
]

# =========================================================
# Table 1: Index_2017 mean, standard deviation, and sample size for each stage and node
# =========================================================
t1_rows = []
for stage_name, s, e in stages:
    sub = df[(df["date"] >= s) & (df["date"] <= e)]
    n   = len(sub)
    row = {"Stage": stage_name, "Start": s, "End": e, "N": n}
    for col, label in [("GL_idx", "GL"), ("SSEZ_idx", "SSEZ"), ("SHV_idx", "SHV")]:
        row[f"{label}_mean"]   = sub[col].mean()
        row[f"{label}_median"] = sub[col].median()
        row[f"{label}_std"]    = sub[col].std()
    t1_rows.append(row)

t1 = pd.DataFrame(t1_rows)
t1.to_csv(OUT_T1, index=False, encoding="utf-8-sig")

print("\n========== Table 1: Stage index means ==========")
print(t1[["Stage", "N", "GL_mean", "SSEZ_mean", "SHV_mean"]].to_string(index=False))

# =========================================================
# Table 2: YoY correlations (full period and by phase)
# =========================================================
pairs = [
    ("GL_yoy",   "SSEZ_yoy", "GL↔SSEZ"),
    ("GL_yoy",   "SHV_yoy",  "GL↔SHV"),
    ("SSEZ_yoy", "SHV_yoy",  "SSEZ↔SHV"),
]

phase_windows = [
    ("Full period",    "2014-01-01", "2026-03-31"),
    ("Gambling Boom",  "2017-01-01", "2019-08-17"),
    ("Post-818",       "2019-08-18", "2021-06-30"),
    ("Expansion",      "2021-07-01", "2025-10-14"),
]

t2_rows = []
for phase_name, s, e in phase_windows:
    sub = df[(df["date"] >= s) & (df["date"] <= e)].dropna(subset=["GL_yoy", "SSEZ_yoy", "SHV_yoy"])
    for col_a, col_b, pair_name in pairs:
        if len(sub) >= 5:
            r, p = stats.pearsonr(sub[col_a], sub[col_b])
            sig  = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        else:
            r, p, sig = np.nan, np.nan, "n/a"
        t2_rows.append({
            "Phase":   phase_name,
            "Pair":    pair_name,
            "r":       round(r, 3) if not np.isnan(r) else np.nan,
            "p":       round(p, 4) if not np.isnan(p) else np.nan,
            "sig":     sig,
            "n":       len(sub),
        })

t2 = pd.DataFrame(t2_rows)
t2.to_csv(OUT_T2, index=False, encoding="utf-8-sig")

print("\n========== Table 2: YoY correlations ==========")
print(t2.to_string(index=False))

# =========================================================
# Table 3: 818 policy shock response
#
#   Index_2017 is used as the unified comparison baseline to ensure cross-node comparability
#
#   Field descriptions:
#     pre818_idx_mean  : mean Index_2017 over 2019-02 to 2019-08-17
#     post818_idx_min  : lowest Index_2017 in the post-818 window
#     post818_idx_mean : mean Index_2017 during the Post-818 phase
#     trough_drop_pct  : (trough - pre818 mean) / |pre818 mean| * 100
#                        negative = genuine decline; positive = no trough
#     post818_avg_chg  : (stage mean - pre818 mean) / |pre818 mean| * 100
#     interpretation   : economic interpretation label for the result
#
#   GL: trough < pre818 mean → genuine trough exists; report trough_drop_pct
#   SSEZ/SHV: trend monotonically increasing; trough > pre818 mean
#             → labelled as "Monotonic Expansion (No Trough)"
# =========================================================
pre818_mask  = (df["date"] >= "2019-02-01") & (df["date"] <= "2019-08-17")
post818_mask = (df["date"] >= "2019-08-18") & (df["date"] <= "2021-06-30")

t3_rows = []
for idx_col, name, sector_type in [
    ("GL_idx",   "GL",   "Service / Informal"),
    ("SSEZ_idx", "SSEZ", "Industrial"),
    ("SHV_idx",  "SHV",  "Macro / Province"),
]:
    pre_v     = df.loc[pre818_mask,  idx_col].mean()
    trough_v  = df.loc[post818_mask, idx_col].min()
    avg_v     = df.loc[post818_mask, idx_col].mean()
    trough_dt = df.loc[df.loc[post818_mask, idx_col].idxmin(), "date"]

    drop_pct  = (trough_v - pre_v) / abs(pre_v) * 100
    avg_chg   = (avg_v    - pre_v) / abs(pre_v) * 100
    has_trough = trough_v < pre_v

    if has_trough:
        interpretation = f"Service contraction: trough {drop_pct:.1f}% below pre-818 avg"
    else:
        interpretation = f"Monotonic Expansion (No Trough): avg +{avg_chg:.1f}% above pre-818"

    t3_rows.append({
        "Node":               name,
        "Sector_Type":        sector_type,
        "Pre818_Index_Mean":  round(pre_v, 1),
        "Post818_Index_Min":  round(trough_v, 1),
        "Post818_Min_Date":   trough_dt.strftime("%Y-%m"),
        "Post818_Index_Mean": round(avg_v, 1),
        "Trough_Drop_pct":    round(drop_pct, 1),
        "Post818_Avg_Chg_pct": round(avg_chg, 1),
        "Has_Trough":         has_trough,
        "Interpretation":     interpretation,
    })

t3 = pd.DataFrame(t3_rows)
t3.to_csv(OUT_T3, index=False, encoding="utf-8-sig")

print("\n========== Table 3: 818 policy shock response (Index_2017 basis) ==========")
print(t3[["Node", "Pre818_Index_Mean", "Post818_Index_Min", "Post818_Min_Date",
          "Trough_Drop_pct", "Has_Trough", "Interpretation"]].to_string(index=False))

# =========================================================
# Table 4: 2025 sanctions early response (through 2026-03)
# =========================================================
pre25_mask  = (df["date"] >= "2025-04-01") & (df["date"] <= "2025-10-14")
post25_mask = df["date"] >= "2025-10-15"

t4_rows = []
for idx_col, yoy_col, name, sector_type in [
    ("GL_idx",   "GL_yoy",   "GL",   "Service / Informal"),
    ("SSEZ_idx", "SSEZ_yoy", "SSEZ", "Industrial"),
    ("SHV_idx",  "SHV_yoy",  "SHV",  "Macro / Province"),
]:
    pre_v    = df.loc[pre25_mask,  idx_col].mean()
    post_v   = df.loc[post25_mask, idx_col].mean()
    n_pre    = int(pre25_mask.sum())
    n_post   = int(post25_mask.sum())

    if n_pre > 0 and n_post > 0:
        chg_pct = (post_v - pre_v) / abs(pre_v) * 100
        # Latest month YoY
        last_yoy = df.loc[post25_mask, yoy_col].dropna()
        latest_yoy = last_yoy.iloc[-1] if len(last_yoy) > 0 else np.nan
    else:
        chg_pct    = np.nan
        latest_yoy = np.nan

    t4_rows.append({
        "Node":              name,
        "Sector_Type":       sector_type,
        "Pre_Sanctions_Idx": round(pre_v,    1) if not np.isnan(pre_v)    else np.nan,
        "Post_Sanctions_Idx": round(post_v,  1) if not np.isnan(post_v)   else np.nan,
        "Chg_pct":           round(chg_pct,  1) if not np.isnan(chg_pct)  else np.nan,
        "Latest_YoY_pct":    round(latest_yoy, 1) if not np.isnan(latest_yoy) else np.nan,
        "N_pre":             n_pre,
        "N_post":            n_post,
        "Note":              "Early signal only — 5 months post-sanctions",
    })

t4 = pd.DataFrame(t4_rows)
t4.to_csv(OUT_T4, index=False, encoding="utf-8-sig")

print("\n========== Table 4: 2025 sanctions early response ==========")
print(t4[["Node", "Pre_Sanctions_Idx", "Post_Sanctions_Idx",
          "Chg_pct", "Latest_YoY_pct", "N_post"]].to_string(index=False))

# =========================================================
# Print complete output summary to console
# =========================================================
print("\n========== Output complete ==========")
print(f"Table 1 (stage means):    {OUT_T1}")
print(f"Table 2 (YoY correlations):   {OUT_T2}")
print(f"Table 3 (818 shock):     {OUT_T3}")
print(f"Table 4 (sanctions response):    {OUT_T4}")
