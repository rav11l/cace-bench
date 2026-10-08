#!/usr/bin/env python3
"""Generate paper/generated/numbers_real.tex and tab_real.tex from the real-applicant runs.

    python tools/paper_numbers_real.py results/shift-real results/shift-real-eps010 \
        results/shift-real-n1000 paper/generated
"""
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN, EPS, N1000, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)


def load(d):
    return [json.load(gzip.open(f, "rt")) for f in sorted(glob.glob(os.path.join(d, "cell-*.json.gz")))]


cells, eps_cells, small = load(MAIN), load(EPS), load(N1000)
macros = []


def mac(name, val):
    assert name.isalpha(), name
    macros.append(f"\\newcommand{{\\{name}}}{{{val}}}")


def pp(x, nd=1):
    return f"{x * 100:.{nd}f}"


def gate(cs, arm):
    return (sum(c["arms"][arm]["proposed"] for c in cs), sum(c["arms"][arm]["admitted"] for c in cs),
            sum(c["arms"][arm]["false_admissions_on_H_val"] for c in cs),
            sum(c["arms"][arm]["miss_rate"] > 0.10 for c in cs))


def fmt(n):
    return f"{n:,}".replace(",", "{,}")


mac("rncells", len(cells))
for tag, cs in (("", cells), ("s", small)):
    for arm, a in (("dual", "d"), ("no_gate", "g")):
        p, ad, h, m = gate(cs, arm)
        nm = {"": "", "s": "small"}[tag]
        mac(f"r{nm}prop{a}", fmt(p))
        mac(f"r{nm}adm{a}", fmt(ad))
        mac(f"r{nm}harm{a}", fmt(h))
        mac(f"r{nm}mten{a}", fmt(m))


def reached(cs, pred=lambda c: True):
    xs = [c for c in cs if pred(c)]
    return sum(c["arms"]["dual"]["harness_digest"] == c["arms"]["oracle"]["harness_digest"] for c in xs), len(xs)


sh = lambda c: c["family"] == "scope" and c["severity"] == "high"
k, n = reached(cells, lambda c: not sh(c))
mac("rreachedother", k); mac("rnother", n)
k, n = reached(cells, sh)
mac("rreachedsh", k); mac("rnsh", n)
k, n = reached(eps_cells, sh)
mac("repsreachedsh", k)
mac("repsharm", sum(c["arms"]["dual"]["false_admissions_on_H_val"] for c in eps_cells))
k, n = reached(small)
mac("rsmallreached", k); mac("rsmalln", n)

# the regression clause that blocks the correct scope change in scope-high
regs = []
for c in cells:
    if not sh(c):
        continue
    for rec in c["arms"]["dual"]["log"]:
        if "household_goods" in rec["diff"] and rec["decision"] == "regression_on_C":
            regs.append(rec["H_sel"]["C_regression_rate"])
mac("rshreglo", pp(min(regs), 2)); mac("rshreghi", pp(max(regs), 2))

# applicant shares
appl = {"household": 0}
import evolve_real  # noqa: E402
A = evolve_real.applicants()
mac("rhouseholdshare", f"{100 * sum(a['purpose'] == 'household_goods' for a in A) / len(A):.0f}")
mac("rfemale", sum(a["female"] for a in A)); mac("ryoung", sum(a["young"] for a in A))


# excess subgroup gap over the oracle's own gap, per run
def excess(cs, arm, pair, metric):
    xs = []
    for c in cs:
        s, o = c["arms"][arm]["subgroups"], c["arms"]["oracle"]["subgroups"]
        xs.append((s[pair[0]][metric]["rate"] - s[pair[1]][metric]["rate"])
                  - (o[pair[0]][metric]["rate"] - o[pair[1]][metric]["rate"]))
    return xs


rows = []
other = [c for c in cells if not sh(c)]
shc = [c for c in cells if sh(c)]
for arm, lab in (("dual", "Dual"), ("no_gate", "No gate")):
    for cs, cl in ((other, f"other ({len(other)})"), (shc, f"scope-high ({len(shc)})")):
        cellsx = []
        for pair in (("female", "male"), ("under25", "25plus")):
            for metric in ("fp", "miss"):
                xs = excess(cs, arm, pair, metric)
                mean = sum(xs) / len(xs)
                mx = max(abs(x) for x in xs)
                cellsx.append(f"{mean * 100:+.1f} ({mx * 100:.1f})")
        rows.append(f"{lab}, {cl} & " + " & ".join(cellsx) + r" \\")
open(os.path.join(OUT, "tab_real.tex"), "w").write("\n".join(rows) + "\n")

xs = excess(shc, "dual", ("female", "male"), "fp")
mac("rshfemfpmean", pp(sum(xs) / len(xs))); mac("rshfemfpmax", pp(max(abs(x) for x in xs)))
xs = excess(shc, "dual", ("under25", "25plus"), "fp")
mac("rshyoungfpmean", pp(sum(xs) / len(xs))); mac("rshyoungfpmax", pp(max(abs(x) for x in xs)))
xs = excess(cells, "no_gate", ("female", "male"), "miss")
mac("rngfemmissmax", pp(max(abs(x) for x in xs)))
xs = excess(cells, "no_gate", ("under25", "25plus"), "miss")
mac("rngyoungmissmax", pp(max(abs(x) for x in xs)))

# realised outcome among flagged / cleared, oracle harness, pooled
fk = sum(c["arms"]["oracle"]["bad_rate_flagged"]["k"] for c in cells)
fn = sum(c["arms"]["oracle"]["bad_rate_flagged"]["n"] for c in cells)
ck = sum(c["arms"]["oracle"]["bad_rate_cleared"]["k"] for c in cells)
cn = sum(c["arms"]["oracle"]["bad_rate_cleared"]["n"] for c in cells)
mac("rbadflagged", pp(fk / fn)); mac("rbadcleared", pp(ck / cn))

open(os.path.join(OUT, "numbers_real.tex"), "w").write("\n".join(macros) + "\n")
print("\n".join(macros))
print(open(os.path.join(OUT, "tab_real.tex")).read())
