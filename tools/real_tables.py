#!/usr/bin/env python3
"""Tables for the real-applicant track (evolve_real.py): gate statistics and subgroup gaps.

    python tools/real_tables.py results/shift-real   # writes tables.md and tables.json there
"""
from __future__ import annotations

import glob
import gzip
import json
import math
import os
import statistics
import sys

Z = 1.959963984540054
ARMS_MAIN = ("degraded", "oracle", "manual", "no_gate", "stale_gate", "dual")


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z / d * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def main(d):
    cells = []
    for f in sorted(glob.glob(os.path.join(d, "cell-*.json.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            cells.append(json.load(fh))
    n_cells = len(cells)
    out = {"cells": n_cells}

    # gate statistics over all cells
    g = {}
    for arm in ("dual", "no_gate", "stale_gate", "global_only", "local_only"):
        prop = sum(c["arms"][arm]["proposed"] for c in cells)
        adm = sum(c["arms"][arm]["admitted"] for c in cells)
        harm = sum(c["arms"][arm]["false_admissions_on_H_val"] for c in cells)
        miss10 = sum(c["arms"][arm]["miss_rate"] > 0.10 for c in cells)
        g[arm] = {"proposed": prop, "admitted": adm, "harmful": harm, "runs_miss_gt_10": miss10}
    out["gate"] = g

    # recovery: dual within oracle error on held-out, per family/severity
    rec = {}
    for c in cells:
        k = f'{c["family"]}-{c["severity"]}'
        o, du = c["arms"]["oracle"], c["arms"]["dual"]
        ok = du["harness_digest"] == o["harness_digest"]
        rec.setdefault(k, []).append(ok)
    out["dual_reached_oracle_harness"] = {k: f"{sum(v)}/{len(v)}" for k, v in sorted(rec.items())}

    # pooled subgroup error rates on the held-out window, per arm
    sub = {}
    for arm in ARMS_MAIN:
        agg = {}
        for c in cells:
            for grp, m in c["arms"][arm]["subgroups"].items():
                a = agg.setdefault(grp, {"fp_k": 0, "fp_n": 0, "miss_k": 0, "miss_n": 0})
                a["fp_k"] += m["fp"]["k"]; a["fp_n"] += m["fp"]["n"]
                a["miss_k"] += m["miss"]["k"]; a["miss_n"] += m["miss"]["n"]
        sub[arm] = {grp: {"fp": a["fp_k"] / a["fp_n"] if a["fp_n"] else 0.0,
                          "fp_ci": wilson(a["fp_k"], a["fp_n"]),
                          "miss": a["miss_k"] / a["miss_n"] if a["miss_n"] else 0.0,
                          "miss_ci": wilson(a["miss_k"], a["miss_n"]),
                          "fp_n": a["fp_n"], "miss_n": a["miss_n"]}
                    for grp, a in agg.items()}
    out["subgroups_pooled"] = sub

    # per-cell gap (female - male, under25 - 25plus) relative to oracle: mean and range
    gaps = {}
    for arm in ARMS_MAIN:
        for pair in (("female", "male"), ("under25", "25plus")):
            for metric in ("fp", "miss"):
                xs = []
                for c in cells:
                    s, o = c["arms"][arm]["subgroups"], c["arms"]["oracle"]["subgroups"]
                    gap = s[pair[0]][metric]["rate"] - s[pair[1]][metric]["rate"]
                    ogap = o[pair[0]][metric]["rate"] - o[pair[1]][metric]["rate"]
                    xs.append(gap - ogap)
                key = f"{arm}:{pair[0]}-{pair[1]}:{metric}"
                gaps[key] = {"mean_excess_gap": statistics.fmean(xs),
                             "max_abs_excess_gap": max(abs(x) for x in xs)}
    out["excess_gap_vs_oracle"] = gaps

    # flag rate and realised bad-credit rate among flagged / cleared (oracle harness, pooled)
    fl = {"flagged_bad": [0, 0], "cleared_bad": [0, 0]}
    for c in cells:
        o = c["arms"]["oracle"]
        fl["flagged_bad"][0] += o["bad_rate_flagged"]["k"]; fl["flagged_bad"][1] += o["bad_rate_flagged"]["n"]
        fl["cleared_bad"][0] += o["bad_rate_cleared"]["k"]; fl["cleared_bad"][1] += o["bad_rate_cleared"]["n"]
    out["oracle_bad_rate"] = {k: v[0] / v[1] if v[1] else 0.0 for k, v in fl.items()}
    out["eval_unique_applicants"] = sorted({c["eval_unique_applicants"] for c in cells})
    out["pool_unique_applicants"] = sorted({c["pool_unique_applicants"] for c in cells})

    with open(os.path.join(d, "tables.json"), "w") as fh:
        json.dump(out, fh, indent=1)

    L = [f"# Real-applicant track — {n_cells} runs\n", "## Gate\n",
         "| Arm | Proposed | Admitted | Harmful (H_val) | Runs with missed flags > 10% |",
         "|---|---|---|---|---|"]
    for arm, v in g.items():
        L.append(f"| {arm} | {v['proposed']} | {v['admitted']} | {v['harmful']} | {v['runs_miss_gt_10']} |")
    L += ["", "## Dual loop reached the oracle harness\n", "| Cell | Seeds |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in out["dual_reached_oracle_harness"].items()]
    L += ["", "## Held-out error by subgroup (pooled over runs, 95% Wilson)\n",
          "| Arm | Group | FP rate | Missed-flag rate |", "|---|---|---|---|"]
    for arm in ARMS_MAIN:
        for grp in ("female", "male", "under25", "25plus"):
            s = sub[arm][grp]
            L.append(f"| {arm} | {grp} | {s['fp']:.3f} [{s['fp_ci'][0]:.3f}, {s['fp_ci'][1]:.3f}] | "
                     f"{s['miss']:.3f} [{s['miss_ci'][0]:.3f}, {s['miss_ci'][1]:.3f}] |")
    L += ["", "## Gap between groups beyond the oracle's own gap (per run)\n",
          "| Arm | Pair | Metric | Mean excess gap | Max abs excess gap |", "|---|---|---|---|---|"]
    for k, v in gaps.items():
        arm, pair, metric = k.split(":")
        L.append(f"| {arm} | {pair} | {metric} | {v['mean_excess_gap']:+.4f} | {v['max_abs_excess_gap']:.4f} |")
    L += ["", f"Oracle harness, realised bad-credit rate: flagged {out['oracle_bad_rate']['flagged_bad']:.3f}, "
          f"cleared {out['oracle_bad_rate']['cleared_bad']:.3f}.",
          f"Unique applicants per run: pool {out['pool_unique_applicants']}, held-out {out['eval_unique_applicants']}."]
    with open(os.path.join(d, "tables.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/shift-real")
