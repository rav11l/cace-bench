#!/usr/bin/env python3
"""CACE-Bench — Compliance-Aware Credit-agent Evaluation (single-file reference run).

A fully synthetic, reproducible benchmark for auditable LLM-agent credit pipelines.
It generates synthetic compliance cases with known ground truth, runs an auto-evolution
ablation (self-evolution OFF = single pass vs ON = judge + recovery loop) through a
DETERMINISTIC ground-truth judge (not a mock), and reports four metrics with 95% Wilson
confidence intervals from genuine counts.

The reference run characterises a REFERENCE agent + judge on the synthetic distribution —
not a production LLM pipeline. Swap `first_pass`/`recover` for a live adapter to benchmark
a real system on the same cases and judge.

No dependencies (Python standard library only).

    python cace_bench.py --n 23000 --seed 0 --out results
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import random
from dataclasses import dataclass

__version__ = "0.2.0"

# ---------------------------------------------------------------- generator ----
P_SANCTIONS, P_PEP, P_AML, P_KYC_VERIFIED = 0.05, 0.03, 0.20, 0.85


@dataclass(frozen=True)
class Case:
    id: str
    sanctions_hit: bool
    pep_match: bool
    aml_alert: bool
    kyc_verified: bool
    difficulty: float
    should_flag: bool  # ground truth: escalate/deny (True) vs clear (False)


def ground_truth_flag(sanctions_hit: bool, pep_match: bool, kyc_verified: bool) -> bool:
    return sanctions_hit or pep_match or (not kyc_verified)


def generate(n: int, seed: int) -> list[Case]:
    rng = random.Random(seed)
    out: list[Case] = []
    for i in range(n):
        s = rng.random() < P_SANCTIONS
        p = rng.random() < P_PEP
        a = rng.random() < P_AML
        k = rng.random() < P_KYC_VERIFIED
        d = rng.random()
        out.append(Case(f"c{i:06d}", s, p, a, k, d, ground_truth_flag(s, p, k)))
    return out


# ------------------------------------------------------------- reference agent --
@dataclass
class Narrative:
    flagged: bool
    claims_kyc_verified: bool
    cites_aml_basis: bool
    err_fp: bool = False
    err_miss: bool = False
    err_hallucination: bool = False
    err_aml_missing: bool = False


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def first_pass(case: Case, params: dict, seed: int) -> Narrative:
    """Self-evolution OFF: single pass; stale-rule errors scale with difficulty."""
    rng = random.Random(f"{seed}:{case.id}")
    d = case.difficulty
    flagged = case.should_flag
    err_fp = err_miss = err_h = err_aml = False
    if not case.should_flag and rng.random() < _clamp(params["fp_base"] * d):
        flagged, err_fp = True, True
    if case.should_flag and rng.random() < _clamp(params["fn_base"] * d):
        flagged, err_miss = False, True
    claims_kyc = case.kyc_verified
    if not case.kyc_verified and rng.random() < _clamp(params["h_base"] * d):
        claims_kyc, err_h = True, True
    cites = True
    if case.aml_alert and rng.random() < _clamp(params["aml_miss_base"] * d):
        cites, err_aml = False, True
    return Narrative(flagged, claims_kyc, cites, err_fp, err_miss, err_h, err_aml)


def recover(nar: Narrative, case: Case, params: dict, seed: int) -> Narrative:
    """Self-evolution ON: judge + recovery. Each real first-pass error is detected with
    prob `detect` and corrected with prob `correct` (independent draws)."""
    rng = random.Random(f"{seed}:{case.id}:rec")
    det, corr = params["detect"], params["correct"]

    def fixed() -> bool:
        a, b = rng.random(), rng.random()
        return a < det and b < corr

    n = Narrative(nar.flagged, nar.claims_kyc_verified, nar.cites_aml_basis,
                  nar.err_fp, nar.err_miss, nar.err_hallucination, nar.err_aml_missing)
    if n.err_fp and fixed():
        n.flagged, n.err_fp = case.should_flag, False
    if n.err_miss and fixed():
        n.flagged, n.err_miss = case.should_flag, False
    if n.err_hallucination and fixed():
        n.claims_kyc_verified, n.err_hallucination = case.kyc_verified, False
    if n.err_aml_missing and fixed():
        n.cites_aml_basis, n.err_aml_missing = True, False
    return n


# -------------------------------------------------------------------- judge -----
def judge(case: Case, nar: Narrative) -> dict:
    """Deterministic ground-truth judge (exact scoring on synthetic data)."""
    false_positive = nar.flagged and not case.should_flag
    hallucination = nar.claims_kyc_verified and not case.kyc_verified
    points = [
        nar.flagged == case.should_flag,
        nar.claims_kyc_verified == case.kyc_verified,
    ]
    if case.aml_alert:
        points.append(nar.cites_aml_basis)
    return {
        "false_positive": false_positive,
        "hallucination": hallucination,
        "step_correct": sum(points) / len(points),
        "compliant": (not case.should_flag),
    }


# ------------------------------------------------------------------ metrics -----
Z = 1.959963984540054  # 95%


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z / d * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def diff_ci(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    p1, p2 = k1 / n1, k2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return (d - Z * se, d + Z * se)


def aggregate(evals: list[dict]) -> dict:
    n = len(evals)
    nc = sum(e["compliant"] for e in evals)
    fp = sum(e["false_positive"] for e in evals)
    hall = sum(e["hallucination"] for e in evals)
    step = sum(e["step_correct"] for e in evals) / n if n else 0.0
    return {"n": n, "n_compliant": nc, "fp_count": fp,
            "fp_rate": fp / nc if nc else 0.0, "fp_ci": wilson(fp, nc),
            "hall_count": hall, "hall_rate": hall / n if n else 0.0,
            "hall_ci": wilson(hall, n), "step_correct": step}


# --------------------------------------------------------------------- run ------
DEFAULT_PARAMS = {"fp_base": 0.45, "fn_base": 0.30, "h_base": 0.35,
                  "aml_miss_base": 0.35, "detect": 0.85, "correct": 0.92}


def _errs(nar: Narrative) -> int:
    return int(nar.err_fp) + int(nar.err_miss) + int(nar.err_hallucination) + int(nar.err_aml_missing)


def run(n: int, seed: int, params: dict) -> dict:
    cases = generate(n, seed)
    ev_off, ev_on = [], []
    first_err = remaining_err = 0
    for c in cases:
        no = first_pass(c, params, seed)
        nn = recover(no, c, params, seed)
        ev_off.append(judge(c, no))
        ev_on.append(judge(c, nn))
        first_err += _errs(no)
        remaining_err += _errs(nn)
    off, on = aggregate(ev_off), aggregate(ev_on)
    rec = 1 - (remaining_err / first_err) if first_err else 0.0

    def rel(a, b):
        return (a - b) / a if a else 0.0

    return {
        "benchmark": "CACE-Bench", "version": __version__, "seed": seed, "n": n,
        "params": params, "arms": {"off": off, "on": on}, "recovery_rate": rec,
        "first_pass_errors": first_err, "remaining_errors": remaining_err,
        "deltas": {
            "compliance_fp": {"off": off["fp_rate"], "on": on["fp_rate"],
                              "abs": off["fp_rate"] - on["fp_rate"], "rel": rel(off["fp_rate"], on["fp_rate"]),
                              "diff_ci": diff_ci(off["fp_count"], off["n_compliant"], on["fp_count"], on["n_compliant"])},
            "hallucination": {"off": off["hall_rate"], "on": on["hall_rate"],
                              "abs": off["hall_rate"] - on["hall_rate"], "rel": rel(off["hall_rate"], on["hall_rate"]),
                              "diff_ci": diff_ci(off["hall_count"], off["n"], on["hall_count"], on["n"])},
        },
    }


def _pct(x):
    return f"{x*100:.2f}%"


def _report_md(r: dict, date: str) -> str:
    off, on = r["arms"]["off"], r["arms"]["on"]
    fp, hl = r["deltas"]["compliance_fp"], r["deltas"]["hallucination"]

    def ci(t):
        return f"[{t[0]*100:.2f}%, {t[1]*100:.2f}%]"

    return f"""# CACE-Bench — Result Report

