#!/usr/bin/env python3
"""Compare the language-model proposer with the seeded proposer on the same cells.

    # tables.md for any grid (written into the LLM results directory)
    python tools/llm_tables.py results/shift-llm-api results/shift --severities low,mid,high
    python tools/llm_tables.py results/shift-llm-real results/shift-real --world real --severities low,mid,high

    # additionally the paper's macros and table (mid severity), into paper/generated
    python tools/llm_tables.py results/shift-llm results/shift paper/generated

Besides the end-of-stream metrics stored in each cell, it reconstructs every arm's deployed
harness window by window from the admissions in the gate log and counts the flags that were
missed *during* adaptation (the windows between the shift and the evaluation point). The
reconstruction is checked against the error count the engine logged for the same windows.
"""
import argparse
import glob
import gzip
import json
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import evolve as E  # noqa: E402

ap = argparse.ArgumentParser(description="LLM vs seeded proposer tables")
ap.add_argument("llm", help="results directory of proposer_llm.py")
ap.add_argument("seeded", help="results directory of the seeded run on the same world")
ap.add_argument("out", nargs="?", default=None,
                help="paper/generated: also write numbers_llm.tex and tab_llm.tex (mid severity)")
ap.add_argument("--severities", default="mid")
ap.add_argument("--world", choices=("synthetic", "real"), default="synthetic")
A = ap.parse_args()
if A.world == "real":
    import evolve_real  # noqa: E402
    evolve_real.install()

FAMS = ("thr", "scope", "struct")
ARMS = ("no_gate", "dual")
SEVS = A.severities.split(",")
NAMES = {"thr": "Threshold", "scope": "Scope", "struct": "Structural"}


def load(d, fam, sev, seeds):
    return [json.load(gzip.open(os.path.join(d, f"cell-{fam}-{sev}-seed{s}.json.gz"), "rt"))
            for s in seeds]


def n_seeds(d, fam, sev):
    return len(glob.glob(os.path.join(d, f"cell-{fam}-{sev}-seed*.json.gz")))


def adaptation(c, arm):
    fam, sev, seed = c["family"], c["severity"], c["seed"]
    cases = E.generate(seed, fam, sev, c["n"])
    n = len(cases)
    T, Ev = int(E.T_FRAC * n), int(E.EVAL_FRAC * n)
    v2 = [E.truth(x, fam, sev, "v2") for x in cases]
    adm = [r for r in c["arms"][arm]["log"] if r["decision"] == "admitted"]
    h, fn, pos, worst, errs = E.H0, 0, 0, 0.0, 0
    for w0 in range(T, Ev, E.WINDOW):
        win = cases[w0:min(w0 + E.WINDOW, Ev)]
        f = sum((not E.decide(h, x)) and v2[x.idx] for x in win)
        p = sum(v2[x.idx] for x in win)
        errs += sum(E.decide(h, x) != v2[x.idx] for x in win)
        fn, pos, worst = fn + f, pos + p, max(worst, f / p if p else 0.0)
        for r in adm:                      # admissions at w0 take effect from the next window
            if r["t"] == w0:
                h = E._harness_from_text(r)
    assert errs == c["arms"][arm]["adapt_errors"], "reconstruction does not match the log"
    return fn, pos, worst


