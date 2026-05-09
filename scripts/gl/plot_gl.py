utf-8import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

                                                           
         
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = PROJECT_ROOT / "outputs" / "gl" / "stats" / "gl_boundary_stats.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_MAIN  = OUTPUT_DIR / "gl_main.png"
OUT_AUDIT = OUTPUT_DIR / "gl_lighting_audit.png"
OUT_STL   = OUTPUT_DIR / "gl_stl_decomp.png"

                                                           
         
                                                           
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

required_cols = [
          , "Mean_raw", "Intensity_Mean", "Mean_interp",
               , "STL_Seasonal", "STL_Resid",
             , "Index_2017", "is_cloud_gap", "is_low_cvg",
]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(
                                          
                                      
    )

                         
cloud_dates = df.loc[df["is_cloud_gap"] | df["is_low_cvg"], "date"]

ymax_raw = df["Mean_raw"].replace(0, np.nan).dropna().max()
if pd.isna(ymax_raw):
    ymax_raw = 1.0

valid_intensity = df["Intensity_Mean"].dropna()
ymin_marker = valid_intensity.quantile(0.05) if len(valid_intensity) > 0 else 1.0

                                                           
              
                                                           
stage_bands = [
    ("2017-01-01", "2019-08-17", "#E8F5E9", "Gambling Boom"),
    ("2019-08-18", "2021-06-30", "#FFEBEE", "Post-818"),
    ("2021-07-01", "2025-10-14", "#E3F2FD", "Second Boom / Expansion"),
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
    cloud_dates,
    [ymin_marker * 0.3] * len(cloud_dates),
    marker="v", color="#E74C3C", s=30, zorder=5,
    label="Low-quality obs (avg_cvg < 1, mostly monsoon)",
)
ax1.scatter(
    df["date"], df["Intensity_Mean"],
    color="#7D3C98", alpha=0.25, s=18, zorder=2,
    label="Monthly Mean (raw)",
)
ax1.plot(
    df["date"], df["STL_Trend"],
    color="#6C3483", linewidth=3, zorder=4,
    label="STL Trend",
)

ax1.text(pd.to_datetime("2019-09-01"), ymax_raw * 0.90,
                            , color="#C0392B", fontsize=9, fontweight="bold")
ax1.text(pd.to_datetime("2025-10-22"), ymax_raw * 0.75,
                              , color="darkorange", fontsize=9, fontweight="bold")

for s, e, c, label in stage_bands:
    mid = pd.to_datetime(s) + (pd.to_datetime(e) - pd.to_datetime(s)) / 2
    ax1.text(mid, ymax_raw * 0.04, label,
             ha="center", fontsize=7.5, color="#555", style="italic")

ax1.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax1.set_ylabel("Intensity Mean (nW·cm⁻²·sr⁻¹)", fontsize=11)
ax1.set_title(
                                                                               
                                                                                       ,
    fontsize=13, fontweight="bold",
)
ax1.legend(loc="upper left", fontsize=9)
ax1.grid(True, alpha=0.2)

                   
draw_bands(ax2)
ax2.axhline(100, color="black", linewidth=1, linestyle=":", alpha=0.6)
ax2.plot(df["date"], df["Index_2017"], color="#6C3483", linewidth=2.5, zorder=4)
ax2.fill_between(df["date"], 100, df["Index_2017"],
                 where=df["Index_2017"] >= 100, color="#6C3483", alpha=0.15)
ax2.fill_between(df["date"], 100, df["Index_2017"],
                 where=df["Index_2017"] < 100,  color="#C0392B", alpha=0.15)

ax2.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax2.set_ylabel("Index (2017 = 100)", fontsize=11)
ax2.set_title("Normalized Activity Index (2017 = 100)", fontsize=11)
ax2.grid(True, alpha=0.2)

                 
draw_bands(ax3)
ax3.axhline(0, color="black", linewidth=1, alpha=0.7)
yoy = df["YoY_pct"]
ax3.fill_between(df["date"], yoy, 0, where=yoy >= 0, color="#6C3483", alpha=0.55)
ax3.fill_between(df["date"], yoy, 0, where=yoy <  0, color="#C0392B", alpha=0.55)
ax3.plot(df["date"], yoy, color="#6C3483", linewidth=1.5, zorder=4)

                                   
ax3.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
ax3.set_ylim(-80, 150)
ax3.set_ylabel("YoY % (STL trend-based)", fontsize=11)
ax3.set_title("Year-on-Year Growth Rate — Seasonal Effects Removed", fontsize=11)
ax3.grid(True, alpha=0.2)

