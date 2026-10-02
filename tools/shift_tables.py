#!/usr/bin/env python3
"""Tables for the regulatory-shift track: reads results/shift/cell-*.json, writes
results/shift/tables.md and results/shift/tables.json. Every figure in the paper's
Section 9 is taken from these two files."""
import glob
import gzip
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evolve import mean_ci  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else "results/shift"
cells = [json.load(gzip.open(f, "rt")) for f in sorted(glob.glob(os.path.join(D, "cell-*.json.gz")))]
ARMS = ["healthy", "degraded", "oracle", "manual", "no_gate", "stale_gate",
        "global_only", "local_only", "local_only_cm", "dual"]
FAM = ["thr", "scope", "struct"]
SEV = ["low", "mid", "high"]


def recovery_window(a, oracle):
    """First window from which the arm's true error stays within 1 pp of the oracle's."""
    w, o = a["window_err"], oracle["window_err"]
    for i in range(len(w)):
        if all(w[j] <= o[j] + 0.01 for j in range(i, len(w))):
            return i
    return len(w)


def pct(m):
    return f"{m*100:.1f}"


def fmt(xs, scale=100, nd=1):
    m, ci = mean_ci(xs)
    return f"{m*scale:.{nd}f} [{ci[0]*scale:.{nd}f}, {ci[1]*scale:.{nd}f}]", m, ci


out = {"main": {}, "grid": {}, "gate": {}, "rejection_example": None}
md = []

# --- main table: mid severity, each family -----------------------------------
for fam in FAM:
    sub = [c for c in cells if c["family"] == fam and c["severity"] == "mid"]
    md.append(f"\n### {fam} / mid  (seeds = {len(sub)})\n")
    md.append("| arm | FP % | miss % | recall % | regress. on C_E % | excess adapt. errors | "
              "recovery window | proposed | admitted | rejected (no gain / regression) | "
              "false adm. (H_val) |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    out["main"][fam] = {}
    for arm in ARMS:
        xs = [c["arms"][arm] for c in sub]
        fp, fpm, fpci = fmt([x["fp_rate"] for x in xs])
        mi, mim, mici = fmt([x["miss_rate"] for x in xs])
        rc, rcm, rcci = fmt([x["recall"] for x in xs])
        rg, rgm, rgci = fmt([x["regression_rate"] for x in xs])
        ex, exm, exci = fmt([x["excess_adapt_errors"] for x in xs], scale=1, nd=0)
        rw = [recovery_window(c["arms"][arm], c["arms"]["oracle"]) for c in sub]
        rwm, rwci = mean_ci(rw)
        prop = sum(x["proposed"] for x in xs)
        adm = sum(x["admitted"] for x in xs)
        rej = {}
        for x in xs:
            for k, v in x["rejected"].items():
                rej[k] = rej.get(k, 0) + v
        fa = sum(x["false_admissions_on_H_val"] for x in xs)
        rej_s = (f"{rej.get('no_significant_improvement', 0)} / {rej.get('regression_on_C', 0)}"
                 if arm != "no_gate" else f"{rej.get('no_trace_improvement', 0)} (trace check)")
        md.append(f"| {arm} | {fp} | {mi} | {rc} | {rg} | {ex} | {rwm:.1f} | {prop} | {adm} | "
                  f"{rej_s} | {fa} |")
        out["main"][fam][arm] = {
            "fp": [fpm, fpci], "miss": [mim, mici], "recall": [rcm, rcci],
            "regression": [rgm, rgci], "excess": [exm, exci], "recovery_window": [rwm, rwci],
            "proposed": prop, "admitted": adm, "rejected": rej, "false_admissions": fa,
            "n_clear_per_seed": statistics.fmean(x["fp"] + x["tn"] for x in xs),
            "n_flag_per_seed": statistics.fmean(x["tp"] + x["fn"] for x in xs),
            "C_E_per_seed": statistics.fmean(x["C_E"] for x in xs),
            "max_miss": max(x["miss_rate"] for x in xs),
        }

# --- full grid: FP and miss for the key arms ---------------------------------
md.append("\n### Full grid, mean over seeds: FP % / miss %\n")
key = ["degraded", "no_gate", "global_only", "local_only", "dual", "oracle"]
md.append("| family | severity | " + " | ".join(key) + " |")
md.append("|---|---|" + "---|" * len(key))
for fam in FAM:
    for sev in SEV:
        sub = [c for c in cells if c["family"] == fam and c["severity"] == sev]
        row = []
        out["grid"].setdefault(fam, {})[sev] = {}
        for arm in key:
            fp = statistics.fmean(c["arms"][arm]["fp_rate"] for c in sub)
            mi = statistics.fmean(c["arms"][arm]["miss_rate"] for c in sub)
            mx = max(c["arms"][arm]["miss_rate"] for c in sub)
            row.append(f"{pct(fp)} / {pct(mi)}")
            out["grid"][fam][sev][arm] = {"fp": fp, "miss": mi, "max_miss": mx,
                                          "seeds": len(sub)}
        md.append(f"| {fam} | {sev} | " + " | ".join(row) + " |")

# --- gate statistics over the whole grid --------------------------------------
md.append("\n### Gate statistics over all cells\n")
for arm in ["dual", "local_only", "global_only", "stale_gate", "no_gate"]:
    xs = [c["arms"][arm] for c in cells]
    rej = {}
    for x in xs:
        for k, v in x["rejected"].items():
            rej[k] = rej.get(k, 0) + v
    g = {"cells": len(xs), "proposed": sum(x["proposed"] for x in xs),
         "admitted": sum(x["admitted"] for x in xs), "rejected": rej,
         "false_admissions_on_H_val": sum(x["false_admissions_on_H_val"] for x in xs),
         "escalations": sum(x["escalations"] for x in xs),
         "cells_miss_over_10pct": sum(x["miss_rate"] > 0.10 for x in xs),
         "logs_verified": all(x["log_ok"] for x in xs),
         "max_admitted_per_cell": max(x["admitted"] for x in xs)}
    out["gate"][arm] = g
    md.append(f"- **{arm}**: {json.dumps(g)}")

# --- worked rejection: struct / mid / seed 0, first regression rejection ----------
c0 = next(c for c in cells if c["family"] == "struct" and c["severity"] == "mid" and c["seed"] == 0)
log = c0["arms"]["dual"]["log"]
rej = next(r for r in log if r["decision"] == "regression_on_C")
adm = next(r for r in log if r["decision"] == "admitted")
out["rejection_example"] = {"rejected": rej, "admitted_after": adm,
                            "n_records": len(log)}
md.append("\n### Worked rejection (struct / mid / seed 0, dual loop)\n")
md.append("```\n" + json.dumps(rej, indent=1) + "\n```")
md.append("Admitted later:\n```\n" + json.dumps(adm, indent=1) + "\n```")

with open(os.path.join(D, "tables.md"), "w") as fh:
    fh.write("\n".join(md) + "\n")
with open(os.path.join(D, "tables.json"), "w") as fh:
    json.dump(out, fh, indent=1, sort_keys=True)
print("\n".join(md[:60]))
