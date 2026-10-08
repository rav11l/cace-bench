#!/usr/bin/env python3
"""Compare the language-model proposer with the seeded proposer on the same cells, and write
the paper's numbers.

    python tools/llm_tables.py results/shift-llm results/shift paper/generated

Besides the end-of-stream metrics stored in each cell, it reconstructs every arm's deployed
harness window by window from the admissions in the gate log and counts the flags that were
missed *during* adaptation (the windows between the shift and the evaluation point). The
reconstruction is checked against the error count the engine logged for the same windows.
"""
import glob
import gzip
import json
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import evolve as E  # noqa: E402

LLM, SEEDED, OUT = sys.argv[1:4]
FAMS = ("thr", "scope", "struct")
ARMS = ("no_gate", "dual")


def cells(d, seeds):
    return {f: [json.load(gzip.open(os.path.join(d, f"cell-{f}-mid-seed{s}.json.gz"), "rt"))
                for s in seeds] for f in FAMS}


def adaptation(c, arm):
    fam, seed = c["family"], c["seed"]
    cases = E.generate(seed, fam, "mid", c["n"])
    n = len(cases)
    T, Ev = int(E.T_FRAC * n), int(E.EVAL_FRAC * n)
    v2 = [E.truth(x, fam, "mid", "v2") for x in cases]
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


L = cells(LLM, range(len(glob.glob(os.path.join(LLM, "cell-thr-mid-seed*.json.gz")))))
seeds = range(len(L["thr"]))
R = cells(SEEDED, seeds)
summ = json.load(open(os.path.join(LLM, "summary.json")))
ps = summ["proposer_stats"]

macros = []


def mac(k, v):
    assert k.isalpha(), k
    macros.append(f"\\newcommand{{\\{k}}}{{{v}}}")


def fmt(n):
    return f"{n:,}".replace(",", "{,}")


allL = [c for f in FAMS for c in L[f]]
mac("lncells", len(allL)); mac("lnseeds", len(seeds))
mac("lcalls", fmt(ps["calls"])); mac("lprompts", fmt(sum(1 for _ in open(os.path.join(LLM, "llm_cache.jsonl")))))
mac("lreturned", fmt(ps["returned"])); mac("linvalid", ps["invalid"]); mac("ldup", ps["duplicate"])
for arm, a in (("dual", "d"), ("no_gate", "g")):
    xs = [c["arms"][arm] for c in allL]
    mac(f"lprop{a}", fmt(sum(x["proposed"] for x in xs)))
    mac(f"ladm{a}", fmt(sum(x["admitted"] for x in xs)))
    mac(f"lharm{a}", fmt(sum(x["false_admissions_on_H_val"] for x in xs)))
    mac(f"lreach{a}", sum(x["harness_digest"] == c["arms"]["oracle"]["harness_digest"]
                          for x, c in zip(xs, allL)))

rows, out = [], {}
names = {"thr": "Threshold", "scope": "Scope", "struct": "Structural"}
for fam in FAMS:
    for lab, D in (("LLM", L), ("seeded", R)):
        for arm in ARMS:
            cs = D[fam]
            ad = [adaptation(c, arm) for c in cs]
            am = 100 * sum(a[0] for a in ad) / sum(a[1] for a in ad)
            ww = 100 * max(a[2] for a in ad)
            fm = 100 * S.mean(c["arms"][arm]["miss_rate"] for c in cs)
            harm = sum(c["arms"][arm]["false_admissions_on_H_val"] for c in cs)
            ex = S.mean(c["arms"][arm]["excess_adapt_errors"] for c in cs)
            fw = [c["arms"][arm]["first_admission_window"] for c in cs]
            T0 = int(E.T_FRAC * cs[0]["n"])
            done = []                     # window in which the oracle harness was admitted
            for c in cs:
                o = c["arms"]["oracle"]["harness_digest"]
                ts = [r["t"] for r in c["arms"][arm]["log"] if r["decision"] == "admitted" and r["h_prime"] == o]
                done.append((ts[0] - T0) // E.WINDOW if ts else None)
            out[(fam, lab, arm)] = dict(am=am, ww=ww, fm=fm, harm=harm, ex=ex, fw=fw, done=done)
            armlab = "Dual" if arm == "dual" else "No gate"
            rows.append(f"{names[fam] if (lab, arm) == ('LLM', 'no_gate') else ''} & {lab} & {armlab} & "
                        f"{fm:.1f} & {am:.1f} & {ww:.1f} & {harm} & {ex:.0f}\\\\")
    if fam != FAMS[-1]:
        rows.append("\\midrule")
open(os.path.join(OUT, "tab_llm.tex"), "w").write("\n".join(rows) + "\n")

g = lambda fam, lab, arm, k: out[(fam, lab, arm)][k]
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
mac("loraclemiss", f"{100 * S.mean(c['arms']['oracle']['miss_rate'] for c in allL):.1f}")
open(os.path.join(OUT, "numbers_llm.tex"), "w").write("\n".join(macros) + "\n")

md = ["| Family | Proposer | Arm | Final miss % | Miss during adaptation % | Worst window % | Harmful adm. | Excess errors |",
      "|---|---|---|---|---|---|---|---|"]
for (fam, lab, arm), v in out.items():
    md.append(f"| {fam} | {lab} | {arm} | {v['fm']:.1f} | {v['am']:.1f} | {v['ww']:.1f} | {v['harm']} | {v['ex']:.0f} |")
md.append(f"\nProposer: {summ['proposer']}; stats: {ps}")
open(os.path.join(LLM, "tables.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md)); print("\n".join(macros))