plt.savefig(OUT_MAIN, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"已保存: {OUT_MAIN}")

                                                           
               
                                                           
trough_periods = {
          : ("2014-01-01", "2014-12-31"),
          : ("2015-01-01", "2015-12-31"),
          : ("2016-01-01", "2016-12-31"),
          : ("2020-03-01", "2020-12-31"),
          : ("2021-01-01", "2021-06-30"),
}
trough_means = {}
for yr, (s, e) in trough_periods.items():
    sub = df[
        (df["date"] >= s) &
        (df["date"] <= e) &
        (~df["is_cloud_gap"])
    ]["Mean_raw"]
    trough_means[yr] = sub.mean()

t_labels = list(trough_means.keys())
t_vals   = list(trough_means.values())

base_2014_16 = np.mean(t_vals[:3])
base_2020_21 = np.mean(t_vals[3:])
gap = base_2020_21 - base_2014_16

stage_audit = {
                   :       ("2017-01-01", "2017-12-31", "#2E86C1"),
                       :   ("2019-06-01", "2019-08-31", "#C0392B"),
                    :      ("2020-01-01", "2021-06-30", "#884EA0"),
                         : ("2022-01-01", "2023-05-31", "#E67E22"),
                        :  ("2025-01-01", "2025-08-31", "#1E8449"),
}

pre818     = df[
    (df["date"] >= "2019-06-01") &
    (df["date"] <= "2019-08-31") &
    (~df["is_cloud_gap"])
]["Mean_raw"].mean()

base_early = base_2014_16
mom        = df["Mean_interp"].pct_change() * 100

fig2 = plt.figure(figsize=(16, 14))
gs2  = fig2.add_gridspec(3, 1, height_ratios=[3, 1.5, 1.5], hspace=0.42)
bx1  = fig2.add_subplot(gs2[0])
bx2  = fig2.add_subplot(gs2[1])
bx3  = fig2.add_subplot(gs2[2])

                 
for label, (s, e, col) in stage_audit.items():
    sub = df[
        (df["date"] >= s) &
        (df["date"] <= e) &
        (~df["is_cloud_gap"])
    ]["Mean_raw"]
    if len(sub) == 0:
        continue
    mu = sub.mean()
    bx1.axvspan(pd.to_datetime(s), pd.to_datetime(e), color=col, alpha=0.12)
    bx1.hlines(mu, pd.to_datetime(s), pd.to_datetime(e),
               colors=col, linewidths=2.5, zorder=5)
    bx1.text(pd.to_datetime(s) + pd.Timedelta(days=8), mu + 2,
                          , color=col, fontsize=9, fontweight="bold")

bx1.scatter(
    cloud_dates, [2] * len(cloud_dates),
    marker="v", color="#E74C3C", s=25, zorder=6,
    label="Low-quality obs (avg_cvg < 1, mostly monsoon)",
)
bx1.plot(df["date"], df["Mean_interp"],
         color="#B0B7BC", alpha=0.85, linewidth=1, label="Monthly (interpolated)")
bx1.plot(df["date"], df["STL_Trend"],
         color="#6C3483", linewidth=2.5, label="STL Trend")

bx1.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
            linestyle="--", linewidth=1.5, alpha=0.9)
bx1.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
            linestyle="--", linewidth=1.5, alpha=0.9)

bx1.text(pd.to_datetime("2019-08-18") + pd.Timedelta(days=8), ymax_raw * 1.10,
                           , rotation=90, color="#C0392B",
         fontsize=9, fontweight="bold", va="top", ha="left", alpha=0.95)
bx1.text(pd.to_datetime("2025-10-15") + pd.Timedelta(days=8), ymax_raw * 1.10,
                             , rotation=90, color="darkorange",
         fontsize=9, fontweight="bold", va="top", ha="left", alpha=0.95)

bx1.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
bx1.set_ylim(-5, ymax_raw * 1.15)
bx1.set_ylabel("Intensity Mean (nW·cm⁻²·sr⁻¹)", fontsize=11)
bx1.set_title(
                                                                                      ,
    fontsize=12, fontweight="bold",
)
bx1.legend(loc="upper left", fontsize=9)
bx1.grid(True, alpha=0.2)

            
bar_cols = ["#85C1E9", "#5DADE2", "#2E86C1", "#884EA0", "#6C3483"]
x_pos    = np.arange(len(t_labels))
bars     = bx2.bar(x_pos, t_vals, color=bar_cols,
                   edgecolor="white", linewidth=0.5, width=0.6)

for bar, val in zip(bars, t_vals):
    bx2.text(bar.get_x() + bar.get_width() / 2, val + 0.4,
                         , ha="center", va="bottom", fontsize=10, fontweight="bold")

