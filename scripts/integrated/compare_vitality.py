import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from scipy import stats
from pathlib import Path

# =========================================================
# 1. Path configuration
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]

GL_FILE   = PROJECT_ROOT / "outputs" / "gl"   / "stats" / "gl_boundary_stats.csv"
SSEZ_FILE = PROJECT_ROOT / "outputs" / "ssez" / "stats" / "ssez_boundary_stats.csv"
SHV_FILE  = PROJECT_ROOT / "outputs" / "shv"  / "stats" / "shv_boundary_stats.csv"

OUT_FIG_DIR = PROJECT_ROOT / "outputs" / "integrated" / "figures"
OUT_STA_DIR = PROJECT_ROOT / "outputs" / "integrated" / "stats"

OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_STA_DIR.mkdir(parents=True, exist_ok=True)

OUT_MAIN       = OUT_FIG_DIR / "comparison_vitality_main.png"
OUT_DIVERGENCE = OUT_FIG_DIR / "comparison_structural_divergence.png"
OUT_MERGED     = OUT_STA_DIR / "comparison_merged.csv"

# =========================================================
# 2. Load data and align all dates to month start
# =========================================================
def load(path):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df.sort_values("date").reset_index(drop=True)

gl   = load(GL_FILE)
ssez = load(SSEZ_FILE)
shv  = load(SHV_FILE)

# =========================================================
# 3. Merge three nodes
# =========================================================
df = (
    gl[["date", "STL_Trend", "Index_2017", "YoY_pct"]]
    .rename(columns={"STL_Trend": "GL_trend", "Index_2017": "GL_idx", "YoY_pct": "GL_yoy"})
    .merge(
        ssez[["date", "STL_Trend", "Index_2017", "YoY_pct"]]
        .rename(columns={"STL_Trend": "SSEZ_trend", "Index_2017": "SSEZ_idx", "YoY_pct": "SSEZ_yoy"}),
        on="date", how="inner",
    )
    .merge(
        shv[["date", "STL_Trend", "Index_2017", "YoY_pct"]]
        .rename(columns={"STL_Trend": "SHV_trend", "Index_2017": "SHV_idx", "YoY_pct": "SHV_yoy"}),
        on="date", how="inner",
    )
    .sort_values("date")
    .reset_index(drop=True)
)

df["year"] = df["date"].dt.year
print(f"Merged rows: {len(df)}, {df['date'].min().date()} ~ {df['date'].max().date()}")

# =========================================================
# 4. Stage definitions
# =========================================================
stages = [
    ("Pre-development", "2014-01-01", "2016-12-31"),
    ("Gambling Boom",   "2017-01-01", "2019-08-17"),
    ("Post-818",        "2019-08-18", "2021-06-30"),
    ("Expansion",       "2021-07-01", "2025-10-14"),
    ("Post-sanctions",  "2025-10-15", "2026-03-31"),
]

# =========================================================
# 5. Key statistics
# =========================================================

# YoY correlation
common_yoy = df.dropna(subset=["GL_yoy", "SSEZ_yoy", "SHV_yoy"])
r_gl_ssez,  p_gl_ssez  = stats.pearsonr(common_yoy["GL_yoy"], common_yoy["SSEZ_yoy"])
r_gl_shv,   p_gl_shv   = stats.pearsonr(common_yoy["GL_yoy"], common_yoy["SHV_yoy"])
r_ssez_shv, p_ssez_shv = stats.pearsonr(common_yoy["SSEZ_yoy"], common_yoy["SHV_yoy"])

# =========================================================
# 818 shock: using Index_2017 as the unified comparison baseline
#   pre818: mean Index_2017 over 2019-02 to 2019-08-17
#   shock_min: lowest Index_2017 in the post-818 window
#   shock_avg: mean Index_2017 during the Post-818 phase
#
#   GL: has a genuine trough (below pre818); report trough drop
#   SSEZ/SHV: trend monotonically increasing; minimum > pre818; labelled as Monotonic Expansion
# =========================================================
pre818_mask  = (df["date"] >= "2019-02-01") & (df["date"] <= "2019-08-17")
post818_mask = (df["date"] >= "2019-08-18") & (df["date"] <= "2021-06-30")

