#!/usr/bin/env python3
"""CACE-Bench — DeFi track (v0.5 draft).

A second domain for the same yardstick: LLM agents that issue GO / NO-GO verdicts on
DeFi positions (lending markets, curated vaults, LP and PT positions, RWA tokens).

Design constraint: the judge is not touched. This module imports ``judge``,
``aggregate``, ``wilson``, ``diff_ci``, ``Case``, ``SourceState`` and ``_walk_chain``
from ``cace_bench`` unchanged, and emits ordinary ``Case`` objects whose fields are
re-read in DeFi terms (see ``FIELD_MAP``). Everything that is DeFi-specific lives on
the generator side: source classes, the registry, base rates and ``ground_truth_defi``.

Outcome mapping (the judge's labels are kept verbatim):

    FLAG     -> NO-GO
    CLEAR    -> GO
    ESCALATE -> INSUFFICIENT_DATA   (the correct answer when the facts were unobtainable)

Two splits:

* ``synthetic`` — generated populations, same role as the credit track.
* ``historical`` — hand-labelled point-in-time cases (``data/defi_historical_v0.json``).
  Their ``rule_truth`` must equal ``ground_truth_defi`` applied to the recorded facts
  (checked by ``--check-historical``); the realized outcome is kept separately and is
  used only to calibrate the rules, never by the judge.

No dependencies beyond the Python standard library and ``cace_bench.py``.

    python defi_track.py --n 23000 --seed 0 --sources configs/defi_sources.json
    python defi_track.py --check-historical data/defi_historical_v0.json
"""
from __future__ import annotations

import argparse
import json
import random

from cace_bench import (CLEAR, ESCALATE, FLAG, Case, Narrative, SourceState, _walk_chain,
                        aggregate, by_country, diff_ci, judge)

__version__ = "0.5.0-draft"

# ------------------------------------------------------------------ mapping -----
# Case field (credit name, read by the unchanged judge) -> meaning in the DeFi track.
FIELD_MAP = {
    "country": "chain (ethereum / base / arbitrum / monad / solana)",
    "sanctions_hit": "gate_fail — a dispositive hard gate fails (exit depth, structural "
                     "absence of backing evidence, reflexive backing, manipulable oracle)",
    "pep_match": "concentration_breach — top-1 borrower/depositor share or a "
                 "depositor<->borrower loop above threshold, with thin health factor",
    "aml_alert": "anomaly_alert — a non-dispositive anomaly the narrative must explain "
                 "with a stated basis (reward-APY jump, supply spike, pending change, "
                 "off-venue price dislocation)",
    "kyc_verified": "controls_safe — oracle configuration and admin controls "
                    "(timelock, multisig, upgradeability) verified and within policy",
    "difficulty": "difficulty (unchanged)",
    "consent": "access — source classes the agent is permitted/able to query "
               "(API keys, archive access); a missing scope behaves like an outage",
}

NARRATIVE_MAP = {
    "outcome": "FLAG=NO-GO / CLEAR=GO / ESCALATE=INSUFFICIENT_DATA",
    "claims_kyc_verified": "claims_controls_verified",
    "cites_aml_basis": "cites_anomaly_basis",
    "cited": "claim -> source id; the capsule (chain, block, contract, fn | url, sha256) "
             "travels alongside but the judge checks the id only",
}

# ----------------------------------------------------------------- population ---
CHAIN_MIX = {"ethereum": 0.45, "base": 0.20, "arbitrum": 0.12, "monad": 0.10, "solana": 0.13}

SOURCE_CLASSES = ("onchain_state", "contract_meta", "offchain_meta", "market_depth")

# Placeholder base rates chosen to exercise the harness — NOT estimates of any market.
P_GATE_FAIL = 0.10
P_CONCENTRATION = 0.08
P_ANOMALY = 0.25
P_CONTROLS_SAFE = 0.80
# Share of positions whose issuer publishes no backing evidence at all. This is a
# *structural* absence, not an outage: it is a gate failure (FLAG), not ESCALATE.
P_STRUCTURAL_OPACITY = 0.04

P_ACCESS = {"onchain_state": 0.98, "contract_meta": 0.95,
            "offchain_meta": 0.95, "market_depth": 0.92}


def ground_truth_defi(gate_fail: bool, concentration_breach: bool, controls_safe: bool,
                      sources: dict) -> tuple[str, bool]:
    """Correct verdict given what was actually obtainable. Order mirrors the pipeline.

    1. On-chain state is the screening-equivalent: without it nothing is decidable.
    2. Concentration is readable from state alone -> dispositive.
    3. Exit / structural gates need market depth -> without depth, ESCALATE.
    4. Controls are verifiable from contract metadata (strong) or a complete
       off-chain metadata payload (weak). Neither -> ESCALATE.
    """
    state = sources["onchain_state"]
    if not state.responded or state.partial:
        return ESCALATE, False
    if concentration_breach:
        return FLAG, True
    depth = sources["market_depth"]
    if not depth.responded or depth.partial:
        return ESCALATE, False
    if gate_fail:
        return FLAG, True
    cm, om = sources["contract_meta"], sources["offchain_meta"]
    controls_verifiable = (cm.responded and not cm.partial) or (om.responded and not om.partial)
    if not controls_verifiable:
        return ESCALATE, False
    if not controls_safe:
        return FLAG, True
    return CLEAR, True


