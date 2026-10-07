#!/usr/bin/env python3
"""BENCH — regulatory-shift track: compliance-bounded self-evolution with an audit gate.

This module executes the experiment the paper describes and v0.4.1 only specified:
a supervisory re-interpretation at the 70% mark of a chronologically ordered stream,
a dual-loop engine that may change only the runtime harness, and an admission gate
whose every decision is written to a hash-chained log. Every number it prints is an
output of the seeded run; every assumption is a named constant below.

World
-----
The population is the screening-alert queue: every case carries a name hit of one of
five types and a beneficial-ownership chain of depth 1-3. The compliance primitive
decides FLAG or CLEAR. Ground truth is a *rule*, versioned:

* ``v1`` (before T): flag if the hit type is in scope and the stake in the first-layer
  holding is at least 25%.
* ``v2`` (from T): a re-interpretation from one of three families, each at three
  severities (``SHIFTS``):
    - ``thr``    parametric: the ownership threshold rises;
    - ``scope``  clause: some hit types no longer qualify on their own;
    - ``struct`` structural: the threshold applies to the *effective* stake, the
      product of stakes along the chain, which no threshold edit can express.

Where the labels of the retrospective pool come from after the shift
--------------------------------------------------------------------
The pool H is the pre-T stream. At T it is **relabelled by applying rule v2 to the
stored case facts** (``truth(..., rule="v2")``). In a deployment that is the
compliance function encoding the supervisor's re-interpretation; nobody relabels
cases by hand, but a human does author the rule. The engine therefore searches for a
harness edit autonomously while the *target* of that search is set by people: the
adaptation is supervised at the level of the rule and autonomous at the level of the
harness. The arm ``stale_gate`` keeps the v1 labels and shows what happens otherwise.

Harness and agent
-----------------
The harness is a versioned config: the primitive in use, its threshold and its set of
in-scope hit types, rendered to instruction text for the audit log. The agent applies
it and slips (flips its outcome) with probability ``SLIP`` on a per-case draw shared
across harness versions (common random numbers), standing in for LLM execution error.

Loops (see the paper's Algorithms 1-3; every threshold is a constant here)
------------------------------------------------------------------------
Operational feedback arrives per window of ``WINDOW`` cases: every flagged case is
reviewed by an analyst (its false positive becomes visible), cleared cases are audited
at rate ``AUDIT`` (most misses stay invisible). The local loop clusters visible errors
by (hit type, error kind) and proposes one-step edits to the deployed primitive; a
cluster with no admission for ``N_ESC`` consecutive cycles escalates to the global
loop, which proposes primitive replacements from a typed library. Both loops submit
to the same gate.

The proposer is a seeded search over the edit space, not a language model. What this
track measures is therefore the gate and the loop structure under a stated proposer,
not the quality of any LLM's proposals.

Gate (Eq. 1)
------------
Evaluated on ``H_sel`` (half the relabelled pool). Admit iff the paired 95% interval
for the reduction in the target error has a lower bound above zero, and the
regression rate on ``C`` (the cases the deployed harness answers correctly) is at most
``EPS``. ``EPS`` is not zero because execution noise makes strict non-regression
unsatisfiable for any change that touches a case. ``H_val`` (the other half) is never
seen by the gate and is used only to audit its decisions.

    python evolve.py --seeds 10 --out results/shift
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import statistics
from dataclasses import dataclass, field

__version__ = "0.6.0"

# ------------------------------------------------------------------ constants ---
N_CASES = 23000          # alerts per stream
T_FRAC = 0.70            # shift point
EVAL_FRAC = 0.85         # adaptation on [T, EVAL), held-out evaluation on [EVAL, N)
WINDOW = 500             # cases per operational window / cycle
AUDIT = 0.05             # share of cleared cases audited (misses become visible)
SLIP = 0.02              # agent execution error, per case, common across versions
THETA0 = 0.25            # v1 ownership threshold
B_LOCAL = 3              # candidates per cluster per cycle (local)
K_CLUSTERS = 3           # clusters handled per cycle (local)
N_ESC = 3                # cycles without admission before escalation
B_GLOBAL = 6             # candidates per escalation (global)
EPS = 0.005              # non-regression tolerance on C
TAU = 0.05               # global-only trigger: observed flag-FP above pre-T level
MANUAL_LAG = 2000        # cases from T until a human engineer's fix is deployed
Z = 1.959963984540054

HIT_TYPES = ("designation", "adverse_media_high", "adverse_media_low",
             "pep_foreign", "pep_domestic")
HIT_P = (0.25, 0.20, 0.20, 0.15, 0.20)

SHIFTS = {
    "thr":    {"low": 0.30, "mid": 0.40, "high": 0.50},
    "scope":  {"low": ("adverse_media_low",),
               "mid": ("adverse_media_low", "adverse_media_high"),
               "high": ("adverse_media_low", "adverse_media_high", "pep_domestic")},
    "struct": {"low": 0.30, "mid": 0.50, "high": 0.70},
}
P_MULTI_DEFAULT = 0.40   # share of multi-layer chains outside the struct family

# local_only_cm must run after dual: its budget is scaled to the dual loop's proposal count
ARMS = ("healthy", "degraded", "oracle", "manual", "no_gate", "stale_gate",
        "global_only", "local_only", "dual", "local_only_cm")


# ---------------------------------------------------------------------- world ---
@dataclass(frozen=True)
class Case:
    idx: int
    hit: str
    stakes: tuple
    u_slip: float
    u_audit: float

    @property
    def s1(self) -> float:
        return self.stakes[0]

    @property
    def eff(self) -> float:
        return math.prod(self.stakes)


def generate(seed: int, family: str, severity: str, n: int = N_CASES) -> list[Case]:
    p_multi = SHIFTS["struct"][severity] if family == "struct" else P_MULTI_DEFAULT
    out = []
    for i in range(n):
        r = random.Random(f"{seed}:{i}:alert")
        hit = r.choices(HIT_TYPES, weights=HIT_P, k=1)[0]
        s1 = 0.95 * r.random() ** 1.5
        depth = 1
        if r.random() < p_multi:
            depth = 2 if r.random() < 0.6 else 3
        stakes = (s1,) + tuple(r.uniform(0.2, 1.0) for _ in range(depth - 1))
        out.append(Case(i, hit, stakes, r.random(), r.random()))
    return out


def truth(c: Case, family: str, severity: str, rule: str) -> bool:
    """True = FLAG. ``rule`` is 'v1' (before T) or 'v2' (the re-interpretation)."""
    if rule == "v1":
        return c.s1 >= THETA0
    if family == "thr":
        return c.s1 >= SHIFTS["thr"][severity]
    if family == "scope":
        return c.hit not in SHIFTS["scope"][severity] and c.s1 >= THETA0
    return c.eff >= THETA0  # struct


# -------------------------------------------------------------------- harness ---
@dataclass(frozen=True)
class Harness:
    primitive: str            # 'direct_stake_check' | 'effective_stake_check'
    theta: float
    scope: frozenset          # hit types that qualify

    def key(self) -> str:
        return json.dumps({"primitive": self.primitive, "theta": round(self.theta, 4),
                           "scope": sorted(self.scope)}, sort_keys=True)

    def digest(self) -> str:
        return hashlib.sha256(self.key().encode()).hexdigest()

    def render(self) -> str:
        stake = ("the stake held through the first-layer vehicle"
                 if self.primitive == "direct_stake_check"
                 else "the effective stake, the product of stakes along the ownership chain")
        return (f"[{self.primitive}] Flag the applicant if the name hit is one of "
                f"{', '.join(sorted(self.scope))} and {stake} is at least "
                f"{self.theta:.0%}. Otherwise clear.")

    def size(self) -> int:
        return len(self.render())


H0 = Harness("direct_stake_check", THETA0, frozenset(HIT_TYPES))


def decide(h: Harness, c: Case) -> bool:
    stake = c.s1 if h.primitive == "direct_stake_check" else c.eff
    flag = c.hit in h.scope and stake >= h.theta - 1e-12
    return (not flag) if c.u_slip < SLIP else flag


def oracle_harness(family: str, severity: str) -> Harness:
    if family == "thr":
        return Harness("direct_stake_check", SHIFTS["thr"][severity], frozenset(HIT_TYPES))
    if family == "scope":
        return Harness("direct_stake_check", THETA0,
                       frozenset(HIT_TYPES) - frozenset(SHIFTS["scope"][severity]))
    return Harness("effective_stake_check", THETA0, frozenset(HIT_TYPES))


def diff(h: Harness, g: Harness) -> str:
    parts = []
    if h.primitive != g.primitive:
        parts.append(f"primitive {h.primitive} -> {g.primitive}")
    if abs(h.theta - g.theta) > 1e-9:
        parts.append(f"theta {h.theta:.2f} -> {g.theta:.2f}")
    for t in sorted(h.scope - g.scope):
        parts.append(f"scope -{t}")
    for t in sorted(g.scope - h.scope):
        parts.append(f"scope +{t}")
    return "; ".join(parts) or "no-op"


# ------------------------------------------------------------------ audit log ---
class AuditLog:
    """Append-only, hash-chained gate log. A record is written before deployment."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def write(self, rec: dict) -> dict:
        prev = self.records[-1]["hash"] if self.records else "0" * 64
        body = dict(rec, seq=len(self.records), prev=prev, identity="gate@bench")
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self.records.append(body)
        return body

    def verify(self) -> bool:
        prev = "0" * 64
        for r in self.records:
            body = {k: v for k, v in r.items() if k != "hash"}
            if body["prev"] != prev:
                return False
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != r["hash"]:
                return False
            prev = r["hash"]
        return True