shocks = {}
for idx_col, name in [("GL_idx", "GL"), ("SSEZ_idx", "SSEZ"), ("SHV_idx", "SHV")]:
    pre_v    = df.loc[pre818_mask,  idx_col].mean()
    trough_v = df.loc[post818_mask, idx_col].min()
    avg_v    = df.loc[post818_mask, idx_col].mean()
    trough_dt = df.loc[df.loc[post818_mask, idx_col].idxmin(), "date"]

    drop_pct = (trough_v - pre_v) / abs(pre_v) * 100
    avg_chg  = (avg_v    - pre_v) / abs(pre_v) * 100

    # Determine whether a genuine decline exists (trough below pre818 mean)
    has_trough = trough_v < pre_v

    shocks[name] = {
        "pre_idx":      pre_v,
        "trough_idx":   trough_v,
        "trough_date":  trough_dt,
        "avg_idx":      avg_v,
        "drop_pct":     drop_pct,       # trough change relative to pre818 (negative = decline)
        "avg_chg_pct":  avg_chg,        # stage mean change relative to pre818
        "has_trough":   has_trough,
    }

# 2025 sanctions response (Index_2017 basis; limited sample, early-signal reference only)
pre25_mask  = (df["date"] >= "2025-04-01") & (df["date"] <= "2025-10-14")
post25_mask = df["date"] >= "2025-10-15"

sanc_chg = {}
for idx_col, name in [("GL_idx", "GL"), ("SSEZ_idx", "SSEZ"), ("SHV_idx", "SHV")]:
    pre_v  = df.loc[pre25_mask,  idx_col].mean()
    post_v = df.loc[post25_mask, idx_col].mean()
    if len(df.loc[pre25_mask]) > 0 and len(df.loc[post25_mask]) > 0:
        sanc_chg[name] = (post_v - pre_v) / abs(pre_v) * 100
    else:
        sanc_chg[name] = np.nan

# Print summary statistics to console
print("\nStage-average index values (2017=100):")
print(f"  {'Stage':<22} {'GL(Svc)':>10} {'SSEZ(Ind)':>10} {'SHV(Macro)':>11}")
for name, s, e in stages:
    sub = df[(df["date"] >= s) & (df["date"] <= e)]
    if len(sub) > 0:
        print(f"  {name:<22} {sub['GL_idx'].mean():>10.0f}"
              f" {sub['SSEZ_idx'].mean():>10.0f}"
              f" {sub['SHV_idx'].mean():>11.0f}")

print("\n818 shock (Index_2017 basis):")
for name, v in shocks.items():
    if v["has_trough"]:
        print(f"  {name}: trough {v['drop_pct']:.1f}% @ {v['trough_date'].strftime('%Y-%m')}"
              f"  (pre={v['pre_idx']:.0f}, trough={v['trough_idx']:.0f})")
    else:
        print(f"  {name}: Monotonic Expansion (+{v['avg_chg_pct']:.1f}% avg)"
              f"  (pre={v['pre_idx']:.0f}, post_avg={v['avg_idx']:.0f})")

print("\n2025 sanctions change (through 2026-03, early signal):")
for name, v in sanc_chg.items():
    if not np.isnan(v):
        print(f"  {name}: {v:+.1f}%")
    else:
        print(f"  {name}: Insufficient data")

print(f"\nYoY correlation (n={len(common_yoy)}):")
print(f"  GL ↔ SSEZ:  r={r_gl_ssez:.3f},  p={p_gl_ssez:.4f}")
print(f"  GL ↔ SHV:   r={r_gl_shv:.3f},  p={p_gl_shv:.4f}")
print(f"  SSEZ ↔ SHV: r={r_ssez_shv:.3f}, p={p_ssez_shv:.4f}")

