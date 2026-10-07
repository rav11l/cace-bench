"""fig_manipulation.py — Figure: H12, cost of moving the MAMO oracle vs what it lets you borrow.

Reads results/defi/micro/manipulation_h12.csv (written by
`tools/microstructure.py manipulation`) and writes manipulation_h12.pdf / .png next to it.

    python tools/microstructure.py manipulation
    python tools/fig_manipulation.py

x: target spot multiple k (spot after the buy / spot at T0), log scale.
y: USD, log scale. "spend" is the quote paid to push spot to k x across the pools
found at T0, in one block, with pool fees and no arbitrage refill. "borrowable"
is collateral factor x bought MAMO x new price, with and without the 20M MAMO supply cap
(4.85M already supplied at T0); the two lines coincide until the cap binds.
Break-even (borrowable = spend) is interpolated linearly in log k. Requires matplotlib.
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "defi", "micro")
SRC = os.path.join(OUT, "manipulation_h12.csv")
with open(SRC, newline="", encoding="utf-8") as f:
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
rows.sort(key=lambda r: r["k"])
K = [r["k"] for r in rows]


def breakeven(net):
    """First k where net turns positive, linear in log k; None if never."""
    for a, b in zip(rows, rows[1:]):
        if a[net] < 0 <= b[net]:
            t = -a[net] / (b[net] - a[net])
            return math.exp(math.log(a["k"]) + t * (math.log(b["k"]) - math.log(a["k"])))
    return K[0] if rows[0][net] >= 0 else None


INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e7e6e2", "#fcfcfb"
C_CAP, C_NOCAP = "#184f95", "#6da7ec"          # same validated blue pair as fig_exit_curves
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.linewidth": 0.6, "figure.facecolor": SURF, "axes.facecolor": SURF})
fig, ax = plt.subplots(figsize=(3.5, 2.7))
series = [("quote_spent_usd", INK2, "spend to move spot", 1.4),
          ("borrowable_uncapped_usd", C_NOCAP, "borrowable, no cap", 1.6),
          ("borrowable_capped_usd", C_CAP, "borrowable, supply cap", 1.6)]
for col, colr, lab, lw in series:
    ys = [r[col] for r in rows]
    ax.plot(K, ys, color=colr, lw=lw, solid_capstyle="round", zorder=3)
    ax.plot(K, ys, "o", ms=3.2, color=colr, mec=SURF, mew=0.8, zorder=4)
    dy = {"quote_spent_usd": -7, "borrowable_uncapped_usd": 7, "borrowable_capped_usd": -1}[col]
    ax.annotate(lab, (K[-1], ys[-1]), xytext=(4, dy), textcoords="offset points",
                color=INK2, fontsize=6.8, va="center")

for net, colr, name in (("net_uncapped_usd", C_NOCAP, "no cap"), ("net_capped_usd", C_CAP, "cap")):
    kb = breakeven(net)
    if kb:
        ax.axvline(kb, color=colr, lw=0.8, ls=(0, (3, 2)), zorder=2)
        ax.text(kb * 1.04, 2.6e4, f"break-even\n{name}: k≈{kb:.1f}", color=INK2, fontsize=6.3, va="bottom")
        print(f"break-even ({name}): k ~ {kb:.2f}")

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1.3, 44); ax.set_ylim(2e4, 8e6)
ax.xaxis.set_major_locator(FixedLocator([2, 3, 5, 10, 20, 40]))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}×"))
ax.xaxis.set_minor_locator(FixedLocator([]))
ax.yaxis.set_major_locator(FixedLocator([3e4, 1e5, 3e5, 1e6, 3e6]))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1e6:g}M" if v >= 1e6 else f"${v/1e3:g}k"))
ax.yaxis.set_minor_locator(FixedLocator([]))
ax.set_xlabel("spot multiple k (spot after buy / spot at T0)")
ax.set_ylabel("USD (log)")
ax.set_title("H12 · MAMO: cost to move the oracle vs borrowable", fontsize=8.5, color=INK, loc="left", pad=4)
ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
pdf, png = os.path.join(OUT, "manipulation_h12.pdf"), os.path.join(OUT, "manipulation_h12.png")
fig.savefig(pdf, bbox_inches="tight"); fig.savefig(png, dpi=220, bbox_inches="tight")
print("wrote", os.path.normpath(pdf), "and", os.path.normpath(png))
