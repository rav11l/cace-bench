#!/usr/bin/env python3
"""CACE-Bench — Compliance-Aware Credit-agent Evaluation (single-file reference run).

v0.3 adds the axis that made v0.2 easy to pass and easy to dismiss: **data
availability**. In v0.2 every fact a compliance narrative needed was always
present, so the only way to be wrong was to reason badly. In production the
dominant failure is different — a provider is not live in that country, times
out, or returns a thin payload, and the pipeline decides anyway and cites a
source that never answered.

What v0.3 adds
--------------
* **Countries and provider chains.** Cases are drawn per country; each of the
  three source classes (``open_banking`` / ``alt_data`` / ``screening``) is
  resolved by walking that country's fallback chain from a provider registry
  (``configs/providers.json``, generated from Cauce's ``config/providers.yaml``).
  Only the *structure* of the registry is used — no provider data of any kind.
* **A third ground-truth outcome.** ``FLAG`` / ``CLEAR`` / ``ESCALATE`` where
  ESCALATE is the *correct* answer when the facts needed for the decision were
  not obtainable. A pipeline that never escalates is now measurably wrong.
* **Provenance.** Every claim in the narrative carries the provider it came
  from. Citing a provider that did not respond is a distinct, separately
  reported error class — the one an auditor reproduces first.

New metrics (all with 95% Wilson intervals, from genuine counts)
----------------------------------------------------------------
* ``silent_decision_rate`` — share of *undecidable* cases decided anyway.
  The regulator-facing headline: it is the rate at which the system asserts a
  conclusion it had no data for.
* ``over_escalation_rate`` — share of *decidable* cases escalated needlessly
  (the operational cost of the safety net).
* ``provenance_completeness`` — share of decisions in which every cited source
  actually responded.
* plus v0.2's compliance false-positive rate, hallucination rate, recovery rate
  and step-level correctness, computed the same way so the v0.2 headline stays
  comparable.

The reference run characterises a REFERENCE agent + judge on the synthetic
distribution — not a production LLM pipeline. Swap ``first_pass``/``recover``
for a live adapter to benchmark a real system on the same cases and judge.

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
from dataclasses import dataclass, field

__version__ = "0.3.0"

# --------------------------------------------------------------- registry ----
# Embedded fallback so the file stays runnable on its own. `--providers` loads
# the registry exported from Cauce's config/providers.yaml.
EMBEDDED_REGISTRY: dict = {
    "version": "embedded-default",
    "providers": {
        "prometeo": {"class": "open_banking", "partial_rate": 0.15,
                     "countries": {"EC": 0.60, "MX": 0.65, "CO": 0.60, "BR": 0.55,
                                   "CL": 0.60, "PE": 0.60, "AR": 0.60}},
        "belvo": {"class": "open_banking", "partial_rate": 0.12,
                  "countries": {"MX": 0.75, "BR": 0.70, "CO": 0.65}},
        "finvero": {"class": "open_banking", "partial_rate": 0.18,
                    "countries": {"MX": 0.60}},
        "riskseal": {"class": "alt_data", "partial_rate": 0.10,
                     "countries": {"EC": 0.85, "MX": 0.88, "CO": 0.86, "BR": 0.86,
                                   "CL": 0.85, "PE": 0.84, "AR": 0.84}},
        "altscore": {"class": "alt_data", "partial_rate": 0.15,
                     "countries": {"EC": 0.70, "MX": 0.65}},
        "begini": {"class": "alt_data", "partial_rate": 0.20,
                   "countries": {"EC": 0.55, "MX": 0.60, "CO": 0.55}},
        "abaco": {"class": "alt_data", "partial_rate": 0.20,
                  "countries": {"CO": 0.60}},
        "screening_vendor_tbd": {"class": "screening", "partial_rate": 0.03,
                                 "countries": {"EC": 0.97, "MX": 0.97, "CO": 0.97,
                                               "BR": 0.97, "CL": 0.97, "PE": 0.97,
                                               "AR": 0.97}},
    },
    "chains": {
        "EC": {"open_banking": ["prometeo"], "alt_data": ["altscore", "riskseal", "begini"],
               "screening": ["screening_vendor_tbd"]},
        "MX": {"open_banking": ["belvo", "prometeo", "finvero"],
               "alt_data": ["riskseal", "altscore", "begini"],
               "screening": ["screening_vendor_tbd"]},
        "CO": {"open_banking": ["belvo", "prometeo"], "alt_data": ["riskseal", "abaco", "begini"],
               "screening": ["screening_vendor_tbd"]},
        "BR": {"open_banking": ["belvo", "prometeo"], "alt_data": ["riskseal"],
               "screening": ["screening_vendor_tbd"]},
        "CL": {"open_banking": ["prometeo"], "alt_data": ["riskseal"],
               "screening": ["screening_vendor_tbd"]},
        "PE": {"open_banking": ["prometeo"], "alt_data": ["riskseal"],
               "screening": ["screening_vendor_tbd"]},
        "AR": {"open_banking": ["prometeo"], "alt_data": ["riskseal"],
               "screening": ["screening_vendor_tbd"]},
    },
}

# Share of applications per country in the reference population. Documented as a
# parameter, not a claim about any real market.
COUNTRY_MIX = {"EC": 0.30, "MX": 0.30, "CO": 0.15, "BR": 0.10,
               "CL": 0.05, "PE": 0.05, "AR": 0.05}

SOURCE_CLASSES = ("open_banking", "alt_data", "screening")

# Population base rates. Kept identical to v0.2 so the two versions stay
# comparable; see METHODOLOGY.md §4 for why these are placeholders that a
# supervisor-facing report must replace with cited figures.
P_SANCTIONS, P_PEP, P_AML, P_KYC_VERIFIED = 0.05, 0.03, 0.20, 0.85

# Consent is itself a gate: a borrower may decline a scope. A declined scope is
# indistinguishable, downstream, from an unavailable provider — and both must
# lead to ESCALATE rather than a guess.
P_CONSENT = {"open_banking": 0.90, "alt_data": 0.85, "screening": 1.00}

FLAG, CLEAR, ESCALATE = "flag", "clear", "escalate"


# ---------------------------------------------------------------- generator ---
@dataclass(frozen=True)
class SourceState:
    """Outcome of walking one country's fallback chain for one source class."""

    responded: bool
    provider: str | None
    partial: bool
    attempts: tuple[str, ...]  # providers tried, in order


