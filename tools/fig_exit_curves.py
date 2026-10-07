"""fig_exit_curves.py — Figure: exit cost around T0 for the pool-depth cases.

Reads results/defi/micro/exit_curves.csv (written by
`tools/microstructure.py exit-curves`) and writes exit_curves.pdf / .png next to it.

    python tools/microstructure.py exit-curves --cases H01 H02 H04
    python tools/fig_exit_curves.py

Top row: cost of exiting $1M and $50M of the risky asset, log scale; values <= 0
(the pool pays a premium) are drawn at the floor. Bottom row: risky asset's share
of the pool. Dashed line: the 3% MAX_EXIT_DISCOUNT gate. Grid is 12h, so intraday
peaks are understated. Requires matplotlib.
"""
import os
import csv, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "defi", "micro")
SRC = os.path.join(OUT, "exit_curves.csv")
with open(SRC, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
data = collections.defaultdict(lambda: collections.defaultdict(list))
share = collections.defaultdict(list)
for r in rows:
    h = float(r["hours_from_t0"]); s = int(r["size_usd"])
    d = float(r["exit_discount"]) * 100 if r["exit_discount"] not in ("", "None") else None
    data[r["case"]][s].append((h, d))
    if s == 1_000_000 and r["risky_share_of_pool"] not in ("", "None"):
        share[r["case"]].append((h, float(r["risky_share_of_pool"]) * 100))

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e7e6e2", "#fcfcfb"
C1, C50 = "#6da7ec", "#184f95"          # validated sequential pair (blue 300 / 600)
CASES = [("H01", "H01 · UST → 3CRV", "UST share of pool"),
         ("H02", "H02 · stETH → ETH", "stETH share of pool"),
         ("H04", "H04 · USDC → DAI (3pool)", "USDC share of pool")]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.linewidth": 0.6, "figure.facecolor": SURF, "axes.facecolor": SURF})
fig, ax = plt.subplots(2, 3, figsize=(7.2, 4.4), sharex=True,
                       gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.12, "wspace": 0.45})
pct = FuncFormatter(lambda v, _: (f"{v:.2f}%" if v < 0.1 else f"{v:.1f}%" if v < 1 else f"{v:.0f}%"))
for j, (cid, title, slabel) in enumerate(CASES):
    a = ax[0, j]
    for size, col, lab in ((1_000_000, C1, "$1M"), (50_000_000, C50, "$50M")):
        pts = sorted(p for p in data[cid][size] if p[1] is not None)
        xs = [p[0] for p in pts]; ys = [max(p[1], 0.005) for p in pts]   # premia (<=0) drawn at floor
        a.plot(xs, ys, color=col, lw=1.6, solid_capstyle="round", zorder=3)
        dy = 6 if size == 50_000_000 else -6
        a.annotate(lab, (xs[-1], ys[-1]), xytext=(3, dy), textcoords="offset points",
                   color=INK2, fontsize=7, va="center")
    a.set_yscale("log"); a.set_ylim(0.0025, 150)
    a.yaxis.set_major_locator(FixedLocator([0.01, 0.1, 1, 3, 10, 100]))
    a.yaxis.set_major_formatter(pct); a.yaxis.set_minor_locator(FixedLocator([]))
    a.axhline(3, color=INK2, lw=0.8, ls=(0, (4, 3)), zorder=2)
    if j == 0:
        a.text(-330, 3.6, "gate: 3%", color=INK2, fontsize=7)
        a.text(-330, 0.0029, "floor = premium", color=INK2, fontsize=6.5)
    a.axvline(0, color=INK, lw=0.8, zorder=2)
    a.text(4, 70, "T0", color=INK, fontsize=7)
    a.set_title(title, fontsize=8.5, color=INK, loc="left", pad=4)
    a.grid(axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
    for s in ("top", "right"): a.spines[s].set_visible(False)
    if j == 0: a.set_ylabel("exit cost (log)")
    b = ax[1, j]
    pts = sorted(share[cid]); b.plot([p[0] for p in pts], [p[1] for p in pts], color=INK2, lw=1.4)
    b.axvline(0, color=INK, lw=0.8)
    b.set_ylim(0, 100); b.yaxis.set_major_locator(FixedLocator([0, 50, 100]))
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    b.grid(axis="y", color=GRID, lw=0.6); b.set_axisbelow(True)
    for s in ("top", "right"): b.spines[s].set_visible(False)
    b.set_xlabel("hours from T0"); b.set_xlim(-340, 175)
    b.xaxis.set_major_locator(FixedLocator([-336, -168, 0, 168]))
    b.text(-330, 88, slabel, color=INK2, fontsize=7)
pdf, png = os.path.join(OUT, "exit_curves.pdf"), os.path.join(OUT, "exit_curves.png")
fig.savefig(pdf, bbox_inches="tight"); fig.savefig(png, dpi=220, bbox_inches="tight")
print("wrote", os.path.normpath(pdf), "and", os.path.normpath(png))
