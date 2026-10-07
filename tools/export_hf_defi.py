#!/usr/bin/env python3
"""export_hf_defi.py — build the DeFi configs of the Hugging Face dataset anonymous/bench.

Two files, written to --out (outside git; upload them to the dataset repo's defi/ folder).
They go into two configs, `defi` (split `synthetic`) and `defi_historical` (split
`historical`), because a config's splits must share one schema:

  synthetic   one row per generated DeFi case (seed 0, N=23,000 by default), with the
              reference agent's first pass and post-recovery narrative and the unchanged
              judge's verdict on each — the same columns as the credit config, renamed
              where the DeFi reading differs (country -> chain, sanctions_hit -> gate_fail …).
  historical  one row per entry of data/defi_historical_v0.json (cases, unscored
              controls and prospective slots), with facts, sources and evidence capsules
              kept as JSON strings. Prospective rows carry no label until revealed.

The script re-aggregates the judge rows it writes and checks them against run_defi(),
so the exported split reproduces the figures `python defi_track.py` prints.

    python tools/export_hf_defi.py                       # jsonl, stdlib only
    python tools/export_hf_defi.py --format parquet      # needs pyarrow
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from bench import aggregate, judge  # noqa: E402
from defi_track import (DEFAULT_PARAMS, __version__, first_pass_defi,  # noqa: E402
                        generate_defi, recover_defi, run_defi)

VERDICT = {"flag": "NO-GO", "clear": "GO", "escalate": "INSUFFICIENT_DATA"}


def _nar(n) -> str:
    d = dataclasses.asdict(n)
    d["verdict"] = VERDICT.get(d["outcome"], d["outcome"])
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def _sources(case) -> str:
    return json.dumps({k: dataclasses.asdict(v) for k, v in case.sources.items()},
                      ensure_ascii=False, sort_keys=True)


def synthetic_rows(n: int, seed: int, registry: dict):
    rows, ev_off, ev_on = [], [], []
    for c in generate_defi(n, seed, registry):
        a = first_pass_defi(c, DEFAULT_PARAMS, seed)
        b = recover_defi(a, c, DEFAULT_PARAMS, seed)
        ja, jb = judge(c, a), judge(c, b)
        ev_off.append(ja)
        ev_on.append(jb)
        rows.append({
            "id": c.id, "chain": c.country, "access": list(c.consent), "sources": _sources(c),
            "gate_fail": c.sanctions_hit, "concentration_breach": c.pep_match,
            "anomaly_alert": c.aml_alert, "controls_safe": c.kyc_verified,
            "difficulty": c.difficulty, "truth": c.truth, "truth_verdict": VERDICT[c.truth],
            "decidable": c.decidable,
            "ref_first_pass": _nar(a), "ref_after_recovery": _nar(b),
            "judge_first_pass": json.dumps(ja, sort_keys=True),
            "judge_after_recovery": json.dumps(jb, sort_keys=True),
        })
    return rows, aggregate(ev_off), aggregate(ev_on)


def historical_rows(path: str):
    doc = json.load(open(path, encoding="utf-8"))
    rows = []
    for h in doc["cases"]:
        realized = h.get("realized") or {}
        status = h.get("status", "")
        rows.append({
            "id": h["id"], "name": h.get("name"), "chain": h.get("chain"),
            "t0": h.get("t0"), "t0_block": h.get("t0_block"), "status": status,
            "scored": bool(h.get("scored", True)),
            "split_role": ("prospective" if status == "prospective"
                           else "control" if status == "control" else "historical"),
            "position": h.get("position"),
            "rule_truth": h.get("rule_truth"),
            "rule_verdict": VERDICT.get(h.get("rule_truth") or "", None),
            "realized_loss": realized.get("loss"),
            "realized_summary": realized.get("summary"),
            "read_on_chain": (h.get("display") or {}).get("read_on_chain"),
            "facts": json.dumps(h.get("facts"), ensure_ascii=False, sort_keys=True),
            "sources": json.dumps(h.get("sources"), ensure_ascii=False, sort_keys=True),
            "record": json.dumps(h, ensure_ascii=False, sort_keys=True),
        })
    return rows


def _write(rows, path_noext: str, fmt: str) -> str:
    if fmt == "parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq
        path = path_noext + ".parquet"
        pq.write_table(pa.Table.from_pylist(rows), path)
    else:
        path = path_noext + ".jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=23000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sources", default=os.path.join(ROOT, "configs", "defi_sources.json"))
    ap.add_argument("--historical", default=os.path.join(ROOT, "data", "defi_historical_v0.json"))
    ap.add_argument("--format", choices=["jsonl", "parquet"], default="jsonl")
    ap.add_argument("--out", default="hf_export/defi")
    a = ap.parse_args()
    if os.path.abspath(a.out).startswith(os.path.abspath(ROOT) + os.sep):
        print("note: --out is inside the repository; do not commit the exported data")
    os.makedirs(a.out, exist_ok=True)
    reg = json.load(open(a.sources, encoding="utf-8"))

    rows, off, on = synthetic_rows(a.n, a.seed, reg)
    ref = run_defi(a.n, a.seed, DEFAULT_PARAMS, reg)["arms"]
    for arm, mine in (("off", off), ("on", on)):
        for k in ("silent_rate", "fp_rate", "hall_rate", "over_rate", "prov_rate", "step_correct"):
            if abs(mine[k] - ref[arm][k]) > 1e-12:
                sys.exit(f"export does not reproduce run_defi: {arm}.{k} {mine[k]} != {ref[arm][k]}")
    syn = _write(rows, os.path.join(a.out, f"synthetic-seed{a.seed}-n{a.n}"), a.format)
    hist_rows = historical_rows(a.historical)
    his = _write(hist_rows, os.path.join(a.out, "historical-v0"), a.format)

    manifest = {"track": "defi", "track_version": __version__, "seed": a.seed, "n": a.n,
                "sources_version": reg.get("version"),
                "files": {os.path.basename(syn): _sha(syn), os.path.basename(his): _sha(his)},
                "historical_rows": len(hist_rows),
                "historical_by_role": {r: sum(x["split_role"] == r for x in hist_rows)
                                       for r in ("historical", "control", "prospective")},
                "metrics_off_on": {k: [off[k], on[k]] for k in
                                   ("silent_rate", "fp_rate", "hall_rate", "over_rate", "prov_rate",
                                    "step_correct")},
                "undecidable_share": off["n_undecidable"] / off["n"]}
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8"), indent=1)
    print(f"synthetic : {syn}  ({len(rows)} rows)  matches run_defi: yes")
    print(f"historical: {his}  ({len(hist_rows)} rows: {manifest['historical_by_role']})")
    print(f"silent-decision {off['silent_rate']:.2%} -> {on['silent_rate']:.2%}; "
          f"undecidable {manifest['undecidable_share']:.2%}")


if __name__ == "__main__":
    main()