# =========================================================
# 6. Visualization helpers
# =========================================================
COLORS = {"GL": "#7D3C98", "SSEZ": "#1E8449", "SHV": "#1A5276"}
LABELS = {
    "GL":   "Golden Lions (Service / Informal)",
    "SSEZ": "SSEZ Boundary (Industrial)",
    "SHV":  "Sihanoukville Province (Macro)",
}

stage_bands = [
    ("2017-01-01", "2019-08-17", "#E8F5E9", "Gambling Boom"),
    ("2019-08-18", "2021-06-30", "#FFEBEE", "Post-818"),
    ("2021-07-01", "2025-10-14", "#E3F2FD", "Industrial Expansion"),
    ("2025-10-15", "2026-06-01", "#FFF8E1", "Post-Sanctions"),
]

def draw_bands(ax, xl="2014-01-01", xr="2026-06-01"):
    for s, e, c, _ in stage_bands:
        ax.axvspan(pd.to_datetime(s), pd.to_datetime(e), color=c, alpha=0.38, zorder=0)
    ax.axvline(pd.to_datetime("2019-08-18"), color="#C0392B",
               linestyle="--", linewidth=1.5, alpha=0.9, zorder=3)
    ax.axvline(pd.to_datetime("2025-10-15"), color="darkorange",
               linestyle="--", linewidth=1.5, alpha=0.9, zorder=3)
    ax.set_xlim(pd.to_datetime(xl), pd.to_datetime(xr))

# =========================================================
# Figure 1: three-track comparison (main panel)
# =========================================================
fig = plt.figure(figsize=(16, 15))
gs  = gridspec.GridSpec(3, 1, hspace=0.42)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])
ax3 = fig.add_subplot(gs[2])

# --- ax1: normalized index
#     Annotations changed to multiples (Nx); disclaimer added to title
# ---
draw_bands(ax1)
ax1.axhline(100, color="black", linewidth=1, linestyle=":", alpha=0.5)

for col, name in [("GL_idx", "GL"), ("SSEZ_idx", "SSEZ"), ("SHV_idx", "SHV")]:
    ax1.plot(df["date"], df[col], color=COLORS[name], linewidth=2.8,
             label=LABELS[name], zorder=4)
    last = df[df[col].notna()].iloc[-1]
    # Annotated as multiples rather than absolute index values to avoid magnitude illusion
    multiple = last[col] / 100
    ax1.annotate(
        f"{multiple:.1f}x",
        xy=(last["date"], last[col]),
        xytext=(8, 0), textcoords="offset points",
        fontsize=9, color=COLORS[name], fontweight="bold",
    )

y_top = df[["GL_idx", "SSEZ_idx", "SHV_idx"]].max().max()
ax1.text(pd.to_datetime("2019-09-01"), y_top * 0.92,
         "818\nShock", color="#C0392B", fontsize=9, fontweight="bold")
ax1.text(pd.to_datetime("2025-11-01"), y_top * 0.84,
         "2025\nSanctions", color="darkorange", fontsize=9, fontweight="bold")

for s, e, c, lbl in stage_bands:
    mid = pd.to_datetime(s) + (pd.to_datetime(e) - pd.to_datetime(s)) / 2
    ax1.text(mid, 20, lbl, ha="center", fontsize=7.5, color="#555", style="italic")

ax1.set_ylabel("Index (2017 = 100)", fontsize=11)
ax1.set_title(
    "Economic Vitality: Relative Trajectories of Three Sectors\n"
    "All indices normalized to 2017=100, based on STL-deseasonalized trend\n"
    "Note: Index values reflect internal growth/decline relative to each sector's 2017 baseline,\n"
    "not absolute cross-sector magnitude comparison  (annotations show multiples of 2017 level)",
    fontsize=10, fontweight="bold",
)
ax1.legend(loc="upper left", fontsize=10)
ax1.grid(True, alpha=0.2)