@dataclass(frozen=True)
class Case:
    id: str
    country: str
    sanctions_hit: bool
    pep_match: bool
    aml_alert: bool
    kyc_verified: bool
    difficulty: float
    consent: tuple[str, ...]
    sources: dict = field(hash=False, compare=False)  # class -> SourceState
    truth: str  # FLAG / CLEAR / ESCALATE
    decidable: bool


def _walk_chain(chain: list[str], providers: dict, country: str, rng: random.Random) -> SourceState:
    attempts: list[str] = []
    for pid in chain:
        p = providers.get(pid)
        if not p:
            continue
        coverage = (p.get("countries") or {}).get(country)
        if coverage is None:
            continue  # provider not live in this country — not even an attempt
        attempts.append(pid)
        if rng.random() < coverage:
            partial = rng.random() < p.get("partial_rate", 0.0)
            return SourceState(True, pid, partial, tuple(attempts))
    return SourceState(False, None, False, tuple(attempts))


def ground_truth(sanctions_hit: bool, pep_match: bool, kyc_verified: bool,
                 sources: dict) -> tuple[str, bool]:
    """The correct outcome given what was actually obtainable.

    Order matters and mirrors the pipeline: screening decides first (a sanctions
    hit is dispositive), then identity. A fact that could not be obtained makes
    the case undecidable — ESCALATE is then the *correct* answer, not a failure.
    """
    screening = sources["screening"]
    if not screening.responded or screening.partial:
        return ESCALATE, False
    if sanctions_hit or pep_match:
        return FLAG, True
    # Identity is verifiable from the bank (account-holder match) or, more
    # weakly, from a complete alt-data payload.
    ob, alt = sources["open_banking"], sources["alt_data"]
    identity_verifiable = (ob.responded and not ob.partial) or (alt.responded and not alt.partial)
    if not identity_verifiable:
        return ESCALATE, False
    if not kyc_verified:
        return FLAG, True
    return CLEAR, True


