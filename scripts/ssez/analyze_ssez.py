utf-8import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.seasonal import STL

                                                           
       
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "ssez" / "gee" / "ssez_viirs_monthly_raw.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ssez" / "stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "ssez_boundary_stats.csv"

                                                           
         
                                                           
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])

                                       
df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

df = df.sort_values("date").reset_index(drop=True)

required_cols = ["date", "SOL_Sum", "Intensity_Mean", "is_low_cvg", "is_cloud_gap"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"输入 CSV 缺少必要字段: {missing_cols}")

                                                           
         
                                                           
df["year"]       = df["date"].dt.year
df["month"]      = df["date"].dt.month
df["is_monsoon"] = df["month"].isin([5, 6, 7, 8, 9, 10])

                                                           
       
                                
                          
                                                           
df["SOL_Sum_raw"]        = df["SOL_Sum"].copy()
df["Intensity_Mean_raw"] = df["Intensity_Mean"].copy()

df.loc[df["is_low_cvg"], "SOL_Sum"]        = np.nan
df.loc[df["is_low_cvg"], "Intensity_Mean"] = np.nan

                         
cloud_gap_count = int(df["is_cloud_gap"].sum())
monsoon_gap     = int(df.loc[df["is_cloud_gap"] & df["is_monsoon"], "date"].count())
low_cvg_total   = int(df["is_low_cvg"].sum())

           
print("\n--- 低质量观测月份详情 (avg_cvg < 1) ---")
print(df[df["is_low_cvg"]][["date", "SOL_Sum_raw", "avg_cvg", "is_monsoon"]])
print("-" * 40)

                                                           
                   
                                                           
df["SOL_Sum_interp"]        = df["SOL_Sum"].interpolate(
    method="linear", limit_direction="both"
)
df["Intensity_Mean_interp"] = df["Intensity_Mean"].interpolate(
    method="linear", limit_direction="both"
)

                                                           
                         
                                                           
stl_result = STL(df["SOL_Sum_interp"], period=12, robust=True).fit()

df["STL_Trend"]    = stl_result.trend
df["STL_Seasonal"] = stl_result.seasonal
df["STL_Resid"]    = stl_result.resid

df["YoY_pct"] = df["STL_Trend"].pct_change(12) * 100

                                                           
                     
                                                           
base_mask = (df["date"] >= "2017-01-01") & (df["date"] <= "2017-12-31")
base_val  = df.loc[base_mask, "STL_Trend"].mean()

if pd.isna(base_val) or base_val == 0:
    raise ValueError("2017 基期均值无效，无法计算 Index_2017。")

df["Index_2017"] = df["STL_Trend"] / base_val * 100

                                                           
         
                                                      
                                                           
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

                                                           
         
                                         
                                          
                        
                                                           
pre818 = df[
    (df["date"] >= "2019-02-01") &
    (df["date"] <= "2019-08-17")
]["STL_Trend"].mean()

trough_mask = (df["date"] >= "2019-08-18") & (df["date"] <= "2021-12-31")
trough_val  = df.loc[trough_mask, "STL_Trend"].min()
trough_dt   = df.loc[df.loc[trough_mask, "STL_Trend"].idxmin(), "date"]

df["base_2017_mean"]      = base_val
df["pre818_mean"]         = pre818
                                
df["post818_trough_val"]  = trough_val
df["post818_trough_date"] = trough_dt.strftime("%Y-%m")

                                                           
        
                                                           
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

                                                           
           
                                                           
print("\n========== SSEZ 分析完成 ==========")
print(f"输入文件: {INPUT_CSV}")
print(f"输出文件: {OUTPUT_CSV}")
print(f"时间范围: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"总行数: {len(df)}")
print(f"完全缺测月份 (is_cloud_gap): {cloud_gap_count}")
print(f"  其中雨季月份: {monsoon_gap}")
print(f"低质量月份 (avg_cvg < 1, 含缺测): {low_cvg_total}")
print(f"2017 基期均值: {base_val:.2f}")
print(f"818 前均值 (2019-02~08): {pre818:.2f}")
print(
                                                                   
                                    
)

print("\n阶段均值（基于 STL_Trend）:")
stage_order = [
                     , "Gambling Boom", "Post-818 Trough",
                          , "Post-sanctions", "Other"
]
stage_summary = (
    df.groupby("stage", dropna=False)["STL_Trend"]
    .mean()
    .reindex(stage_order)
    .dropna()
    .reset_index()
)
print(stage_summary.to_string(index=False))
