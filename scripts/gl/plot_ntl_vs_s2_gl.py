utf-8import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from scipy import stats
from pathlib import Path

                                                           
         
                                                           
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "outputs" / "gl" / "merged" / "gl_merged_ntl_s2.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "gl" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FIG = OUTPUT_DIR / "gl_ntl_ndvi_ndbi_v2.png"

                                                           
         
                                                           
df = pd.read_csv(INPUT_FILE)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

                                                
df["is_low_quality"] = df["is_low_quality"].map(
    {True: True, False: False, "True": True, "False": False}
).fillna(True).astype(bool)

                         
s2_valid = df[df["image_count"] > 0].copy()

                                                
common = df[df["common_period"] == True].copy()

print(f"NTL 全时段:      {df['date'].min().date()} ~ {df['date'].max().date()}, n={len(df)}")
print(f"S2 有效期:       {s2_valid['date'].min().date()} ~ {s2_valid['date'].max().date()}, n={len(s2_valid)}")
print(f"高质量共同期:    {common['date'].min().date()} ~ {common['date'].max().date()}, n={len(common)}")

                                                           
                    
                                                           
r_ntl_ndbi, p_ntl_ndbi = stats.pearsonr(common["STL_Trend"], common["NDBI_mean"])
r_ntl_ndvi, p_ntl_ndvi = stats.pearsonr(common["STL_Trend"], common["NDVI_mean"])

print(f"\n全期 NTL vs NDBI: r={r_ntl_ndbi:.3f}, p={p_ntl_ndbi:.4f}")
print(f"全期 NTL vs NDVI: r={r_ntl_ndvi:.3f}, p={p_ntl_ndvi:.4f}")

def sig_label(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"

                                                           
           
                                                    
                                                           
phases = {
                                    :    ("2017-01-01", "2019-08-17"),
                                       : ("2019-08-18", "2021-06-30"),
                                       : ("2021-07-01", "2026-03-31"),
}

print("\n====== 分阶段 NTL vs NDBI 相关性 ======")
phase_corr_rows = []
for phase, (start, end) in phases.items():
    sub = common[
        (common["date"] >= start) & (common["date"] <= end)
    ].dropna(subset=["STL_Trend", "NDBI_mean"])
    if len(sub) >= 5:
        r, p = stats.pearsonr(sub["STL_Trend"], sub["NDBI_mean"])
        sig = sig_label(p)
        print(f"  {phase}: r={r:.3f}, p={p:.4f} {sig}, n={len(sub)}")
        phase_corr_rows.append({"phase": phase, "r": r, "p": p, "n": len(sub), "sig": sig})
    else:
        print(f"  {phase}: 样本不足 (n={len(sub)}), 跳过")

phase_corr_df = pd.DataFrame(phase_corr_rows)
if len(phase_corr_df) > 0:
    print("\n分阶段相关性汇总：")
    print(phase_corr_df.to_string(index=False))

                                                           
         
                                                           
common["ndbi_safe"] = common["NDBI_mean"].clip(lower=0.005)
common["ntl_ndbi_ratio"] = common["STL_Trend"] / common["ndbi_safe"]

annual = common.groupby(common["date"].dt.year).agg(
    NDBI_mean=("NDBI_mean",      "mean"),
    NDVI_mean=("NDVI_mean",      "mean"),
    NTL_mean=("STL_Trend",       "mean"),
    Ratio_mean=("ntl_ndbi_ratio","mean"),
    n=("date",                   "count")
).reset_index()
annual.columns = ["year", "NDBI_mean", "NDVI_mean", "NTL_mean", "Ratio_mean", "n"]
ann_valid = annual[annual["n"] >= 3]

print("\n年度统计（高质量共同期）:")
print(annual.to_string(index=False))

                                                           
        
                                                           
stage_bands = [
    ("2017-01-01", "2019-08-17", "#E8F5E9", "Gambling Boom"),
    ("2019-08-18", "2021-06-30", "#FFEBEE", "Post-818"),
    ("2021-07-01", "2025-10-14", "#E3F2FD", "Second Boom"),
    ("2025-10-15", "2026-06-01", "#FFF8E1", "Post-Sanctions"),
]

def draw_bands(ax, xlim_start="2014-01-01", xlim_end="2026-06-01"):
    for s, e, c, _ in stage_bands:
        ax.axvspan(pd.to_datetime(s), pd.to_datetime(e), color=c, alpha=0.4, zorder=0)
    ax.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
               linestyle="--", linewidth=1.4, alpha=0.9)
    ax.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
               linestyle="--", linewidth=1.4, alpha=0.9)
    ax.set_xlim(pd.to_datetime(xlim_start), pd.to_datetime(xlim_end))