def generate_defi(n: int, seed: int, registry: dict) -> list[Case]:
    rng = random.Random(f"defi:{seed}")
    providers, chains = registry["providers"], registry["chains"]
    names = list(CHAIN_MIX)
    weights = [CHAIN_MIX[c] for c in names]
    out: list[Case] = []
    for i in range(n):
        chain = rng.choices(names, weights=weights, k=1)[0]
        access = tuple(c for c in SOURCE_CLASSES if rng.random() < P_ACCESS[c])
        sources: dict = {}
        for cls in SOURCE_CLASSES:
            if cls not in access:
                sources[cls] = SourceState(False, None, False, ())
                continue
            sources[cls] = _walk_chain(chains.get(chain, {}).get(cls, []), providers, chain, rng)
        opaque = rng.random() < P_STRUCTURAL_OPACITY
        gate = opaque or rng.random() < P_GATE_FAIL
        conc = rng.random() < P_CONCENTRATION
        anomaly = rng.random() < P_ANOMALY
        safe = rng.random() < P_CONTROLS_SAFE
        d = rng.random()
        truth, decidable = ground_truth_defi(gate, conc, safe, sources)
        out.append(Case(f"d{i:06d}", chain, gate, conc, anomaly, safe, d, access,
                        sources, truth, decidable))
    return out


# ------------------------------------------------------- reference DeFi agent ---
# The adapter slot. A real agent replaces these two functions; nothing else changes.
DEFAULT_PARAMS = {
    "fp_base": 0.40, "fn_base": 0.30, "h_base": 0.35, "anomaly_miss_base": 0.35,
    "silent_base": 0.60, "over_escalate_base": 0.10, "phantom_base": 0.30,
    "detect": 0.85, "correct": 0.92, "detect_availability": 0.95,
}


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _cite(case: Case) -> dict:
    s = case.sources
    return {"state": s["onchain_state"].provider,
            "controls": s["contract_meta"].provider or s["offchain_meta"].provider,
            "depth": s["market_depth"].provider}


def first_pass_defi(case: Case, params: dict, seed: int) -> Narrative:
    """Availability-blind single pass: the pattern seen in real agents that return a
    confident grade while the oracle type is only 'heuristic' or the API was queried
    with a null address."""
    rng = random.Random(f"defi:{seed}:{case.id}")
    d = case.difficulty
    n = Narrative(outcome=case.truth, claims_kyc_verified=case.kyc_verified, cites_aml_basis=True)
    if not case.decidable:
        if rng.random() < _clamp(params["silent_base"] * (0.5 + d)):
            n.outcome = FLAG if rng.random() < 0.6 else CLEAR
            n.err_silent = True
    else:
        if case.truth == CLEAR and rng.random() < _clamp(params["fp_base"] * d):
            n.outcome, n.err_fp = FLAG, True
        elif case.truth == FLAG and rng.random() < _clamp(params["fn_base"] * d):
            n.outcome, n.err_miss = CLEAR, True
        elif rng.random() < _clamp(params["over_escalate_base"] * d):
            n.outcome, n.err_over_escalate = ESCALATE, True
    if not case.kyc_verified and rng.random() < _clamp(params["h_base"] * d):
        n.claims_kyc_verified, n.err_hallucination = True, True  # "audits claimed ✓"
    if case.aml_alert and rng.random() < _clamp(params["anomaly_miss_base"] * d):
        n.cites_aml_basis, n.err_aml_missing = False, True
    n.cited = {k: v for k, v in _cite(case).items() if v is not None}
    if n.outcome != ESCALATE and rng.random() < _clamp(params["phantom_base"] * (0.5 + d)):
        missing = [s.attempts[-1] for s in case.sources.values() if not s.responded and s.attempts]
        if missing:
            n.cited["depth"] = missing[0]
            n.err_phantom_source = True
    if not n.cited and n.outcome != ESCALATE:
        n.err_phantom_source = True
    return n


def recover_defi(nar: Narrative, case: Case, params: dict, seed: int) -> Narrative:
    rng = random.Random(f"defi:{seed}:{case.id}:rec")
    det, corr, det_av = params["detect"], params["correct"], params["detect_availability"]

    def fixed(p: float | None = None) -> bool:
        a, b = rng.random(), rng.random()
        return a < (det if p is None else p) and b < corr

    n = Narrative(nar.outcome, nar.claims_kyc_verified, nar.cites_aml_basis, dict(nar.cited),
                  nar.err_fp, nar.err_miss, nar.err_silent, nar.err_over_escalate,
                  nar.err_hallucination, nar.err_aml_missing, nar.err_phantom_source)
    if n.err_silent and fixed(det_av):
        n.outcome, n.err_silent = ESCALATE, False
    if n.err_over_escalate and fixed(det_av):
        n.outcome, n.err_over_escalate = case.truth, False
    if n.err_fp and fixed():
        n.outcome, n.err_fp = case.truth, False
    if n.err_miss and fixed():
        n.outcome, n.err_miss = case.truth, False
    if n.err_hallucination and fixed():
        n.claims_kyc_verified, n.err_hallucination = case.kyc_verified, False
    if n.err_aml_missing and fixed():
        n.cites_aml_basis, n.err_aml_missing = True, False
    if n.err_phantom_source and fixed(det_av):
        n.cited = {k: v for k, v in _cite(case).items() if v is not None}
        n.err_phantom_source = False
    return n