bx2.axhline(base_2014_16, color="#2E86C1", linestyle="--", linewidth=1.5, alpha=0.8,
            label=f"2014–2016 avg = {base_2014_16:.1f}")
bx2.axhline(base_2020_21, color="#884EA0", linestyle="--", linewidth=1.5, alpha=0.8,
            label=f"2020–2021 avg = {base_2020_21:.1f}")

bx2.set_xticks(x_pos)
bx2.set_xticklabels(t_labels, fontsize=11)
bx2.text(
    0.98, 0.6,
                                                                                         
                                                 
                                                                               ,
    transform=bx2.transAxes, ha="right", va="top", fontsize=9, color="#6C3483",
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#F4ECF7",
              edgecolor="#884EA0", alpha=0.85),
)
bx2.set_ylabel("Mean Intensity\n(cloud-gap months excluded)", fontsize=10)
bx2.set_title(
                                             
                                                                     ,
    fontsize=10,
)
bx2.legend(fontsize=9, loc="upper left")
bx2.grid(True, alpha=0.2, axis="y")
bx2.set_ylim(0, max(t_vals) * 1.35)

              
bx3.fill_between(df["date"], mom.clip(lower=0), 0,
                 color="#1E8449", alpha=0.6, label="MoM increase")
bx3.fill_between(df["date"], mom.clip(upper=0), 0,
                 color="#C0392B", alpha=0.6, label="MoM decrease")
bx3.axhline(0, color="black", linewidth=0.8)
bx3.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
            linestyle="--", linewidth=1.5, alpha=0.9)
bx3.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
            linestyle="--", linewidth=1.5, alpha=0.9)

bx3.annotate(
                                                                                 ,
    xy=(pd.to_datetime("2020-02-01"), -40),
    xytext=(pd.to_datetime("2017-04-01"), -115),
    fontsize=8.5, color="#C0392B",
    arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.5),
)
bx3.set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))
bx3.set_ylim(-120, 200)
bx3.set_ylabel("Month-on-Month %", fontsize=10)
bx3.set_title(
                                                                              ,
    fontsize=10,
)
bx3.legend(fontsize=9, loc="upper left")
bx3.grid(True, alpha=0.2)

fig2.suptitle(
                                                          
                                                                       ,
    fontsize=13, fontweight="bold",
)
plt.savefig(OUT_AUDIT, dpi=300, bbox_inches="tight")
plt.close(fig2)
print(f"已保存: {OUT_AUDIT}")

                                                           
                
                                                           
fig3, axes3 = plt.subplots(4, 1, figsize=(16, 14), sharex=True)

panels3 = [
    (df["Intensity_Mean"], "#7D3C98", "Original Intensity Mean (NaN / low-cvg = interpolated)"),
    (df["STL_Trend"],      "#6C3483", "STL Trend — activity signal"),
    (df["STL_Seasonal"],   "#2471A3", "STL Seasonal Component — monsoon pattern"),
    (df["STL_Resid"],      "#C0392B", "STL Residual — unexplained shocks"),
]

for ax, (data, color, title) in zip(axes3, panels3):
    ax.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
               linestyle="--", linewidth=1.2, alpha=0.8)
    ax.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
               linestyle="--", linewidth=1.2, alpha=0.8)

    if "Residual" in title or "Seasonal" in title:
        ax.fill_between(df["date"], data.clip(lower=0), 0, color="#6C3483", alpha=0.6)
        ax.fill_between(df["date"], data.clip(upper=0), 0, color="#C0392B", alpha=0.6)
        ax.axhline(0, color="black", linewidth=0.8)
    else:
        ax.scatter(df["date"], data, color=color, alpha=0.3, s=14, zorder=2)
        ax.plot(df["date"], data, color=color, linewidth=1.8, zorder=3)

    ax.set_title(title, fontsize=10, pad=4)
    ax.grid(True, alpha=0.15)
    ax.set_ylabel("Intensity", fontsize=9)

axes3[-1].set_xlim(pd.to_datetime("2014-01-01"), pd.to_datetime("2026-06-01"))

fig3.suptitle(
                                                                
                                                                       ,
    fontsize=13, fontweight="bold", y=1.01,
)
plt.tight_layout()
plt.savefig(OUT_STL, dpi=300, bbox_inches="tight")
plt.close(fig3)

                                                           
         
                                                           
print("\n========== GL 绘图完成 ==========")
print(f"输入文件: {INPUT_CSV}")
print(f"输出目录: {OUTPUT_DIR}")
print(f"已保存: {OUT_MAIN}")
print(f"已保存: {OUT_AUDIT}")
print(f"已保存: {OUT_STL}")