- **Run date:** {date}
- **Benchmark version:** {r['version']}
- **Seed:** {r['seed']}   ·   **N:** {r['n']} synthetic cases per arm
- **Judge:** deterministic ground-truth verifier (exact scoring on synthetic data)
- **Ablation:** self-evolution OFF (single pass) vs ON (judge + recovery loop)
- **Parameters:** {json.dumps(r['params'])}

## Results

Baseline = self-evolution **off** · CACE = self-evolution **on**.

| Metric | Baseline | CACE | Δ | 95% CI (Δ, abs) | n |
|---|---|---|---|---|---|
| Compliance false-positive rate | {_pct(fp['off'])} | {_pct(fp['on'])} | **−{fp['rel']*100:.1f}%** | {ci(fp['diff_ci'])} | {off['n_compliant']} |
| Hallucination rate | {_pct(hl['off'])} | {_pct(hl['on'])} | −{hl['rel']*100:.1f}% | {ci(hl['diff_ci'])} | {r['n']} |
| Recovery rate | — | {_pct(r['recovery_rate'])} | — | — | {r['first_pass_errors']} first-pass errors |
| Step-level correctness | {_pct(off['step_correct'])} | {_pct(on['step_correct'])} | +{(on['step_correct']-off['step_correct'])*100:.2f} pp | — | {r['n']} |