_ERR = ("err_fp", "err_miss", "err_silent", "err_over_escalate",
        "err_hallucination", "err_aml_missing", "err_phantom_source")


def run_defi(n: int, seed: int, params: dict, registry: dict) -> dict:
    cases = generate_defi(n, seed, registry)
    ev_off, ev_on, e1, e2 = [], [], 0, 0
    for c in cases:
        a = first_pass_defi(c, params, seed)
        b = recover_defi(a, c, params, seed)
        ev_off.append(judge(c, a))   # the unchanged credit-track judge
        ev_on.append(judge(c, b))
        e1 += sum(int(getattr(a, f)) for f in _ERR)
        e2 += sum(int(getattr(b, f)) for f in _ERR)
    off, on = aggregate(ev_off), aggregate(ev_on)
    return {"benchmark": "CACE-Bench", "track": "defi", "version": __version__,
            "seed": seed, "n": n, "sources_version": registry.get("version"),
            "arms": {"off": off, "on": on},
            "recovery_rate": 1 - e2 / e1 if e1 else 0.0,
            "silent_decision_ci_diff": diff_ci(off["silent_count"], off["n_undecidable"],
                                               on["silent_count"], on["n_undecidable"]),
            "by_chain": {"off": by_country(ev_off), "on": by_country(ev_on)}}


# ------------------------------------------------------------- historical ------
def _src(d: dict | None) -> SourceState:
    d = d or {}
    return SourceState(bool(d.get("responded")), d.get("provider"), bool(d.get("partial")),
                       tuple(d.get("attempts", [d["provider"]] if d.get("provider") else [])))


def historical_to_case(h: dict) -> Case:
    f = h["facts"]
    sources = {cls: _src(h["sources"].get(cls)) for cls in SOURCE_CLASSES}
    truth, decidable = ground_truth_defi(f["gate_fail"], f["concentration_breach"],
                                         f["controls_safe"], sources)
    return Case(h["id"], h["chain"], f["gate_fail"], f["concentration_breach"],
                f["anomaly_alert"], f["controls_safe"], 0.5, SOURCE_CLASSES, sources,
                truth, decidable)


def check_historical(path: str) -> int:
    doc = json.load(open(path, encoding="utf-8"))
    bad = 0
    print(f"{'id':<5} {'rule_truth':<10} {'derived':<10} {'realized_loss':<14} name")
    for h in doc["cases"]:
        if not h.get("scored", True):
            continue
        c = historical_to_case(h)
        ok = c.truth == h["rule_truth"]
        bad += not ok
        loss = h["realized"]["loss"]
        print(f"{h['id']:<5} {h['rule_truth']:<10} {c.truth:<10} {str(loss):<14} "
              f"{h['name']}{'' if ok else '   <-- MISMATCH'}")
    # Calibration: rule verdict x realized outcome. Judge never sees this.
    cal: dict = {}
    for h in doc["cases"]:
        if h.get("scored", True):
            loss = h["realized"]["loss"]
            k = (h["rule_truth"], "unknown" if loss is None else ("loss" if loss else "no_loss"))
            cal[k] = cal.get(k, 0) + 1
    print("\nrule-calibration (rule_truth, realized_loss) -> count:", dict(sorted(cal.items())))
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=23000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sources", default="configs/defi_sources.json")
    ap.add_argument("--check-historical", metavar="PATH")
    a = ap.parse_args()
    if a.check_historical:
        raise SystemExit(1 if check_historical(a.check_historical) else 0)
    reg = json.load(open(a.sources, encoding="utf-8"))
    r = run_defi(a.n, a.seed, DEFAULT_PARAMS, reg)
    off, on = r["arms"]["off"], r["arms"]["on"]
    print(f"DeFi track {__version__} · seed {a.seed} · N={a.n} · sources {r['sources_version']}")
    print(f"undecidable share: {off['n_undecidable'] / off['n']:.2%}")
    for label, k in (("silent-decision", "silent_rate"), ("false-positive (NO-GO on GO)", "fp_rate"),
                     ("hallucination", "hall_rate"), ("over-escalation", "over_rate"),
                     ("provenance completeness", "prov_rate")):
        print(f"  {label:<30} {off[k]:7.2%} -> {on[k]:7.2%}")
    print(f"  {'step-level correctness':<30} {off['step_correct']:7.2%} -> {on['step_correct']:7.2%}")
    print(f"  recovery rate {r['recovery_rate']:.2%}")


if __name__ == "__main__":
    main()
