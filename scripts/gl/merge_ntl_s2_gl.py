utf-8import pandas as pd
from pathlib import Path

                                                           
           
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

S2_FILE  = PROJECT_ROOT / "outputs" / "gl" / "sentinel_indices" / "gl_s2_indices_monthly.csv"
NTL_FILE = PROJECT_ROOT / "outputs" / "gl" / "stats" / "gl_boundary_stats.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "merged"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "gl_merged_ntl_s2.csv"

                                                           
         
                                                           
df_s2  = pd.read_csv(S2_FILE)
df_ntl = pd.read_csv(NTL_FILE)

print("S2 列名:",   df_s2.columns.tolist())
print("夜光列名:", df_ntl.columns.tolist())

                                                           
                
                                                           
for df_, name in [(df_s2, "S2"), (df_ntl, "NTL")]:
    if "date" not in df_.columns:
        raise ValueError(f"{name} 文件中没有 date 列。")

df_s2["date"]  = pd.to_datetime(df_s2["date"]).dt.to_period("M").dt.to_timestamp()
df_ntl["date"] = pd.to_datetime(df_ntl["date"]).dt.to_period("M").dt.to_timestamp()

                                                           
                
                                                     
                                                           
ntl_keep_candidates = [
          ,
                    ,
             ,
              ,
             ,
             ,
                  ,
                ,
                 ,
               ,
                  ,
               ,
             ,
                ,
           ,
          ,
           ,
                ,
]

ntl_keep    = [c for c in ntl_keep_candidates if c in df_ntl.columns]
df_ntl_sub  = df_ntl[ntl_keep].copy()

                                                           
               
                         
                                              
                                                           
s2_keep_candidates = [
          ,
                 ,
               ,
               ,
                 ,
                 ,
                    ,
                    ,
]

s2_keep    = [c for c in s2_keep_candidates if c in df_s2.columns]
df_s2_sub  = df_s2[s2_keep].copy()

                                                           
       
                                                           
df_merge = pd.merge(
    df_ntl_sub,
    df_s2_sub,
    on="date",
    how="outer",
    sort=True,
)

                                                           
           
                                         
                                                           
df_merge["has_ntl"]  = df_merge["Intensity_Mean"].notna() if "Intensity_Mean" in df_merge.columns else False
df_merge["has_ndvi"] = df_merge["NDVI_mean"].notna()      if "NDVI_mean"       in df_merge.columns else False
df_merge["has_ndbi"] = df_merge["NDBI_mean"].notna()      if "NDBI_mean"       in df_merge.columns else False

                         
ntl_ok = ~df_merge["is_low_cvg"].fillna(False)     if "is_low_cvg"     in df_merge.columns else True
s2_ok  = ~df_merge["is_low_quality"].fillna(False) if "is_low_quality" in df_merge.columns else True

df_merge["common_period"] = (
    df_merge["has_ntl"] &
    df_merge["has_ndvi"] &
    ntl_ok &
    s2_ok
)

common_df = df_merge[df_merge["common_period"]].copy()

                                                           
       
                                                           
df_merge.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n========== 合并完成 ==========")
print(f"输出文件: {OUTPUT_FILE}")
print(f"总行数: {len(df_merge)}")

if len(common_df) > 0:
    print(f"高质量共同样本行数: {len(common_df)}")
    print(f"共同时间范围: {common_df['date'].min().date()} ~ {common_df['date'].max().date()}")
else:
    print("没有找到高质量共同样本期，请检查 date 格式或数据质量标记。")

print("\n合并后列名:")
print(df_merge.columns.tolist())

print("\n最后 12 行预览:")
print(df_merge.tail(12).to_string(index=False))