# ----------------------------------------------------------------------- gate ---
def paired_gain(h: Harness, g: Harness, cases: list[Case], labels: list[bool], kind: str):
    """Reduction in target errors of ``kind`` ('fp' | 'miss'), paired on the same cases."""
    b = c_ = n = 0
    for c, y in zip(cases, labels):
        if kind == "fp" and y:
            continue
        if kind == "miss" and not y:
            continue
        n += 1
        e_h, e_g = decide(h, c) != y, decide(g, c) != y
        b += e_h and not e_g
        c_ += e_g and not e_h
    if n == 0:
        return 0.0, (0.0, 0.0), b, c_, n
    d = (b - c_) / n
    var = (b + c_) / n**2 - (b - c_) ** 2 / n**3
    se = math.sqrt(max(var, 0.0))
    return d, (d - Z * se, d + Z * se), b, c_, n


def regression(h: Harness, g: Harness, cases: list[Case], labels: list[bool]):
    C = [(c, y) for c, y in zip(cases, labels) if decide(h, c) == y]
    reg = sum(decide(g, c) != y for c, y in C)
    return reg, len(C)


def gate_decision(h, g, kind, pool, labels):
    d, ci, b, c_, n = paired_gain(h, g, pool, labels, kind)
    reg, nC = regression(h, g, pool, labels)
    rate = reg / nC if nC else 0.0
    if ci[0] <= 0:
        reason = "no_significant_improvement"
    elif rate > EPS:
        reason = "regression_on_C"
    else:
        reason = "admitted"
    return reason, {"improvement_ok": ci[0] > 0, "regression_ok": rate <= EPS,
                    "target": kind, "gain": d, "gain_ci": ci, "improved": b,
                    "worsened": c_, "n_target": n, "C_size": nC, "C_regressed": reg,
                    "C_regression_rate": rate}


