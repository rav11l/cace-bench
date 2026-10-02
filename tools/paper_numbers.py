#!/usr/bin/env python3
"""Generate paper/generated/*.tex from the result files, so that every number in the
paper is read from a run output and none is typed by hand.

    python tools/paper_numbers.py results/shift results/shift-eps010 results paper/generated
"""
import glob
import gzip
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evolve import mean_ci  # noqa: E402

SHIFT, EPSDIR, REF, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
cells = [json.load(gzip.open(f, "rt")) for f in sorted(glob.glob(os.path.join(SHIFT, "cell-*.json.gz")))]
eps_cells = [json.load(gzip.open(f, "rt")) for f in sorted(glob.glob(os.path.join(EPSDIR, "cell-*.json.gz")))]
FAM = ["thr", "scope", "struct"]
SEV = ["low", "mid", "high"]
FAMNAME = {"thr": "Thr", "scope": "Scope", "struct": "Struct"}
ARMLABEL = {
    "healthy": "Healthy (no shift)", "degraded": "Degraded (no adaptation)",
    "oracle": "Oracle update", "manual": "Manual update (lag 2{,}000)",
    "no_gate": "No gate (trace check only)", "stale_gate": "Gate on stale labels",
    "global_only": "Global loop only", "local_only": "Local loop only",
    "local_only_cm": "Local only, compute-matched", "dual": "Dual loop (gated)",
}
macros = []


def mac(name, val):
    macros.append(f"\\newcommand{{\\{name}}}{{{val}}}")


def p1(x):
    return f"{x*100:.1f}"


def ci_str(xs, scale=100, nd=1, clip=True):
    m, (lo, hi) = mean_ci(xs)
    if clip:
        lo, hi = max(lo, 0.0), min(hi, 1.0 if scale == 100 else hi)
    return f"{m*scale:.{nd}f}", f"[{lo*scale:.{nd}f}, {hi*scale:.{nd}f}]"


def recovery_window(a, o):
    w, ow = a["window_err"], o["window_err"]
    for i in range(len(w)):
        if all(w[j] <= ow[j] + 0.01 for j in range(i, len(w))):
            return i
    return len(w)


# ---------------------------------------------------------- main table (mid) ---
arms_main = ["healthy", "degraded", "oracle", "manual", "no_gate", "stale_gate",
             "global_only", "local_only", "local_only_cm", "dual"]
rows = []
for fam in FAM:
    sub = [c for c in cells if c["family"] == fam and c["severity"] == "mid"]
    rows.append(f"\\multicolumn{{7}}{{l}}{{\\textit{{{FAMNAME[fam]} shift, mid severity, "
                f"{len(sub)} seeds}}}}\\\\")
    for arm in arms_main:
        xs = [c["arms"][arm] for c in sub]
        fpm, fpci = ci_str([x["fp_rate"] for x in xs])
        mim, mici = ci_str([x["miss_rate"] for x in xs])
        if arm == "no_gate":
            lo, hi = min(x["miss_rate"] for x in xs), max(x["miss_rate"] for x in xs)
            mici = f"\\{{{lo*100:.1f}--{hi*100:.1f}\\}}"
        rgm, _ = ci_str([x["regression_rate"] for x in xs])
        if arm == "healthy":
            ex, rw = "--", "--"
        else:
            ex = f"{statistics.fmean(x['excess_adapt_errors'] for x in xs):.0f}"
            rws = [recovery_window(c["arms"][arm], c["arms"]["oracle"]) for c in sub]
            rw = f"{statistics.fmean(rws):.1f}"
        prop = sum(x["proposed"] for x in xs)
        adm = sum(x["admitted"] for x in xs)
        fa = sum(x["false_admissions_on_H_val"] for x in xs)
        gate_cols = f"{prop} / {adm} / {fa}" if prop else "--"
        rows.append(f"{ARMLABEL[arm]} & {fpm} {{\\scriptsize {fpci}}} & {mim} {{\\scriptsize {mici}}} "
                    f"& {rgm} & {ex} & {rw} & {gate_cols}\\\\")
        key = f"{fam}{arm.replace('_', '')}"
        mac(f"fp{key}", fpm)
        mac(f"miss{key}", mim)
        mac(f"ex{key}", ex)
    rows.append("\\midrule")
