"""Offline gate comparison on frozen proposals, not a new adaptive LLM run."""
import gzip
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
import evolve as E

def rate(before, after, pool, labels):
    reg, count = E.regression(before, after, pool, labels)
    return reg / count if count else 0.0

rows = []
for model, directory in [("Sol", ROOT / "results/combined"),
                         ("Haiku", SOURCE / "results/shift-llm")]:
    for path in sorted(directory.glob("cell-*-mid-seed*.json.gz")):
        with gzip.open(path, "rt") as f:
            cell = json.load(f)
        family, severity, seed = cell["family"], cell["severity"], cell["seed"]
        cases = E.generate(seed, family, severity, cell["n"])
        pre = cases[:cell["T"]]
        sel = [c for c in pre if c.idx % 2 == 0]
        val = [c for c in pre if c.idx % 2 == 1]
        ev = cases[cell["eval_start"]:]
        labels = lambda pool: [E.truth(c, family, severity, "v2") for c in pool]
        sl, vl, el = labels(sel), labels(val), labels(ev)
        original = cell["arms"]["dual"]
        row = {"model": model, "family": family, "seed": seed, "variants": {}}
        for variant in ["original", "fixed_baseline_added"]:
            current = E.H0
            admitted = blocked = harmful = 0
            max_cumulative = 0.0
            decisions = []
            for rec in original["log"]:
                candidate = E._harness_from_text(rec)
                assert candidate.digest() == rec["h_prime"]
                decision, _ = E.gate_decision(current, candidate, rec["cause"][1], sel, sl)
                cumulative = rate(E.H0, candidate, sel, sl)
                if variant == "original":
                    assert current.digest() == rec["h"]
                    assert decision == rec["decision"]
                elif decision == "admitted" and cumulative > E.EPS:
                    decision = "fixed_baseline_regression"
                    blocked += 1
                if decision == "admitted":
                    harmful += E._err(candidate, val, vl) > E._err(current, val, vl)
                    current = candidate
                    admitted += 1
                    max_cumulative = max(max_cumulative, cumulative)
                decisions.append(decision)
            if variant == "original":
                assert current.digest() == original["harness_digest"]
                assert admitted == original["admitted"]
                assert harmful == original["false_admissions_on_H_val"]
            else:
                assert max_cumulative <= E.EPS
            row["variants"][variant] = {
                "admitted": admitted, "blocked_by_fixed_baseline": blocked,
                "harmful_on_validation": harmful,
                "oracle_reached": current.digest() == E.oracle_harness(family, severity).digest(),
                "max_selection_cumulative_regression": max_cumulative,
                "final_selection_cumulative_regression": rate(E.H0, current, sel, sl),
                "final_validation_cumulative_regression": rate(E.H0, current, val, vl),
                "final_evaluation": E.evaluate(current, ev, el, E.H0),
                "final_harness": json.loads(current.key()), "decisions": decisions,
            }
        rows.append(row)

summary = {}
for model in ["Sol", "Haiku"]:
    subset = [r for r in rows if r["model"] == model]
    summary[model] = {}
    for variant in ["original", "fixed_baseline_added"]:
        vs = [r["variants"][variant] for r in subset]
        summary[model][variant] = {
            "cells": len(vs),
            "oracle_reached": sum(v["oracle_reached"] for v in vs),
            "admitted": sum(v["admitted"] for v in vs),
            "blocked_by_fixed_baseline": sum(v["blocked_by_fixed_baseline"] for v in vs),
            "harmful_on_validation": sum(v["harmful_on_validation"] for v in vs),
            "cells_over_selection_limit": sum(v["max_selection_cumulative_regression"] > E.EPS for v in vs),
            "cells_over_validation_limit": sum(v["final_validation_cumulative_regression"] > E.EPS for v in vs),
        }
report = {
    "protocol": "Original per-step gate plus cumulative H0 regression <= 0.005 on H_sel; identical frozen proposal order, unchanged thresholds and data. H_val and final evaluation never drive decisions.",
    "limitations": "After a changed decision, later saved proposals were generated for another state. This is an offline frozen-proposal diagnostic, not a fresh adaptive model run or a guarantee on unseen data. Historical model runs are unpinned.",
    "summary": summary, "cells": rows,
}
output = ROOT / "results/fixed-baseline-comparison.json"
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
for row in rows:
    if row["family"] == "scope" and row["seed"] == 4:
        print(json.dumps({"model": row["model"], "scenario": "scope/4", "variants": {
            k: {key: value for key, value in v.items() if key != "decisions"}
            for k, v in row["variants"].items()}}, indent=2))