# ------------------------------------------------------------------- proposers ---
def local_candidates(h: Harness, hit: str, kind: str, rng: random.Random, budget: int):
    pool = []
    if kind == "fp":
        if hit in h.scope:
            pool.append(Harness(h.primitive, h.theta, h.scope - {hit}))
        pool += [Harness(h.primitive, round(min(h.theta + s, 0.95), 4), h.scope)
                 for s in (0.05, 0.10, 0.15, 0.20, 0.25)]
    else:
        if hit not in h.scope:
            pool.append(Harness(h.primitive, h.theta, h.scope | {hit}))
        pool += [Harness(h.primitive, round(max(h.theta - s, 0.05), 4), h.scope)
                 for s in (0.05, 0.10, 0.15)]
    pool = [g for g in pool if g != h]
    rng.shuffle(pool)
    return pool[:budget]


def global_candidates(h: Harness, rng: random.Random, budget: int):
    lib = ("direct_stake_check", "effective_stake_check")
    pool = [Harness(p, t, h.scope) for p in lib for t in
            (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50) if p != h.primitive]
    rng.shuffle(pool)
    return pool[:budget]


# ----------------------------------------------------------------------- run ---
@dataclass
class ArmResult:
    arm: str
    harness: Harness
    log: AuditLog = field(default_factory=AuditLog)
    proposed: int = 0
    admitted: int = 0
    rejected: dict = field(default_factory=dict)
    escalations: int = 0
    window_err: list = field(default_factory=list)   # true v2 error rate per window
    adapt_errors: int = 0
    first_admission_window: int | None = None