rows = rows[:-1]
open(os.path.join(OUT, "tab_main.tex"), "w").write("\n".join(rows) + "\n")

# ------------------------------------------------------------- full grid -------
grid_arms = ["degraded", "no_gate", "global_only", "local_only", "dual", "oracle"]
g = []
for fam in FAM:
    for sev in SEV:
        sub = [c for c in cells if c["family"] == fam and c["severity"] == sev]
        cols = []
        for arm in grid_arms:
            fp = statistics.fmean(c["arms"][arm]["fp_rate"] for c in sub)
            mi = statistics.fmean(c["arms"][arm]["miss_rate"] for c in sub)
            cols.append(f"{p1(fp)} / {p1(mi)}")
        nclr = statistics.fmean(c["arms"]["dual"]["fp"] + c["arms"]["dual"]["tn"] for c in sub)
        nflg = statistics.fmean(c["arms"]["dual"]["tp"] + c["arms"]["dual"]["fn"] for c in sub)
        g.append(f"{FAMNAME[fam]} & {sev} & {nclr:,.0f} / {nflg:,.0f} & ".replace(",", "{,}")
                 + " & ".join(cols) + "\\\\")
    g.append("\\midrule")
open(os.path.join(OUT, "tab_grid.tex"), "w").write("\n".join(g[:-1]) + "\n")

# ------------------------------------------------------ gate statistics --------
gs = []
for arm in ["dual", "local_only", "global_only", "stale_gate", "no_gate"]:
    xs = [c["arms"][arm] for c in cells]
    rej = {}
    for x in xs:
        for k, v in x["rejected"].items():
            rej[k] = rej.get(k, 0) + v
    prop = sum(x["proposed"] for x in xs)
    adm = sum(x["admitted"] for x in xs)
    fa = sum(x["false_admissions_on_H_val"] for x in xs)
    orj = sum(x.get("oracle_candidate_rejected", 0) for x in xs)
    m10 = sum(x["miss_rate"] > 0.10 for x in xs)
    mx = max(x["admitted"] for x in xs)
    ok = all(x["log_ok"] for x in xs)
    if arm == "no_gate":
        r1, r2 = f"{rej.get('no_trace_improvement', 0)}$^\\dagger$", "--"
    else:
        r1, r2 = rej.get("no_significant_improvement", 0), rej.get("regression_on_C", 0)
    gs.append(f"{ARMLABEL[arm]} & {prop} & {adm} & {r1} & {r2} & {fa} & {orj} & {m10} & {mx}\\\\")
    k = arm.replace("_", "")
    for n, v in [("prop", prop), ("adm", adm), ("fa", fa), ("orj", orj), ("mten", m10),
                 ("maxadm", mx), ("rejns", rej.get("no_significant_improvement", 0)),
                 ("rejreg", rej.get("regression_on_C", 0)),
                 ("rejtrace", rej.get("no_trace_improvement", 0)),
                 ("esc", sum(x["escalations"] for x in xs))]:
        mac(f"g{n}{k}", f"{v:,}".replace(",", "{,}"))
    mac(f"glogs{k}", "all verified" if ok else "FAILED")
open(os.path.join(OUT, "tab_gate.tex"), "w").write("\n".join(gs) + "\n")
for fam in FAM:
    for arm in ("local_only", "global_only"):
        xs = [c["arms"][arm] for c in cells if c["family"] == fam]
        k = arm.replace("_", "")
        mac(f"fam{fam}{k}prop", f"{sum(x['proposed'] for x in xs):,}".replace(",", "{,}"))
        mac(f"fam{fam}{k}reg", f"{sum(x['rejected'].get('regression_on_C', 0) for x in xs):,}".replace(",", "{,}"))
        mac(f"fam{fam}{k}adm", sum(x["admitted"] for x in xs))
def cellmean(fam, sev, arm, key):
    sub = [c for c in cells if c["family"] == fam and c["severity"] == sev]
    return statistics.fmean(c["arms"][arm][key] for c in sub)
for fam in FAM:
    for sev in SEV:
        for arm in ("dual", "manual", "global_only", "local_only"):
            mac(f"exc{fam}{sev}{arm.replace('_', '')}", f"{cellmean(fam, sev, arm, 'excess_adapt_errors'):.0f}")
