#!/usr/bin/env python3
"""CACE-Bench — regulatory-shift track on real applicants (UCI Statlog German Credit).

The synthetic track (``evolve.py``) draws every case from stated distributions. This
module keeps its engine, gate, arms and audit log unchanged and replaces the case
stream with the 1,000 real applications of the Statlog (German Credit Data) set
(Hofmann 1994, UCI Machine Learning Repository, CC BY 4.0; ``data/real/german.data``,
SHA-256 in ``REAL_SHA256``). Two questions only real data can answer:

1. does the gate behave the same when the joint distribution of the facts it screens
   is a real one rather than a generated one, and
2. does adaptation through the gate change error rates *differently* for women and
   men, or for applicants under and over 25 (the attributes the synthetic benchmark
   omits)?

World
-----
The compliance primitive is an affordability screen that decides FLAG (refer for
enhanced affordability review) or CLEAR. Every fact it reads is a real attribute:

* ``hit`` — the loan purpose, grouped into five classes (``PURPOSE_GROUPS``);
* ``s1`` — a *burden index*: the monthly repayment proxy, credit amount / duration,
  rank-transformed over the 1,000 applicants and mapped as ``0.95 * rank**1.5`` so that
  its marginal distribution is the one the synthetic track uses and every threshold in
  ``evolve.SHIFTS`` keeps its meaning (v1 flags the same share of applicants);
* ``stakes[1:]`` — mitigants that the structural re-interpretation credits: savings
  (``SAVINGS_FACTOR``) and a guarantor or co-applicant (``DEBTOR_FACTOR``). An applicant
  with no mitigant has a chain of depth 1, exactly as in the synthetic track.

Rule v1 flags if the purpose is in scope and the burden index is at least 25%. The
three families of re-interpretation are the synthetic ones: ``thr`` raises the
threshold, ``scope`` removes purposes from scope (``SCOPE_SHIFTS``), ``struct`` applies
the threshold to the burden net of mitigants, with mitigants credited more strongly
at higher severity (``STRUCT_STRENGTH``).

Stream and leakage
------------------
Per seed the 1,000 applicants are split 700 / 300. The stream before the evaluation
point is a bootstrap of the 700 development applicants; the held-out window is a
bootstrap of the other 300, so no evaluated applicant was ever in the gate's pool.
Because the pool is a bootstrap of 700 people, the gate's paired interval treats
duplicated applicants as independent and is therefore optimistic; ``--n 1000`` runs
the same experiment with every applicant used once (sensitivity).

Subgroups
---------
Sex is read from attribute 9 (A92 = female; A91, A93, A94 = male; A95 does not
occur). Age is attribute 13, split at 25. Subgroup rates are computed on the held-out
window for every arm and compared with the oracle harness, which applies rule v2
exactly; a gap that the oracle does not have is a gap the adaptation introduced.

    python evolve_real.py --seeds 10 --out results/shift-real
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
from dataclasses import dataclass

import evolve as E

__version__ = "0.7.0-dev"

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "real", "german.data")
REAL_SHA256 = "b21f3d81db8071257d5ff1deaeba1fd4303b62712e6fcc9715c7a86202cb5871"

PURPOSE_GROUPS = {
    "A40": "car", "A41": "car",
    "A42": "household_goods", "A43": "household_goods", "A44": "household_goods",
    "A45": "repairs_other", "A410": "repairs_other",
    "A46": "education", "A48": "education",
    "A49": "business",
}
GROUPS = ("car", "household_goods", "repairs_other", "education", "business")
SCOPE_SHIFTS = {
    "low": ("education", "repairs_other"),
    "mid": ("education", "repairs_other", "business"),
    "high": ("education", "repairs_other", "business", "household_goods"),
}
# multiplicative credit for a mitigant: (low, mid, high) severity of the struct shift
SAVINGS_FACTOR = {           # attribute 6
    "A61": None,             # < 100 DM: no mitigant
    "A62": (0.90, 0.80, 0.60),   # 100-500 DM
    "A63": (0.80, 0.60, 0.40),   # 500-1000 DM
    "A64": (0.70, 0.40, 0.20),   # >= 1000 DM
    "A65": None,             # unknown / none
}
DEBTOR_FACTOR = {            # attribute 10
    "A101": None,
    "A102": (0.85, 0.70, 0.50),  # co-applicant
    "A103": (0.80, 0.60, 0.40),  # guarantor
}
SEV_IDX = {"low": 0, "mid": 1, "high": 2}
DEV_SHARE = 0.70
AGE_SPLIT = 25


@dataclass(frozen=True)
class RCase(E.Case):
    row: int = -1
    female: bool = False
    young: bool = False
    bad: bool = False         # realised outcome in the data (2 = bad credit)


def load():
    with open(DATA, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != REAL_SHA256:
        raise SystemExit("german.data does not match REAL_SHA256")
    rows = [ln.split() for ln in raw.decode().strip().splitlines()]
    assert len(rows) == 1000 and all(len(r) == 21 for r in rows)
    monthly = [int(r[4]) / int(r[1]) for r in rows]
    order = sorted(range(len(rows)), key=lambda i: (monthly[i], i))
    rank = [0.0] * len(rows)
    for k, i in enumerate(order):
        rank[i] = (k + 0.5) / len(rows)
    out = []
    for i, r in enumerate(rows):
        out.append({
            "row": i, "purpose": PURPOSE_GROUPS[r[3]], "s1": 0.95 * rank[i] ** 1.5,
            "savings": r[5], "debtors": r[9],
            "female": r[8] == "A92", "young": int(r[12]) < AGE_SPLIT,
            "bad": r[20] == "2",
        })
    return out


_APPL = None


def applicants():
    global _APPL
    if _APPL is None:
        _APPL = load()
    return _APPL


def _stakes(a, severity):
    k = SEV_IDX[severity]
    st = [a["s1"]]
    for f in (SAVINGS_FACTOR[a["savings"]], DEBTOR_FACTOR[a["debtors"]]):
        if f is not None:
            st.append(f[k])
    return tuple(st)


def generate(seed: int, family: str, severity: str, n: int = E.N_CASES):
    appl = applicants()
    perm = list(range(len(appl)))
    random.Random(f"{seed}:split").shuffle(perm)
    n_dev = int(DEV_SHARE * len(appl))
    dev, held = perm[:n_dev], perm[n_dev:]
    cut = int(E.EVAL_FRAC * n)
    sev = severity if family == "struct" else "mid"
    out = []
    if n == len(appl):      # sensitivity: every applicant once; the 300 held-out
        seq = dev + held    # applicants fill positions 700-999, so the gate's pool
                            # (positions < T = 700) never contains them
    for i in range(n):
        r = random.Random(f"{seed}:{i}:real")
        if n == len(appl):
            j = seq[i]
        else:
            j = r.choice(dev) if i < cut else r.choice(held)
        a = appl[j]
        out.append(RCase(i, a["purpose"], _stakes(a, sev), r.random(), r.random(),
                         row=a["row"], female=a["female"], young=a["young"], bad=a["bad"]))
    return out


def truth(c, family, severity, rule):
    if rule == "v1":
        return c.s1 >= E.THETA0
    if family == "thr":
        return c.s1 >= E.SHIFTS["thr"][severity]
    if family == "scope":
        return c.hit not in SCOPE_SHIFTS[severity] and c.s1 >= E.THETA0
    return c.eff >= E.THETA0


def render(self):
    burden = ("the burden index (monthly repayment rank)"
              if self.primitive == "direct_stake_check"
              else "the burden index net of savings and guarantor mitigants")
    return (f"[{self.primitive}] Refer the application for enhanced affordability review "
            f"if the loan purpose is one of {', '.join(sorted(self.scope))} and {burden} "
            f"is at least {self.theta:.0%}. Otherwise clear.")


def install():
    """Point the unchanged engine at the real world."""
    E.HIT_TYPES = GROUPS
    E.SHIFTS = dict(E.SHIFTS, scope=SCOPE_SHIFTS)
    E.H0 = E.Harness("direct_stake_check", E.THETA0, frozenset(GROUPS))
    E.generate = generate
    E.truth = truth
    E.Harness.render = render


# --------------------------------------------------------------- subgroups ---
def _rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else 0.0, "ci": [lo, hi]}


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0)
    p, z = k / n, E.Z
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z / d * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def subgroup_metrics(h, cases, labels):
    out = {}
    groups = {"female": lambda c: c.female, "male": lambda c: not c.female,
              "under25": lambda c: c.young, "25plus": lambda c: not c.young}
    for g, sel in groups.items():
        fp = tn = fn = tp = flag = n = 0
        for c, y in zip(cases, labels):
            if not sel(c):
                continue
            f = E.decide(h, c)
            n += 1
            flag += f
            fp += f and not y
            tn += (not f) and not y
            fn += (not f) and y
            tp += f and y
        out[g] = {"fp": _rate(fp, fp + tn), "miss": _rate(fn, fn + tp),
                  "flag": _rate(flag, n), "n": n,
                  "unique_applicants": len({c.row for c, _ in zip(cases, labels) if sel(c)})}
    return out


def harness_from_key(k):
    return E.Harness(k["primitive"], k["theta"], frozenset(k["scope"]))


def run_cell(seed, family, severity, n):
    cell = E.run_cell(seed, family, severity, n)
    cases = generate(seed, family, severity, n)
    ev = cases[cell["eval_start"]:]
    v2 = [truth(c, family, severity, "v2") for c in ev]
    v1 = [truth(c, family, severity, "v1") for c in ev]
    for arm, a in cell["arms"].items():
        h = harness_from_key(a["harness"])
        a["subgroups"] = subgroup_metrics(h, ev, v1 if arm == "healthy" else v2)
        a["bad_rate_flagged"] = _rate(sum(c.bad for c in ev if E.decide(h, c)),
                                      sum(1 for c in ev if E.decide(h, c)))
        a["bad_rate_cleared"] = _rate(sum(c.bad for c in ev if not E.decide(h, c)),
                                      sum(1 for c in ev if not E.decide(h, c)))
    cell["eval_unique_applicants"] = len({c.row for c in ev})
    cell["pool_unique_applicants"] = len({c.row for c in cases[:cell["T"]]})
    cell["world"] = "german_credit"
    return cell


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--families", default="thr,scope,struct")
    ap.add_argument("--severities", default="low,mid,high")
    ap.add_argument("--n", type=int, default=E.N_CASES)
    ap.add_argument("--window", type=int, default=None,
                    help="cases per window (default: evolve.WINDOW; use 50 with --n 1000)")
    ap.add_argument("--out", default="results/shift-real")
    ap.add_argument("--eps", type=float, default=E.EPS,
                    help="non-regression tolerance on C (sensitivity runs only)")
    args = ap.parse_args()
    install()
    E.EPS = args.eps
    if args.window:
        E.WINDOW = args.window
        E.MANUAL_LAG = 4 * args.window
    os.makedirs(args.out, exist_ok=True)
    cells = []
    for fam in args.families.split(","):
        for sev in args.severities.split(","):
            for s in range(args.seeds):
                cell = run_cell(s, fam, sev, args.n)
                cells.append(cell)
                with gzip.open(os.path.join(args.out, f"cell-{fam}-{sev}-seed{s}.json.gz"),
                               "wt", encoding="utf-8") as fh:
                    json.dump(cell, fh, sort_keys=True, separators=(",", ":"))
                d, ng = cell["arms"]["dual"], cell["arms"]["no_gate"]
                print(f"{fam:6s} {sev:4s} seed {s}: degraded FP "
                      f"{cell['arms']['degraded']['fp_rate']:.3f} -> dual FP {d['fp_rate']:.3f} "
                      f"miss {d['miss_rate']:.3f} | no-gate FP {ng['fp_rate']:.3f} "
                      f"miss {ng['miss_rate']:.3f} | prop {d['proposed']} adm {d['admitted']}",
                      flush=True)
    summary = {"version": __version__, "engine_version": E.__version__,
               "world": "german_credit", "data_sha256": REAL_SHA256,
               "n": args.n, "window": E.WINDOW, "eps": E.EPS,
               "rows": E.summarise(cells)}
    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
