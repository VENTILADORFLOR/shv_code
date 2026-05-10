import pandas as pd
from pathlib import Path

# =========================================================
# 1. Path configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "outputs" / "ssez" / "gee" / "ssez_viirs_monthly_raw.csv"

def check_quality():
    if not DATA_PATH.exists():
        print(f"Error: file not found {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

    # =========================================================
    # 2. Apply quality screening criterion (0.5 <= avg_cvg < 1.5)
    # =========================================================
    mask_marginal = (df["avg_cvg"] >= 0.5) & (df["avg_cvg"] < 1.5)
    df_marginal = df[mask_marginal][["date", "avg_cvg", "SOL_Sum", "is_monsoon"]]

    print("\n" + "="*50)
    print(f" Marginal-quality months detected (0.5 <= avg_cvg < 1.5) ")
    print("="*50)
    
    if df_marginal.empty:
        print("No months found in this range.")
    else:
        print(df_marginal.to_string(index=False))

    # =========================================================
    # 3. In-depth quality analysis
    # =========================================================
    print("\n" + "="*50)
    print(" Quality overview statistics ")
    print("="*50)
    
    total = len(df)
    low_cvg_count = (df["avg_cvg"] < 1.0).sum()
    zero_sol_count = df["SOL_Sum"].isna().sum()

    print(f"Total months: {total}")
    print(f"Fully missing (SOL is NaN): {zero_sol_count} ({zero_sol_count/total:.1%})")
    print(f"Low quality (avg_cvg < 1.0): {low_cvg_count} ({low_cvg_count/total:.1%})")

    # Comparison by season
    print("\nMean observation frequency by season (avg_cvg):")
    season_stats = df.groupby("is_monsoon")["avg_cvg"].mean()
    print(f"  - Dry season: {season_stats[False]:.2f}")
    print(f"  - Monsoon season: {season_stats[True]:.2f}")

    # =========================================================
    # 4. Flagged months for review
    # =========================================================
    # Identify months with non-missing but extremely low observation counts, which may introduce spurious variation
    df_warning = df[(df["avg_cvg"] < 0.8) & (df["SOL_Sum"].notna())]
    if not df_warning.empty:
        print("\n[WARNING] The following months have very low observation counts (<0.8) and should be excluded from analysis:")
        print(df_warning[["date", "avg_cvg", "SOL_Sum"]])

if __name__ == "__main__":
    check_quality()