utf-8import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

                                                           
         
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "ssez" / "stats" / "ssez_boundary_stats.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ssez" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_MAIN = OUTPUT_DIR / "ssez_main.png"
OUT_STL  = OUTPUT_DIR / "ssez_stl_decomp.png"

                                                           
         
                                                           
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])

                                
df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

df = df.sort_values("date").reset_index(drop=True)

required_cols = [
          , "SOL_Sum_raw", "SOL_Sum", "SOL_Sum_interp",
               , "STL_Seasonal", "STL_Resid",
             , "Index_2017", "is_cloud_gap", "is_low_cvg",
]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(
                                          
                                        
    )

                 
cloud_dates = df.loc[df["is_cloud_gap"] | df["is_low_cvg"], "date"]

valid_sol = df["SOL_Sum"].dropna()
ymax = valid_sol.max() if len(valid_sol) > 0 else 1.0
ymin = valid_sol.min() if len(valid_sol) > 0 else 0.0

marker_y = ymin - (ymax - ymin) * 0.08

                                                           
         
                                                           
stage_bands = [
    ("2017-01-01", "2019-08-17", "#E8F5E9", "Gambling Boom"),
    ("2019-08-18", "2021-06-30", "#FFEBEE", "Post-818"),
    ("2021-07-01", "2025-10-14", "#E3F2FD", "Industrial Expansion"),
    ("2025-10-15", "2026-06-01", "#FFF8E1", "Post-Sanctions"),
]

def draw_bands(ax):
    for s, e, c, _ in stage_bands:
        ax.axvspan(pd.to_datetime(s), pd.to_datetime(e), color=c, alpha=0.4, zorder=0)
    ax.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
               linestyle="--", linewidth=1.5, alpha=0.9, zorder=3)
    ax.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
               linestyle="--", linewidth=1.5, alpha=0.9, zorder=3)

                                                           
                            
                                                           
fig = plt.figure(figsize=(16, 12))
gs  = fig.add_gridspec(3, 1, height_ratios=[3, 1.8, 1.8], hspace=0.35)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])
ax3 = fig.add_subplot(gs[2])

                                
draw_bands(ax1)

ax1.scatter(
    cloud_dates, [marker_y] * len(cloud_dates),
    marker="v", color="#E74C3C", s=30, zorder=5,
    label="Low-quality obs (avg_cvg < 1, mostly monsoon)",
)
ax1.scatter(
    df["date"], df["SOL_Sum"],
    color="#7D3C98", alpha=0.25, s=18, zorder=2,
    label="Monthly SOL (raw)",
)
ax1.plot(
    df["date"], df["STL_Trend"],
    color="#1E8449", linewidth=3, zorder=4,
    label="STL Trend (seasonality removed)",
)

ax1.text(pd.to_datetime("2019-09-01"), ymax * 0.90,
                            , color="#C0392B", fontsize=9, fontweight="bold")
ax1.text(pd.to_datetime("2025-10-22"), ymax * 0.75,
                              , color="darkorange", fontsize=9, fontweight="bold")

for s, e, c, label in stage_bands:
    mid = pd.to_datetime(s) + (pd.to_datetime(e) - pd.to_datetime(s)) / 2
    ax1.text(mid, ymin - (ymax - ymin) * 0.04, label,
             ha="center", fontsize=7.5, color="#555", style="italic")

ax1.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax1.set_ylabel("SOL Sum (nW·cm⁻²·sr⁻¹)", fontsize=11)
ax1.set_title(
                                                                    
                                                                                   ,
    fontsize=13, fontweight="bold",
)
ax1.legend(loc="upper left", fontsize=9)
ax1.grid(True, alpha=0.2)

                            
draw_bands(ax2)
ax2.axhline(100, color="black", linewidth=1, linestyle=":", alpha=0.6)

ax2.plot(df["date"], df["Index_2017"], color="#2471A3", linewidth=2.5, zorder=4)
ax2.fill_between(df["date"], 100, df["Index_2017"],
                 where=df["Index_2017"] >= 100, color="#2471A3", alpha=0.15)