lo_scope_mid = [c for c in cells if c["family"] == "scope" and c["severity"] == "mid"]
mac("loScopeMidRecovered", f"{sum(c['arms']['local_only']['harness_digest'] == c['arms']['oracle']['harness_digest'] for c in lo_scope_mid)}/{len(lo_scope_mid)}")
cm = [c["arms"]["local_only_cm"] for c in cells]
mac("cmScaleMin", min(x["budget_scale"] for x in cm))
mac("cmScaleMax", max(x["budget_scale"] for x in cm))
mac("gpropcm", f"{sum(x['proposed'] for x in cm):,}".replace(",", "{,}"))
mac("gadmcm", sum(x["admitted"] for x in cm))
both_fail = sum(1 for c in cells for r in c["arms"]["stale_gate"]["log"]
                if r["H_sel"] and not r["H_sel"]["improvement_ok"] and not r["H_sel"]["regression_ok"])
mac("staleBothFail", f"{both_fail:,}".replace(",", "{,}"))
mac("nlogs", sum(1 for c in cells for a in c["arms"].values() if a["log"]))
mac("nlogsok", sum(1 for c in cells for a in c["arms"].values() if a["log"] and a["log_ok"]))
mac("nrecords", f"{sum(len(a['log']) for c in cells for a in c['arms'].values()):,}".replace(",", "{,}"))
sizes = [a["harness_size"] for c in cells for a in c["arms"].values()]
mac("hsizemin", min(sizes)); mac("hsizemax", max(sizes))
mac("ncells", len(cells))
mac("nseeds", len({c["seed"] for c in cells}))

# ------------------------------------------------------ eps sensitivity -------
es = []
for sev in SEV:
    a = [c for c in cells if c["family"] == "struct" and c["severity"] == sev]
    b = [c for c in eps_cells if c["family"] == "struct" and c["severity"] == sev]
    for lab, sub in [("0.005", a), ("0.010", b)]:
        d = [c["arms"]["dual"] for c in sub]
        fpm, fpci = ci_str([x["fp_rate"] for x in d])
        mim, mici = ci_str([x["miss_rate"] for x in d])
        rec = sum(c["arms"]["dual"]["harness_digest"] == c["arms"]["oracle"]["harness_digest"]
                  for c in sub)
        orj = sum(x.get("oracle_candidate_rejected", 0) for x in d)
        fa = sum(x["false_admissions_on_H_val"] for x in d)
        es.append(f"{sev} & {lab} & {fpm} {{\\scriptsize {fpci}}} & {mim} {{\\scriptsize {mici}}} "
                  f"& {rec}/{len(sub)} & {orj} & {fa}\\\\")
        tag = {"0.005": "A", "0.010": "B"}[lab]
        mac(f"epsrec{sev}{tag}", f"{rec}/{len(sub)}")
        mac(f"epsfp{sev}{tag}", fpm)
        mac(f"epsorj{sev}{tag}", orj)
open(os.path.join(OUT, "tab_eps.tex"), "w").write("\n".join(es) + "\n")

# ------------------------------------------------- worked rejection ----------
c0 = next(c for c in cells if c["family"] == "struct" and c["severity"] == "mid" and c["seed"] == 0)
log = c0["arms"]["dual"]["log"]
rj = next(r for r in log if r["decision"] == "regression_on_C")
ad = next(r for r in log if r["decision"] == "admitted")
H = rj["H_sel"]
mac("wrT", rj["t"])
mac("wrDiff", rj["diff"].replace("->", "$\\rightarrow$").replace("_", "\\_"))
mac("wrImproved", H["improved"])
mac("wrWorsened", H["worsened"])
mac("wrNtarget", f"{H['n_target']:,}".replace(",", "{,}"))
mac("wrGain", f"{H['gain']*100:.1f}")
mac("wrGainLo", f"{H['gain_ci'][0]*100:.1f}")
mac("wrGainHi", f"{H['gain_ci'][1]*100:.1f}")
mac("wrC", f"{H['C_size']:,}".replace(",", "{,}"))
mac("wrCreg", H["C_regressed"])
mac("wrCrate", f"{H['C_regression_rate']*100:.1f}")
mac("wrHash", rj["hash"][:12])
mac("wrPrev", rj["prev"][:12])
mac("wrSeq", rj["seq"])
nrej_before = sum(1 for r in log if r["seq"] < ad["seq"] and r["decision"] != "admitted")
mac("wrRejBefore", nrej_before)
Ha = ad["H_sel"]
before = [r for r in log if r["seq"] < ad["seq"]]
n_local_rej = sum(1 for r in before if r["loop"] == "local")
glob_rej = [r for r in before if r["loop"] == "global"]
mac("wrLocalRej", n_local_rej)
mac("wrGlobalRej", len(glob_rej))
mac("wrGlobalRejList", ", ".join(r["diff"].split("theta ")[-1].split(" -> ")[-1] for r in glob_rej
                                 if "theta" in r["diff"]) or "--")