fig = plt.figure(figsize=(16, 16))
gs  = gridspec.GridSpec(4, 1, hspace=0.42)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])
ax3 = fig.add_subplot(gs[2])
ax4 = fig.add_subplot(gs[3])

                             
draw_bands(ax1)
ax1.scatter(df["date"], df["Intensity_Mean"],
            color="#7D3C98", alpha=0.2, s=14, zorder=2, label="Monthly Mean (raw)")
ax1.plot(df["date"], df["STL_Trend"],
         color="#6C3483", linewidth=2.8, zorder=4, label="STL Trend")

                         
pre_mean  = common[common["date"] < "2019-08-18"]["STL_Trend"].mean()
post_mean = common[
    (common["date"] >= "2019-08-18") & (common["date"] <= "2021-06-30")
]["STL_Trend"].mean()

if not np.isnan(pre_mean):
    ax1.axhline(pre_mean,  color="#C0392B", linestyle=":", alpha=0.7, linewidth=1,
                label=f"Pre-818 mean = {pre_mean:.1f}")
if not np.isnan(post_mean):
    ax1.axhline(post_mean, color="#884EA0", linestyle=":", alpha=0.7, linewidth=1,
                label=f"Post-818 mean = {post_mean:.1f}")

ax1.set_ylabel("Intensity Mean  (nW·cm⁻²·sr⁻¹)", fontsize=10)
ax1.set_title("① Nighttime Light STL Trend — Full Period (2014–2026)", fontsize=11, fontweight="bold")
ax1.legend(fontsize=9, loc="upper left")
ax1.grid(True, alpha=0.2)

                               
draw_bands(ax2, "2015-07-01")
ax2.scatter(s2_valid["date"], s2_valid["NDBI_mean"],
            color="#E67E22", alpha=0.4, s=20, zorder=3, label="NDBI (S2 valid months)")
ax2.plot(s2_valid["date"], s2_valid["NDBI_interp"],
         color="#A04000", linewidth=2.2, zorder=4, label="NDBI interpolated")

                 
for _, row in ann_valid.iterrows():
    ax2.scatter(pd.to_datetime(f"{int(row['year'])}-07-01"),
                row["NDBI_mean"], color="#D35400", s=80, zorder=5, marker="D")
if len(ann_valid) > 1:
    ax2.plot(
        [pd.to_datetime(f"{int(y)}-07-01") for y in ann_valid["year"]],
        ann_valid["NDBI_mean"],
        color="#D35400", linewidth=1.5, linestyle="--", alpha=0.7, label="Annual mean trend"
    )

ndbi_min = s2_valid["NDBI_mean"].dropna().min()
ndbi_max = s2_valid["NDBI_mean"].dropna().max()
ax2.text(
    0.02, 0.15,
                                                                                   
                                                                 ,
    transform=ax2.transAxes, fontsize=8.5, va="top",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEF9E7", edgecolor="#E67E22", alpha=0.8)
)

ax2.set_ylabel("NDBI", fontsize=10)
ax2.set_title(
                                                 
                                                                         ,
    fontsize=11, fontweight="bold"
)
ax2.legend(fontsize=9, loc="lower right")
ax2.grid(True, alpha=0.2)

                 
draw_bands(ax3, "2015-07-01")
ax3.scatter(s2_valid["date"], s2_valid["NDVI_mean"],
            color="#27AE60", alpha=0.4, s=20, zorder=3, label="NDVI (S2 valid months)")
ax3.plot(s2_valid["date"], s2_valid["NDVI_interp"],
         color="#1E8449", linewidth=2.2, zorder=4, label="NDVI interpolated")


for _, row in ann_valid.iterrows():
    sub = common[common["date"].dt.year == row["year"]]["NDVI_mean"]
    if len(sub) > 0:
        ax3.scatter(pd.to_datetime(f"{int(row['year'])}-07-01"),
                    sub.mean(), color="#145A32", s=80, zorder=5, marker="D")