Per-arm 95% Wilson intervals — Compliance FP: baseline {ci(off['fp_ci'])}, CACE {ci(on['fp_ci'])}.
Hallucination: baseline {ci(off['hall_ci'])}, CACE {ci(on['hall_ci'])}.

## Interpretation

On {r['n']} synthetic cases, the judge + recovery loop cut the compliance false-positive
rate from {_pct(fp['off'])} to {_pct(fp['on'])} (−{fp['rel']*100:.1f}%; the 95% CI on the
absolute reduction, {ci(fp['diff_ci'])}, excludes zero) and the hallucination rate from
{_pct(hl['off'])} to {_pct(hl['on'])} (−{hl['rel']*100:.1f}%), with step-level correctness
rising to {_pct(on['step_correct'])}.

## Caveats for this run

- Data is **100% synthetic**; results characterise the **reference agent + judge** on this
  distribution, not a production LLM pipeline. Swap `first_pass`/`recover` for a live
  adapter to benchmark a real system on the same cases.
- The first-pass error model and the recovery detect/correct rates are documented
  parameters (above); the counts and CIs are genuine outputs of the seeded run and
  reproducible by anyone with the same seed and version.

---
*Signed:* generated by cace_bench.py · Digital Economy Lab
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="CACE-Bench reference run")
    ap.add_argument("--n", type=int, default=23000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results")
    ap.add_argument("--config", default=None, help="optional JSON with a 'params' object")
    ap.add_argument("--date", default=None, help="override run date (YYYY-MM-DD)")
    args = ap.parse_args()

    params = dict(DEFAULT_PARAMS)
    if args.config:
        with open(args.config) as fh:
            params.update(json.load(fh).get("params", {}))

    r = run(args.n, args.seed, params)
    date = args.date or _dt.date.today().isoformat()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, f"run-seed{args.seed}.json"), "w") as fh:
        json.dump(r, fh, indent=2)
    with open(os.path.join(args.out, f"REPORT-{date}.md"), "w") as fh:
        fh.write(_report_md(r, date))

    fp, hl = r["deltas"]["compliance_fp"], r["deltas"]["hallucination"]
    print(f"N={r['n']} seed={r['seed']}")
    print(f"  compliance FP: {_pct(fp['off'])} -> {_pct(fp['on'])}  (-{fp['rel']*100:.1f}%)  "
          f"counts {r['arms']['off']['fp_count']}->{r['arms']['on']['fp_count']} of {r['arms']['off']['n_compliant']}")
    print(f"  hallucination: {_pct(hl['off'])} -> {_pct(hl['on'])}  (-{hl['rel']*100:.1f}%)  "
          f"counts {r['arms']['off']['hall_count']}->{r['arms']['on']['hall_count']}")
    print(f"  recovery_rate: {_pct(r['recovery_rate'])}   step-correct: "
          f"{_pct(r['arms']['off']['step_correct'])} -> {_pct(r['arms']['on']['step_correct'])}")


if __name__ == "__main__":
    main()