mac("waT", ad["t"])
mac("waLoop", ad["loop"])
mac("waDiff", ad["diff"].replace("->", "$\\rightarrow$").replace("_", "\\_"))
mac("waGain", f"{Ha['gain']*100:.1f}")
mac("waGainLo", f"{Ha['gain_ci'][0]*100:.1f}")
mac("waCreg", Ha["C_regressed"])
mac("waCrate", f"{Ha['C_regression_rate']*100:.2f}")
mac("waSeq", ad["seq"])
mac("nlogrec", len(log))
json.dump({"rejected": rj, "admitted": ad}, open(os.path.join(OUT, "worked_example.json"), "w"),
          indent=1)

# ------------------------------------------------- reference run (5 seeds) ---
runs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(REF, "run-seed[0-9].json")))]
r0 = next(r for r in runs if r["seed"] == 0)
ref = []
spec = [("Silent decision", "silent_decision", "silent", "n_undecidable"),
        ("Compliance FP", "compliance_fp", "fp", "n_clear"),
        ("Missed flag", "compliance_miss", "miss", "n_flag"),
        ("Hallucination", "hallucination", "hall", "n"),
        ("Provenance compl.", "provenance", "prov", "n")]
for lab, dk, ak, nk in spec:
    off, on = r0["arms"]["off"], r0["arms"]["on"]
    ci_off, ci_on = off[f"{ak}_ci"], on[f"{ak}_ci"]
    offs = [r["deltas"][dk]["off"] for r in runs]
    ons = [r["deltas"][dk]["on"] for r in runs]
    ref.append(f"{lab} & {p1(off[f'{ak}_rate'])} {{\\scriptsize [{p1(ci_off[0])}, {p1(ci_off[1])}]}} "
               f"& {p1(on[f'{ak}_rate'])} {{\\scriptsize [{p1(ci_on[0])}, {p1(ci_on[1])}]}} "
               f"& {off[nk]:,} & {p1(min(offs))}--{p1(max(offs))} & {p1(min(ons))}--{p1(max(ons))}\\\\"
               .replace(",", "{,}"))
    mac(f"ref{ak}off", p1(off[f"{ak}_rate"]))
    mac(f"ref{ak}on", p1(on[f"{ak}_rate"]))
    mac(f"ref{ak}offlo", p1(min(offs)))
    mac(f"ref{ak}offhi", p1(max(offs)))
    mac(f"ref{ak}onlo", p1(min(ons)))
    mac(f"ref{ak}onhi", p1(max(ons)))
open(os.path.join(OUT, "tab_ref.tex"), "w").write("\n".join(ref) + "\n")
mac("refundec", p1(r0["arms"]["off"]["n_undecidable"] / r0["n"]))
mac("refundeclo", p1(min(r["arms"]["off"]["n_undecidable"] / r["n"] for r in runs)))
mac("refundechi", p1(max(r["arms"]["off"]["n_undecidable"] / r["n"] for r in runs)))
mac("refnseeds", len(runs))
mac("refrecovery", p1(r0["recovery_rate"]))

open(os.path.join(OUT, "numbers.tex"), "w").write("\n".join(macros) + "\n")
print(f"{len(macros)} macros, {len(cells)} cells, {len(eps_cells)} eps cells, {len(runs)} reference runs")