sig_ndvi = sig_label(p_ntl_ndvi)
ax3.text(
    0.02, 0.08,
                                                                  
                                                          
                                                                     ,
    transform=ax3.transAxes, fontsize=8.5, va="bottom",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#EAFAF1", edgecolor="#27AE60", alpha=0.8)
)

ax3.set_ylabel("NDVI", fontsize=10)
ax3.set_title(
                                                     
                                                                       ,
    fontsize=11, fontweight="bold"
)
ax3.legend(
    fontsize=9, 
    loc="lower right", 
                                             
    bbox_to_anchor=(0.90, 0.02) 
)
ax3.grid(True, alpha=0.2)

                        
draw_bands(ax4, "2015-07-01")
ax4.scatter(common["date"], common["ntl_ndbi_ratio"],
            color="#2471A3", alpha=0.3, s=20, zorder=3, label="Monthly NTL/NDBI ratio")

ratio_smooth = (
    common.set_index("date")["ntl_ndbi_ratio"]
    .rolling(6, center=True, min_periods=3)
    .mean()
)
ax4.plot(ratio_smooth.index, ratio_smooth.values,
         color="#1A5276", linewidth=2.5, zorder=4, label="6-month rolling mean")

first_idx = True
for _, row in ann_valid.iterrows():
    ax4.scatter(
        pd.to_datetime(f"{int(row['year'])}-07-01"),
        row["Ratio_mean"], color="#1A5276", s=100, zorder=5, marker="D",
        label="Annual mean" if first_idx else "",
    )
    ax4.text(
        pd.to_datetime(f"{int(row['year'])}-07-01"),
        row["Ratio_mean"] + 20,
                                  ,
        ha="center", fontsize=8, color="#1A5276", fontweight="bold"
    )
    first_idx = False

sig_ndbi = sig_label(p_ntl_ndbi)
ax4.text(
    0.17, 0.95,
                                                                                         
                                                      
                                                                ,
    transform=ax4.transAxes, fontsize=9, va="top", color="#1A5276",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#EBF5FB", edgecolor="#2471A3", alpha=0.85)
)

ax4.set_ylabel("NTL / NDBI  (activity intensity\nper unit built area)", fontsize=10)
ax4.set_title(
                                                                   
                                                                       ,
    fontsize=11, fontweight="bold"
)
ax4.legend(fontsize=9, loc="upper left")
ax4.grid(True, alpha=0.2)

fig.suptitle(
                                                                   
                                                                               ,
    fontsize=13, fontweight="bold"
)

plt.savefig(OUT_FIG, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"\n图已保存: {OUT_FIG}")

                                                           
           
                                                           
print("\n========== 论文引用数值 ==========")
print(f"\n【指标范围（S2 有效月份）】")
print(f"  NDBI: {s2_valid['NDBI_mean'].dropna().min():.4f} ~ {s2_valid['NDBI_mean'].dropna().max():.4f}")
print(f"  NDVI: {s2_valid['NDVI_mean'].dropna().min():.4f} ~ {s2_valid['NDVI_mean'].dropna().max():.4f}")

print(f"\n【相关性（高质量共同期 n={len(common)}，2018-12 ~ 2026-03）】")
print(f"  NTL vs NDBI: r={r_ntl_ndbi:.3f}, p={p_ntl_ndbi:.4f} {sig_label(p_ntl_ndbi)}")
print(f"  NTL vs NDVI: r={r_ntl_ndvi:.3f}, p={p_ntl_ndvi:.4f} {sig_label(p_ntl_ndvi)}")
print(f"  注：两者均不显著，支持亮度增长由活动驱动而非基础设施增加")

print(f"\n【NDBI 年度趋势】")
for _, row in ann_valid.iterrows():
    print(f"  {int(row['year'])}: NDBI={row['NDBI_mean']:.4f}, NTL_trend≈{row['NTL_mean']:.1f}, n={int(row['n'])}")

print(f"\n【NTL/NDBI 比值趋势（核心论证）】")
for _, row in ann_valid.iterrows():
    print(f"  {int(row['year'])}: ratio={row['Ratio_mean']:.0f}, n={int(row['n'])}")

if len(phase_corr_df) > 0:
    print(f"\n【分阶段相关性（可写入 Table 注脚）】")
    print(phase_corr_df.to_string(index=False))