def observed_errors(h, window, labels):
    """What operations sees: every flag is reviewed, clears are audited at AUDIT."""
    out = []
    for c, y in zip(window, labels):
        f = decide(h, c)
        if f and not y:
            out.append((c.hit, "fp"))
        elif (not f) and y and c.u_audit < AUDIT:
            out.append((c.hit, "miss"))
    return out


def observed_count(h, window, labels):
    return len(observed_errors(h, window, labels))


def run_arm(arm, cases, family, severity, seed, budget_scale=1):
    n = len(cases)
    T, E = int(T_FRAC * n), int(EVAL_FRAC * n)
    v1 = [truth(c, family, severity, "v1") for c in cases]
    v2 = [truth(c, family, severity, "v2") for c in cases]
    pre = cases[:T]
    sel = [c for c in pre if c.idx % 2 == 0]          # gate selection half
    gate_labels_src = v1 if arm == "stale_gate" else v2
    sel_labels = [gate_labels_src[c.idx] for c in sel]

    res = ArmResult(arm, H0)
    if arm == "oracle":
        res.harness = oracle_harness(family, severity)
    rng = random.Random(f"{seed}:{family}:{severity}:{arm}")
    stall: dict = {}
    b_local = B_LOCAL * budget_scale
    k_clusters = K_CLUSTERS * budget_scale

    # pre-T reference level of observed flag-FP (global-only trigger)
    ref_fp = _observed_flag_fp(H0, pre[-4 * WINDOW:], [v1[c.idx] for c in pre[-4 * WINDOW:]])
    breach_run = 0

    for w0 in range(T, E, WINDOW):
        window = cases[w0:min(w0 + WINDOW, E)]
        wl = [v2[c.idx] for c in window]
        if arm == "manual" and w0 - T >= MANUAL_LAG:
            res.harness = oracle_harness(family, severity)
        errs = sum(decide(res.harness, c) != y for c, y in zip(window, wl))
        res.window_err.append(errs / len(window))
        res.adapt_errors += errs
        if arm in ("healthy", "degraded", "oracle", "manual"):
            continue

        obs = observed_errors(res.harness, window, wl)
        clusters: dict = {}
        for k in obs:
            clusters[k] = clusters.get(k, 0) + 1
        ranked = sorted(clusters, key=lambda k: (-clusters[k], k))[:k_clusters]

        def submit(g, cause, loop):
            res.proposed += 1
            if arm == "no_gate":
                ok = observed_count(g, window, wl) < observed_count(res.harness, window, wl)
                reason, stats = ("admitted" if ok else "no_trace_improvement"), {}
            else:
                reason, stats = gate_decision(res.harness, g, cause[1], sel, sel_labels)
            res.log.write({"t": w0, "loop": loop, "cause": list(cause),
                           "diff": diff(res.harness, g), "h": res.harness.digest(),
                           "h_prime": g.digest(), "h_prime_text": g.render(),
                           "H_sel": stats, "decision": reason})
            if reason == "admitted":
                res.admitted += 1
                res.harness = g
                if res.first_admission_window is None:
                    res.first_admission_window = (w0 - T) // WINDOW
                return True
            res.rejected[reason] = res.rejected.get(reason, 0) + 1
            return False

        if arm == "global_only":
            fp = _observed_flag_fp(res.harness, window, wl)
            breach_run = breach_run + 1 if fp > ref_fp + TAU else 0
            if breach_run >= 2 and ranked:
                res.escalations += 1
                for g in global_candidates(res.harness, rng, B_GLOBAL):
                    if submit(g, ranked[0], "global"):
                        breach_run = 0
                        break
            continue

        for cause in ranked:
            admitted = False
            for g in local_candidates(res.harness, cause[0], cause[1], rng, b_local):
                if submit(g, cause, "local"):
                    admitted = True
                    break
            stall[cause] = 0 if admitted else stall.get(cause, 0) + 1
            if (not admitted and stall[cause] >= N_ESC
                    and arm in ("dual", "no_gate", "stale_gate")):
                res.escalations += 1
                stall[cause] = 0
                for g in global_candidates(res.harness, rng, B_GLOBAL):
                    if submit(g, cause, "global"):
                        break
    return res