def generate(n: int, seed: int, registry: dict) -> list[Case]:
    rng = random.Random(seed)
    providers = registry["providers"]
    chains = registry["chains"]
    countries = list(COUNTRY_MIX)
    weights = [COUNTRY_MIX[c] for c in countries]
    out: list[Case] = []
    for i in range(n):
        country = rng.choices(countries, weights=weights, k=1)[0]
        consent = tuple(c for c in SOURCE_CLASSES if rng.random() < P_CONSENT[c])
        sources: dict = {}
        for cls in SOURCE_CLASSES:
            if cls not in consent:
                sources[cls] = SourceState(False, None, False, ())
                continue
            sources[cls] = _walk_chain(chains.get(country, {}).get(cls, []), providers, country, rng)
        s = rng.random() < P_SANCTIONS
        p = rng.random() < P_PEP
        a = rng.random() < P_AML
        k = rng.random() < P_KYC_VERIFIED
        d = rng.random()
        truth, decidable = ground_truth(s, p, k, sources)
        out.append(Case(f"c{i:06d}", country, s, p, a, k, d, consent, sources, truth, decidable))
    return out


# ------------------------------------------------------------- reference agent --
@dataclass
class Narrative:
    outcome: str
    claims_kyc_verified: bool
    cites_aml_basis: bool
    # provider cited for each claim; None means "asserted without a source"
    cited: dict = field(default_factory=dict)
    err_fp: bool = False           # cleared case flagged
    err_miss: bool = False         # flaggable case cleared
    err_silent: bool = False       # undecidable case decided anyway
    err_over_escalate: bool = False  # decidable case escalated
    err_hallucination: bool = False
    err_aml_missing: bool = False
    err_phantom_source: bool = False  # cited a provider that did not respond


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _responding(case: Case) -> list[str]:
    return [s.provider for s in case.sources.values() if s.responded and s.provider]


def first_pass(case: Case, params: dict, seed: int) -> Narrative:
    """Self-evolution OFF: a single, availability-blind pass.

    The baseline agent does not check whether the sources it needed answered. It
    therefore produces two error families that v0.2 could not express: deciding
    on undecidable cases, and citing providers that never responded.
    """
    rng = random.Random(f"{seed}:{case.id}")
    d = case.difficulty
    n = Narrative(outcome=case.truth, claims_kyc_verified=case.kyc_verified, cites_aml_basis=True)

    if not case.decidable:
        # Correct answer is ESCALATE. The blind agent guesses instead.
        if rng.random() < _clamp(params["silent_base"] * (0.5 + d)):
            n.outcome = CLEAR if rng.random() < 0.7 else FLAG
            n.err_silent = True
    else:
        if case.truth == CLEAR and rng.random() < _clamp(params["fp_base"] * d):
            n.outcome, n.err_fp = FLAG, True
        elif case.truth == FLAG and rng.random() < _clamp(params["fn_base"] * d):
            n.outcome, n.err_miss = CLEAR, True
        elif rng.random() < _clamp(params["over_escalate_base"] * d):
            n.outcome, n.err_over_escalate = ESCALATE, True

    if not case.kyc_verified and rng.random() < _clamp(params["h_base"] * d):
        n.claims_kyc_verified, n.err_hallucination = True, True
    if case.aml_alert and rng.random() < _clamp(params["aml_miss_base"] * d):
        n.cites_aml_basis, n.err_aml_missing = False, True

    # Provenance. A correct narrative cites only providers that responded.
    live = _responding(case)
    n.cited = {"identity": live[0] if live else None,
               "screening": case.sources["screening"].provider}
    if n.outcome != ESCALATE and rng.random() < _clamp(params["phantom_base"] * (0.5 + d)):
        missing = [s.attempts[-1] for s in case.sources.values()
                   if not s.responded and s.attempts]
        if missing:
            n.cited["identity"] = missing[0]
            n.err_phantom_source = True
    if n.cited.get("screening") is None and n.outcome != ESCALATE:
        # Asserted a screening conclusion with nothing behind it.
        n.err_phantom_source = True
    return n


def recover(nar: Narrative, case: Case, params: dict, seed: int) -> Narrative:
    """Self-evolution ON: judge + recovery.

    Each real first-pass error is detected with prob ``detect`` and corrected
    with prob ``correct`` (independent draws) — same mechanism as v0.2, extended
    to the three new error classes. Availability errors get a higher detection
    rate (``detect_availability``) because they are checkable against the
    provider-attempt log rather than requiring judgement.
    """
    rng = random.Random(f"{seed}:{case.id}:rec")
    det, corr = params["detect"], params["correct"]
    det_av = params["detect_availability"]

    def fixed(detect_p: float = None) -> bool:
        a, b = rng.random(), rng.random()
        return a < (det if detect_p is None else detect_p) and b < corr

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
        live = _responding(case)
        n.cited = {"identity": live[0] if live else None,
                   "screening": case.sources["screening"].provider}
        n.err_phantom_source = False
    return n


