"""Reproduce scope seed 4 gate decisions offline; no model calls or gate changes."""
import gzip
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
import evolve as E

cases = E.generate(4, "scope", "mid")
pool = [c for c in cases[:int(E.T_FRAC * len(cases))] if c.idx % 2 == 0]
labels = [E.truth(c, "scope", "mid", "v2") for c in pool]
initial = E.H0
oracle = E.oracle_harness("scope", "mid")
intermediate = E.Harness(initial.primitive, initial.theta,
                         initial.scope - frozenset(["adverse_media_low"]))

def check(before, after):
    decision, stats = E.gate_decision(before, after, "fp", pool, labels)
    return {"diff": E.diff(before, after), "decision": decision, **stats}

direct = check(initial, oracle)
step1 = check(initial, intermediate)
step2 = check(intermediate, oracle)
assert direct["decision"] == "regression_on_C"
assert step1["decision"] == step2["decision"] == "admitted"
assert direct["C_regressed"] == 37
with gzip.open(ROOT / "results/combined/cell-scope-mid-seed4.json.gz", "rt") as f:
    sol = json.load(f)["arms"]["dual"]
oracle_rejections = [r for r in sol["log"] if r["h_prime"] == oracle.digest()]
assert len(oracle_rejections) == 9
assert all(r["decision"] == direct["decision"] for r in oracle_rejections)
with gzip.open(SOURCE / "results/shift-llm/cell-scope-mid-seed4.json.gz", "rt") as f:
    haiku = json.load(f)["arms"]["dual"]
accepted = [r for r in haiku["log"] if r["decision"] == "admitted"]
assert [r["h_prime"] for r in accepted] == [intermediate.digest(), oracle.digest()]
report = {
    "scenario": "scope/mid/seed4", "epsilon_unchanged": E.EPS,
    "method": "Offline regeneration of original selection pool and gate; no LLM calls",
    "direct_to_oracle": direct, "sequential_step_1": step1,
    "sequential_step_2": step2, "sol_oracle_proposals_rejected": len(oracle_rejections),
    "sol_final_fp_rate": sol["fp_rate"],
    "finding": "Gate is path-dependent: the same final harness is rejected directly and admitted through two steps. C is recomputed relative to the current harness.",
    "interpretation": "Failure to reach the oracle is not failure to propose it. Execution noise and per-step regression limits contribute. Sequential admission is not a cumulative regression guarantee.",
    "next_experiment": "Pre-register atomic proposal and fixed-baseline cumulative regression variants; evaluate separately on held-out data without changing this pilot's results.",
    "limitations": "Synthetic mid-severity pilot; unpinned Codex model, not raw API; output token cap not enforced. This diagnoses CACE-Bench, not a deployed Cauce LLM integration."
}
output = ROOT / "results/scope-seed4-diagnosis.json"
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
