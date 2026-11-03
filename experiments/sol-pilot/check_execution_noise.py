"""Simulator-only noise ablation on frozen proposals; never edits the source gate."""
import dataclasses
import gzip
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
import evolve as E

def regression(before, after, pool, labels):
    count, size = E.regression(before, after, pool, labels)
    return {"regressed": count, "correct_baseline": size,
            "rate": count / size if size else 0.0}

previous = json.loads((ROOT / "results/fixed-baseline-comparison.json").read_text())
rows = []
for model, directory in [("Sol", ROOT / "results/combined"),
                         ("Haiku", SOURCE / "results/shift-llm")]:
    for path in sorted(directory.glob("cell-*-mid-seed*.json.gz")):
        with gzip.open(path, "rt") as f:
            cell = json.load(f)
        family, severity, seed = cell["family"], cell["severity"], cell["seed"]
        cases = E.generate(seed, family, severity, cell["n"])
        pools = {
            "selection": [c for c in cases[:cell["T"]] if c.idx % 2 == 0],
            "validation": [c for c in cases[:cell["T"]] if c.idx % 2 == 1],
            "evaluation": cases[cell["eval_start"]:],
        }
        clean = {key: [dataclasses.replace(c, u_slip=1.0) for c in pool]
                 for key, pool in pools.items()}
        labels = {key: [E.truth(c, family, severity, "v2") for c in pool]
                  for key, pool in pools.items()}
        oracle = E.oracle_harness(family, severity)
        noisy_regressions = [c for c, y in zip(pools["selection"], labels["selection"])
                             if E.decide(E.H0, c) == y and E.decide(oracle, c) != y]
        current = E.H0
        gate_cache, cumulative_cache = {}, {}
        admitted = harmful = blocked = 0
        decisions = []
        for rec in cell["arms"]["dual"]["log"]:
            candidate = E._harness_from_text(rec)
            assert candidate.digest() == rec["h_prime"]
            key = (current.digest(), candidate.digest(), rec["cause"][1])
            if key not in gate_cache:
                gate_cache[key] = E.gate_decision(current, candidate, rec["cause"][1],
                                                  clean["selection"], labels["selection"])[0]
            decision = gate_cache[key]
            digest = candidate.digest()
            if digest not in cumulative_cache:
                cumulative_cache[digest] = regression(E.H0, candidate, clean["selection"],
                                                       labels["selection"])["rate"]
            if decision == "admitted" and cumulative_cache[digest] > E.EPS:
                decision = "fixed_baseline_regression"
                blocked += 1
            if decision == "admitted":
                harmful += E._err(candidate, pools["validation"], labels["validation"]) > E._err(current, pools["validation"], labels["validation"])
                current = candidate
                admitted += 1
            decisions.append(decision)
        metrics = {}
        for key in pools:
            metrics[key] = {
                "observed_regression": regression(E.H0, current, pools[key], labels[key]),
                "rule_only_regression": regression(E.H0, current, clean[key], labels[key]),
                "observed_errors": E._err(current, pools[key], labels[key]),
                "rule_only_errors": E._err(current, clean[key], labels[key]),
            }
        assert metrics["selection"]["rule_only_regression"]["rate"] <= E.EPS
        rows.append({
            "model": model, "family": family, "seed": seed,
            "oracle_observed_selection_regressions": len(noisy_regressions),
            "oracle_regressions_on_slip_cases": sum(c.u_slip < E.SLIP for c in noisy_regressions),
            "oracle_rule_only_selection_regression": regression(E.H0, oracle, clean["selection"], labels["selection"]),
            "oracle_reached": current.digest() == oracle.digest(),
            "admitted": admitted, "blocked_cumulative": blocked,
            "harmful_admissions_on_noisy_validation": harmful,
            "metrics": metrics, "decisions": decisions,
            "final_harness": json.loads(current.key()),
        })
        print(f"Completed {model} {family}/{seed}", flush=True)

summary = {}
for model in ["Sol", "Haiku"]:
    subset = [r for r in rows if r["model"] == model]
    summary[model] = {
        "cells": len(subset), "oracle_reached": sum(r["oracle_reached"] for r in subset),
        "admitted": sum(r["admitted"] for r in subset),
        "harmful_admissions_on_noisy_validation": sum(r["harmful_admissions_on_noisy_validation"] for r in subset),
        "rule_only_validation_limit_exceeded": sum(r["metrics"]["validation"]["rule_only_regression"]["rate"] > E.EPS for r in subset),
        "observed_validation_limit_exceeded": sum(r["metrics"]["validation"]["observed_regression"]["rate"] > E.EPS for r in subset),
        "rule_only_evaluation_errors": sum(r["metrics"]["evaluation"]["rule_only_errors"] for r in subset),
    }
report = {
    "protocol": "Noise ablation: set u_slip=1 only in copied selection cases for per-step gate and cumulative H0 gate; EPS unchanged. Report both original noisy and clean held-out metrics. Frozen proposal order.",
    "limitations": "Simulator-only diagnostic using known latent slip draws, not an estimated noise correction or a deployable gate. Observed regressions are not eliminated. After divergent admissions proposals are off-policy. No new LLM calls; no source or production changes.",
    "previous_summary": previous["summary"], "summary": summary, "cells": rows,
}
out = ROOT / "results/execution-noise-comparison.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