def _observed_flag_fp(h, window, labels):
    flags = [(c, y) for c, y in zip(window, labels) if decide(h, c)]
    return sum(not y for _, y in flags) / len(flags) if flags else 0.0


def evaluate(h: Harness, cases, labels, h_ref: Harness):
    tp = fp = fn = tn = 0
    reg = n_c = 0
    for c, y in zip(cases, labels):
        f = decide(h, c)
        tp += f and y
        fp += f and not y
        fn += (not f) and y
        tn += (not f) and not y
        if decide(h_ref, c) == y:
            n_c += 1
            reg += f != y
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "fp_rate": fp / (fp + tn) if fp + tn else 0.0,
            "miss_rate": fn / (fn + tp) if fn + tp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "regressed": reg, "C_E": n_c,
            "regression_rate": reg / n_c if n_c else 0.0}


def run_cell(seed, family, severity, n=N_CASES):
    cases = generate(seed, family, severity, n)
    T, E = int(T_FRAC * n), int(EVAL_FRAC * n)
    ev = cases[E:]
    v1 = [truth(c, family, severity, "v1") for c in ev]
    v2 = [truth(c, family, severity, "v2") for c in ev]
    pre = cases[:T]
    val = [c for c in pre if c.idx % 2 == 1]
    val_v2 = [truth(c, family, severity, "v2") for c in val]

    out = {"seed": seed, "family": family, "severity": severity,
           "n": n, "T": T, "eval_start": E, "arms": {}}
    dual_proposed = None
    oracle_errs = None
    for arm in ARMS:
        scale = 1
        if arm == "local_only_cm":
            assert dual_proposed is not None, "dual must run before local_only_cm"
            scale = max(1, math.ceil(dual_proposed / max(out["arms"]["local_only"]["proposed"], 1)))
        r = run_arm(arm, cases, family, severity, seed, budget_scale=scale)
        labels = v1 if arm == "healthy" else v2
        m = evaluate(r.harness, ev, labels, H0)
        # audit of admissions on the held-out half of the pool (never seen by the gate)
        o_dig = oracle_harness(family, severity).digest()
        oracle_rejected = sum(1 for rec in r.log.records
                              if rec["h_prime"] == o_dig and rec["decision"] != "admitted")
        false_adm = 0
        hist = H0
        for rec in r.log.records:
            if rec["decision"] != "admitted":
                continue
            new = _harness_from_text(rec)
            if _err(new, val, val_v2) > _err(hist, val, val_v2):
                false_adm += 1
            hist = new
        if arm == "oracle":
            oracle_errs = r.adapt_errors
        out["arms"][arm] = {
            **m, "harness": json.loads(r.harness.key()), "harness_text": r.harness.render(),
            "harness_digest": r.harness.digest(), "harness_size": r.harness.size(),
            "proposed": r.proposed, "admitted": r.admitted, "rejected": r.rejected,
            "false_admissions_on_H_val": false_adm, "oracle_candidate_rejected": oracle_rejected, "escalations": r.escalations,
            "budget_scale": scale, "adapt_errors": r.adapt_errors,
            "first_admission_window": r.first_admission_window,
            "window_err": r.window_err, "log_ok": r.log.verify(),
            "log": r.log.records,
        }
        if arm == "dual":
            dual_proposed = r.proposed
    for arm in out["arms"]:
        out["arms"][arm]["excess_adapt_errors"] = out["arms"][arm]["adapt_errors"] - oracle_errs
    return out


