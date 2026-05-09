utf-8import pandas as pd
import numpy as np
from pathlib import Path

                                                           
         
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "outputs" / "gl" / "merged" / "gl_merged_ntl_s2.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_STAGE_MEAN  = OUTPUT_DIR / "gl_stage_stats.csv"
OUT_STAGE_DELTA = OUTPUT_DIR / "gl_stage_changes.csv"

                                                           
         
                                                           
df = pd.read_csv(INPUT_FILE)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

                                             
df["is_low_quality"] = df["is_low_quality"].map(
    {True: True, False: False, "True": True, "False": False}
).fillna(True).astype(bool)

                                                           
          
                                
                                   
                                                         
                                                        
                                                           
df_ntl = df.copy()
df_s2  = df[(df["is_low_quality"] == False) & (df["date"] >= "2017-02-01")].copy()

print(f"NTL 全时段样本数: {len(df_ntl)}")
print(f"S2 高质量样本数:  {len(df_s2)}")
print(f"S2 时间范围:      {df_s2['date'].min().date()} ~ {df_s2['date'].max().date()}")

                                                           
         
                                        
                                        
                                                           
stages = [
    ("Gambling_Boom",  "2017-01-01", "2019-08-17"),
    ("Post_818",       "2019-08-18", "2021-06-30"),
    ("Second_Boom",    "2021-07-01", "2025-10-14"),
    ("Post_sanctions", "2025-10-15", "2026-03-31"),
]

                                                           
                     
                                                           
ntl_cols = ["STL_Trend", "Intensity_Mean", "SOL_Sum", "Index_2017", "YoY_pct"]
s2_cols  = ["NDVI_mean", "NDBI_mean", "NDVI_interp", "NDBI_interp"]

rows = []

for name, s, e in stages:
    sub_ntl = df_ntl[(df_ntl["date"] >= s) & (df_ntl["date"] <= e)].copy()
    sub_s2  = df_s2[ (df_s2["date"]  >= s) & (df_s2["date"]  <= e)].copy()

    row = {
               :  name,
               :  s,
             :    e,
               :  len(sub_ntl),
              :   len(sub_s2),
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

print("\n========== 阶段统计 ==========")
print(stage_stats.to_string(index=False))

                                                           
                        
                                                           
compare_cols = [
                    ,
                         ,
                  ,
                     ,
                    ,
                    ,
                      ,
                      ,
]

change_rows = []

for i in range(1, len(stage_stats)):
    prev_row = stage_stats.iloc[i - 1]
    curr_row = stage_stats.iloc[i]

    out = {
                    : prev_row["Stage"],
                  :   curr_row["Stage"],
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

print("\n========== 阶段变化 ==========")
print(stage_changes.to_string(index=False))

                                                           
                  
                                                           
print("\n========== 论文引用摘要 ==========")
for _, row in stage_stats.iterrows():
    print(f"\n[{row['Stage']}] ({row['Start']} ~ {row['End']})")
    print(f"  NTL STL Trend 均值:  {row.get('STL_Trend_mean', np.nan):.2f}")
    print(f"  Index_2017 均值:     {row.get('Index_2017_mean', np.nan):.1f}")
    ntl_n  = int(row["N_ntl"])
    s2_n   = int(row["N_s2"])
    print(f"  夜光月份数: {ntl_n}  |  S2 高质量月份数: {s2_n}")
    if s2_n > 0:
        print(f"  NDBI 均值: {row.get('NDBI_mean_mean', np.nan):.4f}  "
                                                                 )

print("\n========== 输出完成 ==========")
print(f"阶段统计表: {OUT_STAGE_MEAN}")
print(f"阶段变化表: {OUT_STAGE_DELTA}")
