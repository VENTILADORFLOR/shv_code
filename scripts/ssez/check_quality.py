utf-8import pandas as pd
from pathlib import Path

                                                           
         
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "outputs" / "ssez" / "gee" / "ssez_viirs_monthly_raw.csv"

def check_quality():
    if not DATA_PATH.exists():
        print(f"错误: 找不到文件 {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

                                                               
                                          
                                                               
    mask_marginal = (df["avg_cvg"] >= 0.5) & (df["avg_cvg"] < 1.5)
    df_marginal = df[mask_marginal][["date", "avg_cvg", "SOL_Sum", "is_monsoon"]]

    print("\n" + "="*50)
    print(f" 检测到边缘质量月份 (0.5 <= avg_cvg < 1.5) ")
    print("="*50)
    
    if df_marginal.empty:
        print("未发现该区间内的月份。")
    else:
        print(df_marginal.to_string(index=False))

                                                               
               
                                                               
    print("\n" + "="*50)
    print(" 质量概况统计 ")
    print("="*50)
    
    total = len(df)
    low_cvg_count = (df["avg_cvg"] < 1.0).sum()
    zero_sol_count = df["SOL_Sum"].isna().sum()

    print(f"总月份数: {total}")
    print(f"完全缺失 (SOL is NaN): {zero_sol_count} ({zero_sol_count/total:.1%})")
    print(f"低质量 (avg_cvg < 1.0): {low_cvg_count} ({low_cvg_count/total:.1%})")

           
    print("\n按季节划分的平均观测频率 (avg_cvg):")
    season_stats = df.groupby("is_monsoon")["avg_cvg"].mean()
    print(f"  - 非雨季 (Dry): {season_stats[False]:.2f}")
    print(f"  - 雨季 (Monsoon): {season_stats[True]:.2f}")

                                                               
               
                                                               
                                  
    df_warning = df[(df["avg_cvg"] < 0.8) & (df["SOL_Sum"].notna())]
    if not df_warning.empty:
        print("\n[警告] 以下月份观测次数极低 (<0.8)，建议在分析逻辑中剔除:")
        print(df_warning[["date", "avg_cvg", "SOL_Sum"]])

if __name__ == "__main__":
    check_quality()