# --- ax2: YoY comparison ---
draw_bands(ax2)
ax2.axhline(0, color="black", linewidth=1, alpha=0.7)

for col, name in [("GL_yoy", "GL"), ("SSEZ_yoy", "SSEZ"), ("SHV_yoy", "SHV")]:
    ax2.plot(df["date"], df[col], color=COLORS[name], linewidth=2.2,
             label=f"{name} YoY%", zorder=4, alpha=0.9)

ax2.text(
    0.01, 0.97,
    f"YoY correlations (n={len(common_yoy)}):\n"
    f"  GL ↔ SSEZ:  r={r_gl_ssez:.2f}  (p={p_gl_ssez:.3f})\n"
    f"  GL ↔ SHV:   r={r_gl_shv:.2f}  (p={p_gl_shv:.3f})\n"
    f"  SSEZ ↔ SHV: r={r_ssez_shv:.2f}  (p={p_ssez_shv:.3f})",
    transform=ax2.transAxes, fontsize=8.5, va="top", fontfamily="monospace",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#ccc", alpha=0.9),
)

ax2.set_ylabel("YoY Change %\n(STL trend-based)", fontsize=11)
ax2.set_title(
    "Year-on-Year Growth Rate Comparison — Structural Synchrony and Divergence",
    fontsize=12, fontweight="bold",
)
ax2.set_ylim(-60, 140)
ax2.legend(loc="upper right", fontsize=10)
ax2.grid(True, alpha=0.2)

# --- ax3: policy shock bar chart
#     818 bars: use trough drop for nodes with a genuine trough, avg_chg otherwise (annotated accordingly)
#     Color coding: decline = solid dark bar; expansion = light hatched bar
# ---
x = np.arange(3)
names_bar = [
    "Golden Lions\n(Service / Informal)",
    "SSEZ\n(Industrial)",
    "Province\n(Macro)",
]
node_keys  = ["GL", "SSEZ", "SHV"]
cols_bar   = [COLORS[k] for k in node_keys]

# 818 bars: use drop_pct for nodes with a genuine trough, avg_chg_pct otherwise (still positive, color-coded)
chg_818    = [shocks[k]["drop_pct"] if shocks[k]["has_trough"]
              else shocks[k]["avg_chg_pct"]
              for k in node_keys]
chg_2025   = [sanc_chg.get(k, 0) for k in node_keys]

w = 0.32
b1 = ax3.bar(x - w / 2, chg_818,  w, color=cols_bar, alpha=0.85,
             label="818 Policy Shock (trough drop if exists, else Post-818 avg change)",
             edgecolor="white")
b2 = ax3.bar(x + w / 2, chg_2025, w, color=cols_bar, alpha=0.45,
             label="2025 Sanctions (post vs pre, early signal, data through Mar 2026)",
             edgecolor="white", hatch="///")

for bar, val, key in zip(b1, chg_818, node_keys):
    v = shocks[key]
    if v["has_trough"]:
        label_str = f"{val:.1f}%\n(trough)"
    else:
        label_str = f"+{val:.1f}%\n(no trough)"
    ax3.text(
        bar.get_x() + bar.get_width() / 2,
        val - 1.5 if val < 0 else val + 0.5,
        label_str,
        ha="center", va="top" if val < 0 else "bottom",
        fontsize=8.5, fontweight="bold",
    )

for bar, val in zip(b2, chg_2025):
    if not np.isnan(val):
        ax3.text(
            bar.get_x() + bar.get_width() / 2,
            val - 1.5 if val < 0 else val + 0.5,
            f"{val:+.1f}%",
            ha="center", va="top" if val < 0 else "bottom",
            fontsize=8.5, fontweight="bold",
        )

ax3.axhline(0, color="black", linewidth=1)
ax3.set_xticks(x)
ax3.set_xticklabels(names_bar, fontsize=11)
ax3.set_ylabel("Change from Pre-Shock Baseline, Index pts (%)", fontsize=11)
ax3.set_title(
    "Policy Shock Response Comparison (Index_2017 basis — same scale across sectors)\n"
    "818: trough drop (if any) vs pre-818 avg · 2025 Sanctions: early signal, data through Mar 2026",
    fontsize=11, fontweight="bold",
)
ax3.legend(fontsize=8.5, loc="lower right")
ax3.grid(True, alpha=0.2, axis="y")