def stats(cs, arm):
    ad = [adaptation(c, arm) for c in cs]
    T0 = int(E.T_FRAC * cs[0]["n"])
    done = []                              # window in which the oracle harness was admitted
    for c in cs:
        o = c["arms"]["oracle"]["harness_digest"]
        ts = [r["t"] for r in c["arms"][arm]["log"] if r["decision"] == "admitted" and r["h_prime"] == o]
        done.append((ts[0] - T0) // E.WINDOW if ts else None)
    xs = [c["arms"][arm] for c in cs]
    return dict(
        am=100 * sum(a[0] for a in ad) / max(sum(a[1] for a in ad), 1),
        ww=100 * max(a[2] for a in ad),
        fm=100 * S.mean(x["miss_rate"] for x in xs),
        fp=100 * S.mean(x["fp_rate"] for x in xs),
        prop=sum(x["proposed"] for x in xs), adm=sum(x["admitted"] for x in xs),
        harm=sum(x["false_admissions_on_H_val"] for x in xs),
        reach=sum(x["harness_digest"] == c["arms"]["oracle"]["harness_digest"] for x, c in zip(xs, cs)),
        ex=S.mean(x["excess_adapt_errors"] for x in xs),
        fw=[x["first_admission_window"] for x in xs], done=done, n=len(cs))


out = {}
for sev in SEVS:
    for fam in FAMS:
        k = n_seeds(A.llm, fam, sev)
        if not k:
            continue
        L, R = load(A.llm, fam, sev, range(k)), load(A.seeded, fam, sev, range(k))
        for lab, cs in (("LLM", L), ("seeded", R)):
            for arm in ARMS:
                out[(sev, fam, lab, arm)] = stats(cs, arm)

summ = json.load(open(os.path.join(A.llm, "summary.json")))
ps = summ["proposer_stats"]
md = [f"# Language-model vs seeded proposer — {A.llm} vs {A.seeded}\n",
      "| Severity | Family | Proposer | Arm | Runs | Proposed | Admitted | Harmful | Reached oracle | "
      "Final FP % | Final miss % | Miss during adaptation % | Worst window % | Excess errors | "
      "Oracle admitted in window |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for (sev, fam, lab, arm), v in out.items():
    dn = [x for x in v["done"] if x is not None]
    md.append(f"| {sev} | {fam} | {lab} | {arm} | {v['n']} | {v['prop']} | {v['adm']} | {v['harm']} | "
              f"{v['reach']}/{v['n']} | {v['fp']:.1f} | {v['fm']:.1f} | {v['am']:.1f} | {v['ww']:.1f} | "
              f"{v['ex']:.0f} | {(str(min(dn)) + '–' + str(max(dn))) if dn else '—'} |")
for lab in ("LLM", "seeded"):
    for arm in ARMS:
        vs = [v for (s, f, l, a), v in out.items() if l == lab and a == arm]
        md.append(f"\nTotal {lab} {arm}: {sum(v['n'] for v in vs)} runs, proposed {sum(v['prop'] for v in vs)}, "
                  f"admitted {sum(v['adm'] for v in vs)}, harmful {sum(v['harm'] for v in vs)}, "
                  f"reached oracle {sum(v['reach'] for v in vs)}")
md.append(f"\nProposer: {summ['proposer']}; stats: {ps}")
open(os.path.join(A.llm, "tables.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))

if A.out:                                  # the paper's macros and table: mid severity
    assert "mid" in SEVS
    macros = []

    def mac(k, v):
        assert k.isalpha(), k
        macros.append(f"\\newcommand{{\\{k}}}{{{v}}}")

    def fmt(n):
        return f"{n:,}".replace(",", "{,}")

    g = lambda fam, lab, arm, k: out[("mid", fam, lab, arm)][k]
    nruns = sum(g(f, "LLM", "dual", "n") for f in FAMS)
    mac("lncells", nruns); mac("lnseeds", g("thr", "LLM", "dual", "n"))
    mac("lcalls", fmt(ps["calls"]))
    mac("lprompts", fmt(sum(1 for _ in open(os.path.join(A.llm, "llm_cache.jsonl")))))
    mac("lreturned", fmt(ps["returned"])); mac("linvalid", ps["invalid"]); mac("ldup", ps["duplicate"])
    for arm, a in (("dual", "d"), ("no_gate", "g")):
        mac(f"lprop{a}", fmt(sum(g(f, "LLM", arm, "prop") for f in FAMS)))
        mac(f"ladm{a}", fmt(sum(g(f, "LLM", arm, "adm") for f in FAMS)))
        mac(f"lharm{a}", fmt(sum(g(f, "LLM", arm, "harm") for f in FAMS)))
        mac(f"lreach{a}", sum(g(f, "LLM", arm, "reach") for f in FAMS))
    rows = []
    for fam in FAMS:
        for lab in ("LLM", "seeded"):
            for arm in ARMS:
                v = out[("mid", fam, lab, arm)]
                armlab = "Dual" if arm == "dual" else "No gate"
                rows.append(f"{NAMES[fam] if (lab, arm) == ('LLM', 'no_gate') else ''} & {lab} & {armlab} & "
                            f"{v['fm']:.1f} & {v['am']:.1f} & {v['ww']:.1f} & {v['harm']} & {v['ex']:.0f}\\\\")
        if fam != FAMS[-1]:
            rows.append("\\midrule")
    open(os.path.join(A.out, "tab_llm.tex"), "w").write("\n".join(rows) + "\n")
    for fam in FAMS:
        for lab, l in (("LLM", "l"), ("seeded", "s")):
            for arm, a in (("dual", "d"), ("no_gate", "g")):
                mac(f"{l}am{fam}{a}", f"{g(fam, lab, arm, 'am'):.1f}")
                mac(f"{l}ww{fam}{a}", f"{g(fam, lab, arm, 'ww'):.1f}")
                mac(f"{l}ex{fam}{a}", f"{g(fam, lab, arm, 'ex'):.0f}")
                mac(f"{l}harm{fam}{a}", g(fam, lab, arm, "harm"))
                fw = [x for x in g(fam, lab, arm, "fw") if x is not None]
                mac(f"{l}fwlo{fam}{a}", min(fw) if fw else "--"); mac(f"{l}fwhi{fam}{a}", max(fw) if fw else "--")
                dn = [x for x in g(fam, lab, arm, "done") if x is not None]
                mac(f"{l}donelo{fam}{a}", min(dn) if dn else "--"); mac(f"{l}donehi{fam}{a}", max(dn) if dn else "--")
    allL = [c for f in FAMS for c in load(A.llm, f, "mid", range(g(f, "LLM", "dual", "n")))]
    mac("loraclemiss", f"{100 * S.mean(c['arms']['oracle']['miss_rate'] for c in allL):.1f}")
    open(os.path.join(A.out, "numbers_llm.tex"), "w").write("\n".join(macros) + "\n")
    print("\n".join(macros))