def _err(h, cases, labels):
    return sum(decide(h, c) != y for c, y in zip(cases, labels))


def _harness_from_text(rec):
    # the record stores the candidate's rendered text; rebuild from it
    t = rec["h_prime_text"]
    prim = t[1:t.index("]")]
    theta = float(t.split("is at least ")[1].split("%")[0]) / 100
    scope = t.split("is one of ")[1].split(" and ")[0].split(", ")
    return Harness(prim, theta, frozenset(scope))


# ------------------------------------------------------------------- summary ---
def mean_ci(xs):
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, (m, m)
    sd = statistics.stdev(xs)
    # t quantile for 95%, df = n-1 (table for small n)
    tq = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
          8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 14: 2.145, 19: 2.093}.get(len(xs) - 1, 1.96)
    h = tq * sd / math.sqrt(len(xs))
    return m, (m - h, m + h)


def summarise(cells):
    rows = {}
    for cell in cells:
        for arm, a in cell["arms"].items():
            rows.setdefault((cell["family"], cell["severity"], arm), []).append(a)
    out = []
    for (fam, sev, arm), xs in sorted(rows.items()):
        def agg(k):
            m, ci = mean_ci([x[k] for x in xs])
            return {"mean": m, "ci": ci}
        rej = {}
        for x in xs:
            for k, v in x["rejected"].items():
                rej[k] = rej.get(k, 0) + v
        out.append({
            "family": fam, "severity": sev, "arm": arm, "seeds": len(xs),
            "fp_rate": agg("fp_rate"), "miss_rate": agg("miss_rate"),
            "recall": agg("recall"), "precision": agg("precision"),
            "regression_rate": agg("regression_rate"),
            "excess_adapt_errors": agg("excess_adapt_errors"),
            "harness_size": agg("harness_size"),
            "n_true_clear_per_seed": statistics.fmean(x["fp"] + x["tn"] for x in xs),
            "n_true_flag_per_seed": statistics.fmean(x["tp"] + x["fn"] for x in xs),
            "C_E_per_seed": statistics.fmean(x["C_E"] for x in xs),
            "proposed": sum(x["proposed"] for x in xs),
            "admitted": sum(x["admitted"] for x in xs),
            "rejected": rej,
            "false_admissions_on_H_val": sum(x["false_admissions_on_H_val"] for x in xs),
            "escalations": sum(x["escalations"] for x in xs),
            "recovered_to_oracle_seeds": None,
            "logs_verified": all(x["log_ok"] for x in xs),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--families", default="thr,scope,struct")
    ap.add_argument("--severities", default="low,mid,high")
    ap.add_argument("--n", type=int, default=N_CASES)
    ap.add_argument("--out", default="results/shift")
    ap.add_argument("--eps", type=float, default=EPS,
                    help="non-regression tolerance on C (sensitivity runs only)")
    args = ap.parse_args()
    globals()["EPS"] = args.eps
    os.makedirs(args.out, exist_ok=True)
    cells = []
    for fam in args.families.split(","):
        for sev in args.severities.split(","):
            for s in range(args.seeds):
                cell = run_cell(s, fam, sev, args.n)
                cells.append(cell)
                with gzip.open(os.path.join(args.out, f"cell-{fam}-{sev}-seed{s}.json.gz"), "wt",
                               encoding="utf-8") as fh:
                    json.dump(cell, fh, sort_keys=True, separators=(",", ":"))
                d = cell["arms"]["dual"]
                print(f"{fam:6s} {sev:4s} seed {s}: degraded FP "
                      f"{cell['arms']['degraded']['fp_rate']:.3f} -> dual FP {d['fp_rate']:.3f} "
                      f"miss {d['miss_rate']:.3f} | no-gate FP {cell['arms']['no_gate']['fp_rate']:.3f} "
                      f"miss {cell['arms']['no_gate']['miss_rate']:.3f} | prop {d['proposed']} adm {d['admitted']}",
                      flush=True)
    summary = {"version": __version__, "constants": {
        k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, str))},
        "shifts": {f: {s: list(v) if isinstance(v, tuple) else v for s, v in d.items()}
                   for f, d in SHIFTS.items()},
        "rows": summarise(cells)}
    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