all_vals = [v for v in chg_818 + chg_2025 if not np.isnan(v)]
ax3.set_ylim(min(min(all_vals) - 8, -5), max(all_vals) + 16)

fig.suptitle(
    "Sihanoukville Economic Vitality: Three-Sector Comparison\n"
    "Service/Informal (GL Mean) · Industrial (SSEZ Sum) · Macro (Province Sum)\n"
    "All metrics: VIIRS nighttime light, STL-deseasonalized, 2017=100",
    fontsize=13, fontweight="bold",
)

plt.savefig(OUT_MAIN, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {OUT_MAIN}")

# =========================================================
# Figure 2: structural divergence
# =========================================================
fig2, axes2 = plt.subplots(1, 2, figsize=(16, 7))

# Left: stage-average bar chart
ax_l = axes2[0]
stage_names = [s for s, _, _ in stages]
gl_stage   = [df[(df["date"] >= s) & (df["date"] <= e)]["GL_idx"].mean()   for _, s, e in stages]
ssez_stage = [df[(df["date"] >= s) & (df["date"] <= e)]["SSEZ_idx"].mean() for _, s, e in stages]
shv_stage  = [df[(df["date"] >= s) & (df["date"] <= e)]["SHV_idx"].mean()  for _, s, e in stages]

x2 = np.arange(len(stages))
w2 = 0.25
bars1 = ax_l.bar(x2 - w2, gl_stage,   w2, label=LABELS["GL"],   color=COLORS["GL"],   alpha=0.85, edgecolor="white")
bars2 = ax_l.bar(x2,       ssez_stage, w2, label=LABELS["SSEZ"], color=COLORS["SSEZ"], alpha=0.85, edgecolor="white")
bars3 = ax_l.bar(x2 + w2, shv_stage,  w2, label=LABELS["SHV"],  color=COLORS["SHV"],  alpha=0.85, edgecolor="white")

for bars, vals in [(bars1, gl_stage), (bars2, ssez_stage), (bars3, shv_stage)]:
    for bar, val in zip(bars, vals):
        if not np.isnan(val):
            ax_l.text(bar.get_x() + bar.get_width() / 2, val + 5,
                      f"{val:.0f}", ha="center", va="bottom", fontsize=8)

ax_l.axhline(100, color="black", linestyle=":", alpha=0.5)
ax_l.set_xticks(x2)
ax_l.set_xticklabels([s.replace(" ", "\n") for s in stage_names], fontsize=9)
ax_l.set_ylabel("Index (2017 = 100)", fontsize=11)
ax_l.set_title(
    "Stage-Average Index Comparison\nThree Sectors by Policy Phase",
    fontsize=11, fontweight="bold",
)
ax_l.legend(fontsize=8, loc="upper left")
ax_l.grid(True, alpha=0.2, axis="y")

# Right: GL vs SSEZ YoY scatter plot
ax_r = axes2[1]
yoy_plot             = common_yoy.copy()
yoy_plot["year_num"] = yoy_plot["date"].dt.year

sc = ax_r.scatter(
    yoy_plot["SSEZ_yoy"], yoy_plot["GL_yoy"],
    c=yoy_plot["year_num"], cmap="plasma", s=50, alpha=0.75, zorder=3,
)
plt.colorbar(sc, ax=ax_r, label="Year")

slope, intercept, r, p, _ = stats.linregress(yoy_plot["SSEZ_yoy"], yoy_plot["GL_yoy"])
x_line = np.linspace(yoy_plot["SSEZ_yoy"].min(), yoy_plot["SSEZ_yoy"].max(), 100)
ax_r.plot(x_line, slope * x_line + intercept, color="#C0392B",
          linewidth=2, linestyle="--", label=f"OLS fit: r={r:.2f}, p={p:.3f}")

ax_r.axhline(0, color="black", linewidth=0.8, alpha=0.5)
ax_r.axvline(0, color="black", linewidth=0.8, alpha=0.5)
ax_r.set_xlabel("SSEZ Industrial YoY (%)", fontsize=11)
ax_r.set_ylabel("Golden Lions Service YoY (%)", fontsize=11)
ax_r.set_title(
    "Service vs Industrial Co-movement\nGL YoY vs SSEZ YoY (color = year)",
    fontsize=11, fontweight="bold",
)
ax_r.legend(fontsize=9)
ax_r.grid(True, alpha=0.2)

# Annotation: flag possible common macro-trend confound
ax_r.text(
    0.05, 0.95,
    f"Co-movement: r={r_gl_ssez:.2f} (p={p_gl_ssez:.3f})\n"
    f"Suggests partial demand linkage\nbetween service and industrial sectors.\n"
    f"Note: High correlation may partially\nreflect common macro growth trends\n"
    f"in Sihanoukville rather than direct\ncausal spillover.",
    transform=ax_r.transAxes, fontsize=8.5, va="top",
    bbox=dict(boxstyle="round,pad=0.35", facecolor="#F9F9F9",
              edgecolor="#aaa", alpha=0.88),
)

fig2.suptitle(
    "Structural Divergence Analysis\nHow Three Sectors Decouple Under Policy Shocks",
    fontsize=13, fontweight="bold",
)
plt.tight_layout()
plt.savefig(OUT_DIVERGENCE, dpi=300, bbox_inches="tight")
plt.close(fig2)
print(f"Saved: {OUT_DIVERGENCE}")

# =========================================================
# 7. Save merged data
# =========================================================
df.to_csv(OUT_MERGED, index=False, encoding="utf-8-sig")

# =========================================================
# 8. Paper citation value summary
# =========================================================
print("\n========== Paper citation values ==========")
print("\n[Stage-average index values (2017=100)]")
print(f"  {'Stage':<22} {'GL(Svc)':>10} {'SSEZ(Ind)':>10} {'SHV(Macro)':>11}")
for name, s, e in stages:
    sub = df[(df["date"] >= s) & (df["date"] <= e)]
    if len(sub) > 0:
        print(f"  {name:<22} {sub['GL_idx'].mean():>10.0f}"
              f" {sub['SSEZ_idx'].mean():>10.0f}"
              f" {sub['SHV_idx'].mean():>11.0f}")

print("\n[818 shock (Index_2017 basis, unified scale)]")
for name, v in shocks.items():
    if v["has_trough"]:
        print(f"  {name}: trough drop {v['drop_pct']:.1f}% @ {v['trough_date'].strftime('%Y-%m')}"
              f"  (pre={v['pre_idx']:.0f} → trough={v['trough_idx']:.0f})")
    else:
        print(f"  {name}: Monotonic Expansion, avg +{v['avg_chg_pct']:.1f}%"
              f"  (pre={v['pre_idx']:.0f} → post_avg={v['avg_idx']:.0f})")

print("\n[2025 sanctions change (through 2026-03, early signal)]")
for name, v in sanc_chg.items():
    if not np.isnan(v):
        print(f"  {name}: {v:+.1f}%")
    else:
        print(f"  {name}: Insufficient data")

print("\n[YoY correlation]")
print(f"  GL ↔ SSEZ:  r={r_gl_ssez:.3f}, p={p_gl_ssez:.4f}")
print(f"  GL ↔ SHV:   r={r_gl_shv:.3f},  p={p_gl_shv:.4f}")
print(f"  SSEZ ↔ SHV: r={r_ssez_shv:.3f}, p={p_ssez_shv:.4f}")

print("\nOutput files:")
print(f"  {OUT_MAIN}")
print(f"  {OUT_DIVERGENCE}")
print(f"  {OUT_MERGED}")
