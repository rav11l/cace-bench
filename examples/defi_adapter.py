#!/usr/bin/env python3
"""Benchmark YOUR DeFi risk agent on the CACE-Bench DeFi track.

Same contract as ``benchmark_your_pipeline.py`` for the credit track: your agent gets
one case, returns one verdict; the population, registry, rules and the unchanged judge
do the rest. Put this file next to ``cace_bench.py`` and ``defi_track.py`` (or run it
from the repo root with ``PYTHONPATH=.``).

Your agent is called as a subprocess (``--cmd``). It reads one JSON request on stdin
and prints one JSON verdict on stdout:

    request  {"mode": "verdict", "case_id": ..., "chain": ..., "access": [...],
              "sources": {class: {"responded", "provider", "partial", "attempts"}},
              "position": "...",            # historical only, anonymised
              "evidence": [capsules...]}    # historical only, state at t0_block
    verdict  {"verdict": "GO" | "NO-GO" | "INSUFFICIENT_DATA",
              "controls_verified": true/false,
              "anomaly_basis": true/false,  # did the narrative explain anomalies
              "citations": {"claim": "<source id from configs/defi_sources.json>"}}

Ground truth (``truth``, ``decidable``, and the ``facts`` block of historical cases) is
never sent. For historical runs the recall probe (§5a of METHODOLOGY-DeFi.md) sends
``{"mode": "probe", ...}`` with the evidence withheld and expects
``{"incident": "<free text or null>"}``.

    # dry run with the built-in honest agent
    python examples/defi_adapter.py --demo --n 3000

    # your agent on the synthetic split
    python examples/defi_adapter.py --cmd "python my_agent.py" --n 3000 --seed 0

    # your agent on the historical split, with cutoff gate and recall probe
    python examples/defi_adapter.py --cmd "python my_agent.py" --historical \
        data/defi_historical_v0.json --model-cutoff 2026-06-30

Digital Economy Lab · CACE-Bench · MIT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from cace_bench import CLEAR, ESCALATE, FLAG, Narrative, aggregate, by_country, judge
from defi_track import SOURCE_CLASSES, generate_defi, historical_to_case

OUTCOME_MAP = {"GO": CLEAR, "NO-GO": FLAG, "NO_GO": FLAG, "INSUFFICIENT_DATA": ESCALATE,
               "ESCALATE": ESCALATE}


# ------------------------------------------------------------- anonymisation ----
# Names that would let a model recognise a historical case. Extend as cases are added.
KNOWN_NAMES = [
    "UST", "Anchor", "Terra", "LUNA", "stETH", "Lido", "Celsius", "3AC", "Mango", "MNGO",
    "USDC", "SVB", "Circle", "CRV", "Curve", "LlamaLend", "Inverse", "Fraxlend", "UwU",
    "Egorov", "Morpho", "PAXG", "Resupply", "ERC-4626", "USDe", "sUSDe", "Ethena", "Aave",
    "Binance", "Stream", "xUSD", "Elixir", "deUSD", "Euler", "Silo", "Balancer", "RLUSD",
    "Sentora", "kBTC", "Kraken", "weETH", "USDT", "DAI", "DOLA",
    # added for H11-H13 and the re-scoped H09/H10
    "Term Finance", "Term", "Moonwell", "MAMO", "mMAMO", "Edel", "GOOGLx", "wGOOGLx",
    "MSTRx", "wMSTRx", "xStocks", "cbBTC", "Zodiac", "Stream Finance", "Elixir USDC",
    "MEV Capital", "Steakhouse", "Gauntlet", "Wormhole", "Ripple", "Coinbase",
]
_HEX64 = re.compile(r"0x[0-9a-fA-F]{64}(?![0-9a-fA-F])")   # tx hashes, market ids
_ADDR = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_DATES = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ][0-9:.]+(?:Z|[+-]\d{2}:?\d{2})?)?"),  # ISO
    re.compile(r"\b\d{1,2}\s+" + _MONTHS + r"\s+\d{4}\b"),                     # 10 Oct 2025
    re.compile(r"\b" + _MONTHS + r"[\s-]+\d{1,2}(?:st|nd|rd|th)?,?[\s-]+\d{4}\b"),  # Aug 27, 2026
    re.compile(r"\b" + _MONTHS + r"\s+\d{4}\b"),                                  # May 2022
    re.compile(r"\b(?:19|20)\d{2}\b"),                                             # bare years
]


def _alias(name: str) -> str:
    return "TKN_" + hashlib.sha256(name.lower().encode()).hexdigest()[:6].upper()


def anonymize(text: str) -> str:
    """Stable pseudonyms for names; hashes for addresses, tx hashes and market ids; dates
    and years replaced. State numbers are kept on purpose: they are the evidence. Recall
    through distinctive numbers is what the probe and the cutoff gate are for."""
    if not text:
        return text
    out = _HEX64.sub(lambda m: "h_" + hashlib.sha256(m.group().lower().encode()).hexdigest()[:10], text)
    out = _ADDR.sub(lambda m: "addr_" + hashlib.sha256(m.group().lower().encode()).hexdigest()[:10], out)
    for rx in _DATES:
        out = rx.sub("[date]", out)
    for n in sorted(KNOWN_NAMES, key=len, reverse=True):
        out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(n)}(?![A-Za-z0-9_])", _alias(n), out)
    return out


def _capsule_view(c: dict, t0_block) -> dict:
    """Evidence as the agent may see it: absolute block numbers become offsets from T0,
    retrieval timestamps are dropped, everything else goes through anonymize()."""
    c = dict(c)
    c.pop("retrieved_at", None)
    if isinstance(c.get("block"), int):
        b = c.pop("block")
        if isinstance(t0_block, int):
            c["block_offset_from_t0"] = b - t0_block
    return json.loads(anonymize(json.dumps(c, ensure_ascii=False)))


# ------------------------------------------------------------------ requests ----
def _sources_view(case) -> dict:
    return {cls: {"responded": s.responded, "provider": s.provider, "partial": s.partial,
                  "attempts": list(s.attempts)} for cls, s in case.sources.items()}


def request_from_case(case, hist: dict | None = None) -> dict:
    req = {"mode": "verdict", "case_id": case.id, "chain": case.country,
           "access": list(case.consent), "sources": _sources_view(case)}
    if hist is not None:
        req["case_id"] = "h_" + hashlib.sha256(hist["id"].encode()).hexdigest()[:8]
        req["position"] = anonymize(hist.get("position", ""))
        caps = []
        for cls in SOURCE_CLASSES:
            for c in (hist.get("sources") or {}).get(cls, {}).get("capsules", []):
                caps.append(_capsule_view(c, hist.get("t0_block")))
        req["evidence"] = caps
    return req


def narrative_from_verdict(v: dict) -> Narrative:
    outcome = OUTCOME_MAP.get(str(v.get("verdict", "")).upper().replace(" ", "_"))
    if outcome is None:
        raise ValueError(f"unknown verdict {v.get('verdict')!r}")
    cited = {k: (val or None) for k, val in (v.get("citations") or {}).items()}
    return Narrative(outcome=outcome, claims_kyc_verified=bool(v.get("controls_verified")),
                     cites_aml_basis=bool(v.get("anomaly_basis")), cited=cited)


# -------------------------------------------------------------------- agents ----
def call_cmd(cmd: str, payload: dict, timeout: float) -> dict:
    p = subprocess.run(shlex.split(cmd, posix=os.name != "nt"), input=json.dumps(payload), capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"agent exited {p.returncode}: {p.stderr[-500:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def demo_agent(req: dict) -> dict:
    """Honest availability-aware agent: escalates when a needed source is missing and
    cites only sources that answered. It cannot see the gates, so it returns GO on
    decidable cases — a floor, not a reference."""
    if req["mode"] == "probe":
        return {"incident": None}
    s = req["sources"]
    ok = lambda c: s[c]["responded"] and not s[c]["partial"]
    if not ok("onchain_state") or not ok("market_depth") or not (ok("contract_meta") or ok("offchain_meta")):
        return {"verdict": "INSUFFICIENT_DATA", "controls_verified": False,
                "anomaly_basis": True, "citations": {}}
    cites = {"state": s["onchain_state"]["provider"], "depth": s["market_depth"]["provider"],
             "controls": s["contract_meta"]["provider"] or s["offchain_meta"]["provider"]}
    return {"verdict": "GO", "controls_verified": True, "anomaly_basis": True, "citations": cites}


# ---------------------------------------------------------------------- runs ----
def _report(title: str, evals: list[dict]) -> dict:
    a = aggregate(evals)
    print(f"\n{title}  (n={a['n']}, undecidable={a['n_undecidable']})")
    for label, k, ci in (("silent-decision", "silent_rate", "silent_ci"),
                         ("false-positive (NO-GO on GO)", "fp_rate", "fp_ci"),
                         ("controls hallucination", "hall_rate", "hall_ci"),
                         ("over-escalation", "over_rate", "over_ci"),
                         ("provenance completeness", "prov_rate", "prov_ci")):
        lo, hi = a[ci]
        print(f"  {label:<30} {a[k]:7.2%}  [{lo:.2%}, {hi:.2%}]")
    print(f"  {'step-level correctness':<30} {a['step_correct']:7.2%}")
    return a


def run_synthetic(agent, n: int, seed: int, registry: dict) -> dict:
    evals = []
    for c in generate_defi(n, seed, registry):
        evals.append(judge(c, narrative_from_verdict(agent(request_from_case(c)))))
    a = _report(f"synthetic · seed {seed}", evals)
    return {"aggregate": a, "by_chain": by_country(evals)}


def run_historical(agent, path: str, cutoff: str | None) -> dict:
    doc = json.load(open(path, encoding="utf-8"))
    buckets: dict = {"historical": [], "historical_seen": []}
    log = []
    for h in doc["cases"]:
        if not h.get("scored", True):
            continue
        case = historical_to_case(h)
        req = request_from_case(case, h)
        probe = agent({"mode": "probe", "case_id": req["case_id"], "chain": req["chain"],
                       "position": req["position"]})
        named = bool((probe or {}).get("incident"))
        seen = named or (cutoff is not None and h["t0"] <= cutoff)
        ev = judge(case, narrative_from_verdict(agent(req)))
        buckets["historical_seen" if seen else "historical"].append(ev)
        log.append({"id": h["id"], "status": h.get("status"), "eligible": not seen,
                    "probe_named": named, "probe_answer": (probe or {}).get("incident")})
    print("\nrecall probe / cutoff gate:")
    for r in log:
        print(f"  {r['id']:<4} eligible={r['eligible']!s:<5} probe_named={r['probe_named']!s:<5} "
              f"{r['probe_answer'] or ''}")
    out = {"log": log}
    for b, ev in buckets.items():
        if ev:
            out[b] = _report(b + (" (contamination measurement only)" if b.endswith("seen") else ""), ev)
    drafts = sum(r["status"] == "draft" for r in log)
    if drafts:
        print(f"\nNOTE: {drafts} case(s) still 'draft' — facts not yet reconstructed at t0_block. "
              "Not citable.")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="CACE-Bench DeFi adapter")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true")
    g.add_argument("--cmd", help="command that runs your agent (JSON in on stdin, JSON out)")
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sources", default="configs/defi_sources.json")
    ap.add_argument("--historical", metavar="PATH")
    ap.add_argument("--model-cutoff", help="YYYY-MM-DD training cutoff of the agent's model")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--out")
    a = ap.parse_args()
    agent = demo_agent if a.demo else (lambda req: call_cmd(a.cmd, req, a.timeout))
    if a.historical:
        if not a.model_cutoff and not a.demo:
            sys.exit("--model-cutoff is required for historical runs (§5a)")
        res = run_historical(agent, a.historical, a.model_cutoff)
    else:
        res = run_synthetic(agent, a.n, a.seed, json.load(open(a.sources, encoding="utf-8")))
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=2, default=str)


if __name__ == "__main__":
    main()
