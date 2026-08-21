#!/usr/bin/env python3
"""Benchmark YOUR pipeline on CACE-Bench.

Runs the *same* synthetic cases and the *same* deterministic judge as the
reference run, but with your own credit/compliance pipeline in place of the
reference agent. It reports the six adapter-computable metrics — silent-decision
rate, compliance false-positive rate, hallucination rate, over-escalation rate,
provenance completeness and step-level correctness — with 95% Wilson intervals,
per country and in aggregate.

You change exactly two things, both marked ADAPT below:
  1. `call_your_pipeline()` — how a request reaches your system (HTTP by default).
  2. `OUTCOME_MAP` / `narrative_from_response()` — how your response maps back.

Contract (identical to `first_pass` in cace_bench.py):
  * Your adapter is handed one `Case` and must return one `Narrative`.
  * Ground truth (`case.truth`, `case.decidable`) is NEVER sent to your endpoint
    and must never be read by the adapter. This script builds the request from
    `case_to_request()`, which strips it.
  * The judge is unchanged and deterministic; it compares your narrative to the
    case's ground truth and to the set of providers that actually responded.

Recovery rate is intentionally NOT reported here: it is defined by the
self-evolution off/on ablation and needs both arms. If your system has a
verification loop you can switch off, run this twice (loop off, loop on) and
diff the two JSON outputs, or ask us for the two-arm variant.

No third-party dependencies (urllib from the standard library). Put this file
next to cace_bench.py.

    # end-to-end sanity check with a built-in honest adapter (no endpoint needed)
    python benchmark_your_pipeline.py --demo --n 3000 --seed 0

    # against your real system
    python benchmark_your_pipeline.py --endpoint https://your.api/verify --n 3000 --seed 0 \
        --providers configs/providers.json --out results/your_run

Digital Economy Lab · CACE-Bench · MIT
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import urllib.request

from cace_bench import (
    EMBEDDED_REGISTRY, FLAG, CLEAR, ESCALATE, Case, Narrative,
    generate, judge, aggregate, by_country, wilson,
)

# --------------------------------------------------------------------- request --
# What your pipeline is allowed to see. Mirrors what a real deployment could have
# obtained for this applicant — and nothing it could not. `truth`/`decidable` are
# deliberately absent.

def _availability(case: Case) -> tuple[bool, bool, str | None, str | None]:
    """Recompute obtainability the same way the ground truth does.

    screening_available  -> sanctions/PEP/AML are trustworthy
    identity_available    -> KYC / account-holder match is trustworthy
    Returns (screening_available, identity_available, screening_provider,
    identity_provider). A partial payload counts as not-obtained, exactly as in
    cace_bench.ground_truth().
    """
    scr = case.sources["screening"]
    ob = case.sources["open_banking"]
    alt = case.sources["alt_data"]
    screening_available = scr.responded and not scr.partial
    if ob.responded and not ob.partial:
        identity_provider = ob.provider
    elif alt.responded and not alt.partial:
        identity_provider = alt.provider
    else:
        identity_provider = None
    identity_available = identity_provider is not None
    return screening_available, identity_available, scr.provider, identity_provider


def case_to_request(case: Case) -> dict:
    """Serialize a Case into the payload your endpoint receives.

    Signals are *gated by availability*: a fact that could not be obtained is sent
    as null, so a pipeline that decides anyway is making a real silent decision —
    which is exactly what the benchmark measures.
    """
    scr_ok, id_ok, scr_prov, id_prov = _availability(case)
    return {
        "case_id": case.id,
        "country": case.country,
        "consent": list(case.consent),
        # per source class: did the fallback chain answer, who answered, was it
        # partial, and which providers were tried in order.
        "sources": {
            cls: {
                "responded": st.responded,
                "provider": st.provider,
                "partial": st.partial,
                "providers_tried": list(st.attempts),
            }
            for cls, st in case.sources.items()
        },
        # the evidence itself, revealed only when its source was obtained.
        "signals": {
            "screening": {
                "available": scr_ok,
                "provider": scr_prov if scr_ok else None,
                "sanctions_hit": case.sanctions_hit if scr_ok else None,
                "pep_match": case.pep_match if scr_ok else None,
                "aml_alert": case.aml_alert if scr_ok else None,
            },
            "identity": {
                "available": id_ok,
                "provider": id_prov if id_ok else None,
                "kyc_verified": case.kyc_verified if id_ok else None,
            },
        },
    }


# --------------------------------------------------------------------- response --
# ADAPT (2/2): map your system's decision vocabulary to FLAG / CLEAR / ESCALATE.
OUTCOME_MAP = {
    "flag": FLAG, "reject": FLAG, "deny": FLAG, "review": FLAG, "block": FLAG,
    "clear": CLEAR, "approve": CLEAR, "pass": CLEAR, "ok": CLEAR, "accept": CLEAR,
    "escalate": ESCALATE, "manual": ESCALATE, "insufficient_data": ESCALATE,
    "unknown": ESCALATE, "abstain": ESCALATE,
}


def narrative_from_response(resp: dict) -> Narrative:
    """Turn your JSON response into a Narrative the judge can score.

    Expected shape (rename in the .get() calls to match your API):
        {
          "outcome": "clear" | "flag" | "escalate" | <your vocab>,
          "kyc_verified": true/false,          # what your narrative asserts
          "aml_basis_cited": true/false,       # did you state an AML basis
          "citations": {"identity": "<provider>", "screening": "<provider>"}
        }
    Citations must name the providers your decision actually relied on. Citing a
    provider that did not respond is scored as a phantom source and lowers
    provenance completeness — same rule as the reference agent.
    """
    raw = str(resp.get("outcome", "")).strip().lower()
    outcome = OUTCOME_MAP.get(raw)
    if outcome is None:
        raise ValueError(f"Unmapped outcome {resp.get('outcome')!r}; add it to OUTCOME_MAP")
    citations = resp.get("citations") or {}
    return Narrative(
        outcome=outcome,
        claims_kyc_verified=bool(resp.get("kyc_verified", False)),
        cites_aml_basis=bool(resp.get("aml_basis_cited", False)),
        cited={k: (v or None) for k, v in citations.items()},
    )


# ------------------------------------------------------------------- transport --
def call_your_pipeline(request: dict, endpoint: str, timeout: float) -> dict:
    """ADAPT (1/2): send one request to your system, return its JSON response.

    Default is a plain HTTP POST. Swap the body for an SDK call, a queue publish,
    a subprocess, etc. — anything that turns `request` into a response dict.
    """
    data = json.dumps(request).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=data, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def demo_pipeline(request: dict) -> dict:
    """A minimal HONEST pipeline, for the --demo sanity check (no endpoint).

    It reads only the gated request — never the ground truth — and escalates
    whenever the evidence it needed was not obtained. This is roughly what
    "getting it right" looks like; your real agent will differ, and the gaps are
    the point.
    """
    s = request["signals"]["screening"]
    idn = request["signals"]["identity"]
    citations = {"screening": s["provider"], "identity": idn["provider"]}
    if not s["available"]:
        return {"outcome": "escalate", "kyc_verified": False,
                "aml_basis_cited": False, "citations": {}}
    if s["sanctions_hit"] or s["pep_match"]:
        return {"outcome": "flag", "kyc_verified": bool(idn.get("kyc_verified")),
                "aml_basis_cited": True, "citations": citations}
    if not idn["available"]:
        return {"outcome": "escalate", "kyc_verified": False,
                "aml_basis_cited": True, "citations": {"screening": s["provider"]}}
    if not idn["kyc_verified"]:
        return {"outcome": "flag", "kyc_verified": False,
                "aml_basis_cited": True, "citations": citations}
    return {"outcome": "clear", "kyc_verified": True,
            "aml_basis_cited": True, "citations": citations}


# ------------------------------------------------------------------------ run ---
def run_adapter(cases, endpoint, timeout, demo, audit_fh) -> list[dict]:
    evals = []
    for case in cases:
        request = case_to_request(case)
        resp = demo_pipeline(request) if demo else call_your_pipeline(request, endpoint, timeout)
        nar = narrative_from_response(resp)
        evals.append(judge(case, nar))
        if audit_fh:
            audit_fh.write(json.dumps({"request": request, "response": resp}) + "\n")
    return evals


def _pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def _ci(t) -> str:
    return f"[{t[0] * 100:.2f}%, {t[1] * 100:.2f}%]"


def report(evals: list[dict], meta: dict) -> dict:
    a = aggregate(evals)
    n = a["n"]
    step = a["step_correct"]
    step_k = round(step * n)  # Wilson on the rounded mean, for a rough band
    metrics = {
        "silent_decision_rate": {"rate": a["silent_rate"], "ci": a["silent_ci"],
                                 "count": a["silent_count"], "n": a["n_undecidable"]},
        "compliance_false_positive_rate": {"rate": a["fp_rate"], "ci": a["fp_ci"],
                                           "count": a["fp_count"], "n": a["n_clear"]},
        "hallucination_rate": {"rate": a["hall_rate"], "ci": a["hall_ci"],
                               "count": a["hall_count"], "n": n},
        "over_escalation_rate": {"rate": a["over_rate"], "ci": a["over_ci"],
                                 "count": a["over_count"], "n": a["n_decidable"]},
        "provenance_completeness": {"rate": a["prov_rate"], "ci": a["prov_ci"],
                                    "count": a["prov_count"], "n": n},
        "step_level_correctness": {"rate": step, "ci": wilson(step_k, n), "count": step_k, "n": n},
    }
    out = {**meta, "n": n, "n_undecidable": a["n_undecidable"], "n_decidable": a["n_decidable"],
           "n_clear": a["n_clear"], "metrics": metrics, "by_country": by_country(evals)}

    print(f"CACE-Bench · your pipeline · N={n} seed={meta['seed']} registry={meta['registry_version']}")
    print(f"  undecidable: {a['n_undecidable']:,} ({_pct(a['n_undecidable']/n)}) of {n:,}")
    print("  " + "-" * 74)
    label = {
        "silent_decision_rate": "silent-decision (decided although undecidable)",
        "compliance_false_positive_rate": "compliance false-positive",
        "hallucination_rate": "hallucination",
        "over_escalation_rate": "over-escalation",
        "provenance_completeness": "provenance completeness (higher is better)",
        "step_level_correctness": "step-level correctness (higher is better)",
    }
    for key, m in metrics.items():
        print(f"  {label[key]:<46} {_pct(m['rate']):>8}  95% CI {_ci(m['ci'])}  "
              f"n={m['n']:,}")
    print("  " + "-" * 74)
    print("  by country (undecidable share · silent-decision · provenance):")
    for c, v in out["by_country"].items():
        print(f"    {c}: n={v['n']:,}  undec {_pct(v['undecidable_share'])}  "
              f"silent {_pct(v['silent_rate'])}  prov {_pct(v['prov_rate'])}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark your pipeline on CACE-Bench")
    ap.add_argument("--endpoint", help="HTTP endpoint that accepts the request JSON")
    ap.add_argument("--demo", action="store_true",
                    help="run the built-in honest adapter instead of an endpoint")
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--providers", default=None,
                    help="provider registry JSON (default: embedded)")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--out", default=None,
                    help="path prefix: writes <out>.json (metrics) and <out>.audit.jsonl")
    args = ap.parse_args()

    if not args.demo and not args.endpoint:
        ap.error("provide --endpoint <url>, or --demo for the built-in adapter")

    registry = EMBEDDED_REGISTRY
    if args.providers:
        with open(args.providers) as fh:
            registry = json.load(fh)

    cases = generate(args.n, args.seed, registry)

    audit_fh = open(args.out + ".audit.jsonl", "w") if args.out else None
    try:
        evals = run_adapter(cases, args.endpoint, args.timeout, args.demo, audit_fh)
    finally:
        if audit_fh:
            audit_fh.close()

    meta = {
        "benchmark": "CACE-Bench", "mode": "demo" if args.demo else "adapter",
        "endpoint": None if args.demo else args.endpoint,
        "seed": args.seed, "registry_version": registry.get("version", "unknown"),
        "date": _dt.date.today().isoformat(),
        "note": ("Illustrative of the method on synthetic data, not of production "
                 "performance. Recovery rate omitted (needs the off/on ablation)."),
    }
    out = report(evals, meta)

    if args.out:
        with open(args.out + ".json", "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"\n  wrote {args.out}.json and {args.out}.audit.jsonl")


if __name__ == "__main__":
    main()