ax2.fill_between(df["date"], 100, df["Index_2017"],
                 where=df["Index_2017"] < 100,  color="#C0392B", alpha=0.15)

                               
for name, s, e in [
    ("Pre-dev.",       "2014-01-01", "2016-12-31"),
    ("Gambling\nBoom", "2017-01-01", "2019-08-17"),
    ("Post-818",       "2019-08-18", "2021-06-30"),
    ("Expansion",      "2021-07-01", "2025-10-14"),
]:
    sub = df[(df["date"] >= s) & (df["date"] <= e)]
    if len(sub) > 0:
        mid_date = sub["date"].iloc[len(sub) // 2]
        mid_val  = sub["Index_2017"].mean()
        ax2.text(mid_date, mid_val + 8, f"{mid_val:.0f}",
                 ha="center", fontsize=8, color="#2471A3", fontweight="bold")

ax2.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax2.set_ylabel("Index (2017 = 100)", fontsize=11)
ax2.set_title("Normalized SOL Index (2017 = 100)", fontsize=11)
ax2.grid(True, alpha=0.2)

                 
draw_bands(ax3)
ax3.axhline(0, color="black", linewidth=1, alpha=0.7)

yoy = df["YoY_pct"]
ax3.fill_between(df["date"], yoy, 0, where=yoy >= 0, color="#1E8449", alpha=0.55, label="YoY > 0")
ax3.fill_between(df["date"], yoy, 0, where=yoy <  0, color="#C0392B", alpha=0.55, label="YoY < 0")
ax3.plot(df["date"], yoy, color="#117A65", linewidth=1.5, zorder=4)

                                 
ax3.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax3.set_ylim(-60, 120)
ax3.set_ylabel("YoY Change %\n(STL trend-based)", fontsize=11)
ax3.set_title("Year-on-Year Growth Rate — Seasonal and Weather Effects Removed", fontsize=11)
ax3.legend(loc="upper right", fontsize=9)
ax3.grid(True, alpha=0.2)

plt.savefig(OUT_MAIN, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"已保存: {OUT_MAIN}")

                                                           
                
                                                           
fig2, axes2 = plt.subplots(4, 1, figsize=(16, 14), sharex=True)

panels = [
    (df["SOL_Sum"],      "#7D3C98", "Original SOL Sum (NaN / low-cvg = interpolated)"),
    (df["STL_Trend"],    "#1E8449", "STL Trend — industrial activity signal"),
    (df["STL_Seasonal"], "#2471A3", "STL Seasonal Component — monsoon pattern"),
    (df["STL_Resid"],    "#C0392B", "STL Residual — unexplained shocks"),
]

for ax, (data, color, title) in zip(axes2, panels):
    ax.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
               linestyle="--", linewidth=1.2, alpha=0.8)
    ax.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
               linestyle="--", linewidth=1.2, alpha=0.8)

    if "Residual" in title or "Seasonal" in title:
        ax.fill_between(df["date"], data.clip(lower=0), 0, color="#1E8449", alpha=0.6)
        ax.fill_between(df["date"], data.clip(upper=0), 0, color="#C0392B", alpha=0.6)
        ax.axhline(0, color="black", linewidth=0.8)
    else:
        ax.scatter(df["date"], data, color=color, alpha=0.3, s=14, zorder=2)
        ax.plot(df["date"], data, color=color, linewidth=1.8, zorder=3)

    ax.set_title(title, fontsize=10, pad=4)
    ax.grid(True, alpha=0.15)
    ax.set_ylabel("SOL", fontsize=9)

axes2[-1].set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))

fig2.suptitle(
                                                            
                                                                                       ,
    fontsize=13, fontweight="bold", y=1.01,
)

plt.tight_layout()
plt.savefig(OUT_STL, dpi=300, bbox_inches="tight")
plt.close(fig2)

                                                           
         
                                                           
print("\n========== SSEZ 绘图完成 ==========")
print(f"输入文件: {INPUT_CSV}")
print(f"输出目录: {OUTPUT_DIR}")
print(f"已保存: {OUT_MAIN}")
print(f"已保存: {OUT_STL}")