# -------------------------------------------------------------------- judge -----
def judge(case: Case, nar: Narrative) -> dict:
    """Deterministic ground-truth judge (exact scoring on synthetic data)."""
    live = set(_responding(case))
    cited = [v for v in nar.cited.values() if v is not None]
    provenance_ok = bool(cited) and all(c in live for c in cited)
    if nar.outcome == ESCALATE:
        provenance_ok = True  # an escalation asserts nothing that needs a source

    points = [
        nar.outcome == case.truth,
        nar.claims_kyc_verified == case.kyc_verified,
        provenance_ok,
    ]
    if case.aml_alert:
        points.append(nar.cites_aml_basis)

    return {
        # v0.2-comparable: a truly-clear case wrongly flagged
        "false_positive": nar.outcome == FLAG and case.truth == CLEAR,
        "hallucination": nar.claims_kyc_verified and not case.kyc_verified,
        # v0.3: decided (flag or clear) although the facts were unobtainable
        "silent_decision": (not case.decidable) and nar.outcome != ESCALATE,
        "over_escalation": case.decidable and nar.outcome == ESCALATE,
        "provenance_ok": provenance_ok,
        "step_correct": sum(points) / len(points),
        "decidable": case.decidable,
        "truth_clear": case.truth == CLEAR,
        "country": case.country,
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
    if not n1 or not n2:
        return (0.0, 0.0)
    p1, p2 = k1 / n1, k2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return (d - Z * se, d + Z * se)


def aggregate(evals: list[dict]) -> dict:
    n = len(evals)
    n_clear = sum(e["truth_clear"] for e in evals)
    n_dec = sum(e["decidable"] for e in evals)
    n_undec = n - n_dec
    fp = sum(e["false_positive"] for e in evals)
    hall = sum(e["hallucination"] for e in evals)
    silent = sum(e["silent_decision"] for e in evals)
    over = sum(e["over_escalation"] for e in evals)
    prov = sum(e["provenance_ok"] for e in evals)
    step = sum(e["step_correct"] for e in evals) / n if n else 0.0
    return {
        "n": n, "n_clear": n_clear, "n_decidable": n_dec, "n_undecidable": n_undec,
        "fp_count": fp, "fp_rate": fp / n_clear if n_clear else 0.0, "fp_ci": wilson(fp, n_clear),
        "hall_count": hall, "hall_rate": hall / n if n else 0.0, "hall_ci": wilson(hall, n),
        "silent_count": silent, "silent_rate": silent / n_undec if n_undec else 0.0,
        "silent_ci": wilson(silent, n_undec),
        "over_count": over, "over_rate": over / n_dec if n_dec else 0.0,
        "over_ci": wilson(over, n_dec),
        "prov_count": prov, "prov_rate": prov / n if n else 0.0, "prov_ci": wilson(prov, n),
        "step_correct": step,
    }


def by_country(evals: list[dict]) -> dict:
    out: dict = {}
    for c in sorted({e["country"] for e in evals}):
        sub = [e for e in evals if e["country"] == c]
        a = aggregate(sub)
        out[c] = {"n": a["n"], "undecidable_share": a["n_undecidable"] / a["n"],
                  "silent_rate": a["silent_rate"], "prov_rate": a["prov_rate"]}
    return out


# --------------------------------------------------------------------- run ------
DEFAULT_PARAMS = {
    "fp_base": 0.45, "fn_base": 0.30, "h_base": 0.35, "aml_miss_base": 0.35,
    "silent_base": 0.55, "over_escalate_base": 0.10, "phantom_base": 0.30,
    "detect": 0.85, "correct": 0.92, "detect_availability": 0.95,
}

_ERR_FIELDS = ("err_fp", "err_miss", "err_silent", "err_over_escalate",
               "err_hallucination", "err_aml_missing", "err_phantom_source")


def _errs(nar: Narrative) -> int:
    return sum(int(getattr(nar, f)) for f in _ERR_FIELDS)


def run(n: int, seed: int, params: dict, registry: dict) -> dict:
    cases = generate(n, seed, registry)
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

    def delta(key_rate, key_count, key_den):
        return {"off": off[key_rate], "on": on[key_rate],
                "abs": off[key_rate] - on[key_rate],
                "rel": rel(off[key_rate], on[key_rate]),
                "diff_ci": diff_ci(off[key_count], off[key_den], on[key_count], on[key_den])}

    return {
        "benchmark": "CACE-Bench", "version": __version__, "seed": seed, "n": n,
        "registry_version": registry.get("version", "unknown"),
        "params": params, "country_mix": COUNTRY_MIX,
        "arms": {"off": off, "on": on}, "recovery_rate": rec,
        "first_pass_errors": first_err, "remaining_errors": remaining_err,
        "deltas": {
            "compliance_fp": delta("fp_rate", "fp_count", "n_clear"),
            "hallucination": delta("hall_rate", "hall_count", "n"),
            "silent_decision": delta("silent_rate", "silent_count", "n_undecidable"),
            "over_escalation": delta("over_rate", "over_count", "n_decidable"),
            "provenance": delta("prov_rate", "prov_count", "n"),
        },
        "by_country": {"off": by_country(ev_off), "on": by_country(ev_on)},
    }


def _pct(x):
    return f"{x*100:.2f}%"


def _report_md(r: dict, date: str) -> str:
    off, on = r["arms"]["off"], r["arms"]["on"]
    d = r["deltas"]

    def ci(t):
        return f"[{t[0]*100:.2f}%, {t[1]*100:.2f}%]"

    rows = [
        ("Silent-decision rate (decided although undecidable)", "silent_decision", off["n_undecidable"]),
        ("Compliance false-positive rate", "compliance_fp", off["n_clear"]),
        ("Hallucination rate", "hallucination", r["n"]),
        ("Over-escalation rate", "over_escalation", off["n_decidable"]),
    ]
    body = "\n".join(
        f"| {label} | {_pct(d[k]['off'])} | {_pct(d[k]['on'])} | −{d[k]['rel']*100:.1f}% | {ci(d[k]['diff_ci'])} | {n:,} |"
        for label, k, n in rows
    )
    cty = "\n".join(
        f"| {c} | {v['n']:,} | {_pct(v['undecidable_share'])} | {_pct(v['silent_rate'])} | "
        f"{_pct(r['by_country']['on'][c]['silent_rate'])} | {_pct(r['by_country']['on'][c]['prov_rate'])} |"
        for c, v in r["by_country"]["off"].items()
    )

    return f"""# CACE-Bench — Result Report

- **Run date:** {date}
- **Benchmark version:** {r['version']}   ·   **Provider registry:** {r['registry_version']}
- **Seed:** {r['seed']}   ·   **N:** {r['n']:,} synthetic cases per arm
- **Judge:** deterministic ground-truth verifier (exact scoring on synthetic data)
- **Ablation:** self-evolution OFF (single, availability-blind pass) vs ON (judge + recovery loop)
- **Parameters:** {json.dumps(r['params'])}
- **Country mix:** {json.dumps(r['country_mix'])}

Of {r['n']:,} cases, **{off['n_undecidable']:,} ({_pct(off['n_undecidable']/r['n'])}) were
undecidable** — the consented sources needed for the compliance conclusion did not all
respond — so ESCALATE is the correct outcome for them. That population does not exist in
v0.2 and is where the interesting failure lives.

## Results

Baseline = self-evolution **off** · CACE = self-evolution **on**. Lower is better for
every row below except provenance completeness.

| Metric | Baseline | CACE | Δ | 95% CI (Δ, abs) | n |
|---|---|---|---|---|---|
{body}
| Provenance completeness (higher is better) | {_pct(d['provenance']['off'])} | {_pct(d['provenance']['on'])} | +{(d['provenance']['on']-d['provenance']['off'])*100:.2f} pp | {ci(d['provenance']['diff_ci'])} | {r['n']:,} |
| Recovery rate | — | {_pct(r['recovery_rate'])} | — | — | {r['first_pass_errors']:,} first-pass errors |
| Step-level correctness | {_pct(off['step_correct'])} | {_pct(on['step_correct'])} | +{(on['step_correct']-off['step_correct'])*100:.2f} pp | — | {r['n']:,} |

Per-arm 95% Wilson intervals — silent decision: baseline {ci(off['silent_ci'])}, CACE {ci(on['silent_ci'])}.
Compliance FP: baseline {ci(off['fp_ci'])}, CACE {ci(on['fp_ci'])}.
Provenance: baseline {ci(off['prov_ci'])}, CACE {ci(on['prov_ci'])}.

## By country

Undecidable share is a property of the **provider chain**, not of the agent: it is what
the registry's coverage assumptions imply for that country. It is the number to put in
front of a supervisor when explaining why the pipeline escalates more in one market.

| Country | n | Undecidable | Silent-decision (baseline) | Silent-decision (CACE) | Provenance (CACE) |
|---|---|---|---|---|---|
{cty}

## Interpretation

The availability-blind baseline decides {_pct(d['silent_decision']['off'])} of undecidable
cases anyway; the judge + recovery loop, which can check each claim against the
provider-attempt log, brings that to {_pct(d['silent_decision']['on'])}
(−{d['silent_decision']['rel']*100:.1f}%, 95% CI on the absolute reduction
{ci(d['silent_decision']['diff_ci'])}). Provenance completeness rises from
{_pct(d['provenance']['off'])} to {_pct(d['provenance']['on'])} — i.e. the share of
decisions in which every cited source actually answered.

## Caveats for this run

- Data is **100% synthetic**; results characterise the **reference agent + judge** on this
  distribution, not a production LLM pipeline. Swap `first_pass`/`recover` for a live
  adapter to benchmark a real system.
- Provider coverage figures come from the registry and are **working assumptions until a
  provider confirms them** (`verified: false` in `config/providers.yaml`). They change the
  undecidable share, and therefore every rate reported per country. State this plainly.
- The first-pass error model and the recovery detect/correct rates are documented
  parameters (above); the counts and CIs are genuine outputs of the seeded run and
  reproducible by anyone with the same seed, version and registry.

---
*Signed:* generated by cace_bench.py v{r['version']} · Digital Economy Lab
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="CACE-Bench reference run")
    ap.add_argument("--n", type=int, default=23000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results")
    ap.add_argument("--config", default=None, help="optional JSON with a 'params' object")
    ap.add_argument("--providers", default=None,
                    help="provider registry JSON (default: embedded); "
                         "generate from Cauce's config/providers.yaml")
    ap.add_argument("--date", default=None, help="override run date (YYYY-MM-DD)")
    args = ap.parse_args()

    params = dict(DEFAULT_PARAMS)
    if args.config:
        with open(args.config) as fh:
            params.update(json.load(fh).get("params", {}))

    registry = EMBEDDED_REGISTRY
    if args.providers:
        with open(args.providers) as fh:
            registry = json.load(fh)

    r = run(args.n, args.seed, params, registry)
    date = args.date or _dt.date.today().isoformat()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, f"run-seed{args.seed}.json"), "w") as fh:
        json.dump(r, fh, indent=2)
    with open(os.path.join(args.out, f"REPORT-{date}.md"), "w") as fh:
        fh.write(_report_md(r, date))

    off, on = r["arms"]["off"], r["arms"]["on"]
    d = r["deltas"]
    print(f"N={r['n']} seed={r['seed']} registry={r['registry_version']}")
    print(f"  undecidable:     {off['n_undecidable']} ({_pct(off['n_undecidable']/r['n'])}) of {r['n']}")
    print(f"  silent decision: {_pct(d['silent_decision']['off'])} -> {_pct(d['silent_decision']['on'])}"
          f"  (-{d['silent_decision']['rel']*100:.1f}%)  counts "
          f"{off['silent_count']}->{on['silent_count']} of {off['n_undecidable']}")
    print(f"  compliance FP:   {_pct(d['compliance_fp']['off'])} -> {_pct(d['compliance_fp']['on'])}"
          f"  (-{d['compliance_fp']['rel']*100:.1f}%)  counts "
          f"{off['fp_count']}->{on['fp_count']} of {off['n_clear']}")
    print(f"  hallucination:   {_pct(d['hallucination']['off'])} -> {_pct(d['hallucination']['on'])}"
          f"  (-{d['hallucination']['rel']*100:.1f}%)")
    print(f"  over-escalation: {_pct(d['over_escalation']['off'])} -> {_pct(d['over_escalation']['on'])}")
    print(f"  provenance:      {_pct(d['provenance']['off'])} -> {_pct(d['provenance']['on'])}")
    print(f"  recovery_rate:   {_pct(r['recovery_rate'])}   step-correct: "
          f"{_pct(off['step_correct'])} -> {_pct(on['step_correct'])}")


if __name__ == "__main__":
    main()
