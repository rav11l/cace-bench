#!/usr/bin/env python3
"""prereg.py — commit-reveal pre-registration for the prospective DeFi split.

At T0 an agent's verdict, its evidence capsules and the facts it saw are written to a
PRIVATE record; only the record's SHA-256 (plus a random salt kept inside the record)
is published in ``data/prospective/ledger.jsonl``. Nobody — including the author — can
change the verdict after the fact without breaking the hash, and the verdict itself
stays private until the horizon has passed. This lets a third party's agent be
pre-registered without disclosing its output or its client's position.

    # T0: register a verdict (record stays private, commitment goes to the ledger)
    python prereg.py commit --id P01 --chain ethereum --t0 2026-09-30 --horizon 90 \
        --model "<model id>" --model-cutoff 2026-06-30 \
        --verdict verdict.json --facts facts.json --private-dir ~/cace-private

    # any time: check that a private record still matches its commitment
    python prereg.py verify --record ~/cace-private/P01.json

    # after T0 + horizon: publish the record and the realised outcome
    python prereg.py reveal --record ~/cace-private/P01.json --loss false \
        --summary "no impairment; withdrawals served" --evidence-url https://...

The ledger commit itself should be pushed the same day (git history is the timestamp);
optionally also post the hash publicly (e.g. the lab's Telegram channel) for a second,
independent timestamp.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import secrets
import sys

LEDGER = "data/prospective/ledger.jsonl"
REVEALED = "data/prospective/revealed"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "commitment"}
    return hashlib.sha256(canonical(body)).hexdigest()


def _ledger() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    return [json.loads(x) for x in open(LEDGER, encoding="utf-8") if x.strip()]


def commit(a) -> None:
    if any(e["id"] == a.id for e in _ledger()):
        sys.exit(f"{a.id} is already committed; use a new id")
    verdict = json.load(open(a.verdict, encoding="utf-8"))
    facts = json.load(open(a.facts, encoding="utf-8")) if a.facts else None
    if str(verdict.get("verdict", "")).upper().replace(" ", "_") not in (
            "GO", "NO-GO", "NO_GO", "INSUFFICIENT_DATA"):
        sys.exit("verdict.json must contain verdict: GO | NO-GO | INSUFFICIENT_DATA")
    t0 = _dt.date.fromisoformat(a.t0)
    record = {
        "id": a.id, "chain": a.chain, "t0": a.t0, "t0_block": a.t0_block,
        "horizon_days": a.horizon, "resolves_on": (t0 + _dt.timedelta(days=a.horizon)).isoformat(),
        "model": a.model, "model_cutoff": a.model_cutoff,
        "verdict": verdict, "facts_at_t0": facts,
        "salt": secrets.token_hex(16),
        "committed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    record["commitment"] = digest(record)
    os.makedirs(os.path.expanduser(a.private_dir), exist_ok=True)
    path = os.path.join(os.path.expanduser(a.private_dir), f"{a.id}.json")
    json.dump(record, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    entry = {"id": a.id, "chain": a.chain, "t0": a.t0, "horizon_days": a.horizon,
             "resolves_on": record["resolves_on"], "model_cutoff": a.model_cutoff,
             "sha256": record["commitment"], "committed_at": record["committed_at"]}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"private record : {path}   (do NOT commit this file)")
    print(f"ledger entry   : {LEDGER}")
    print(f"sha256         : {record['commitment']}")


def verify(a) -> None:
    rec = json.load(open(os.path.expanduser(a.record), encoding="utf-8"))
    ok_self = digest(rec) == rec["commitment"]
    led = {e["id"]: e for e in _ledger()}
    ok_ledger = rec["id"] in led and led[rec["id"]]["sha256"] == rec["commitment"]
    print(f"{rec['id']}: record hash {'OK' if ok_self else 'MISMATCH'}, "
          f"ledger {'OK' if ok_ledger else 'MISSING/MISMATCH'}")
    if not (ok_self and ok_ledger):
        sys.exit(1)


def reveal(a) -> None:
    rec = json.load(open(os.path.expanduser(a.record), encoding="utf-8"))
    if digest(rec) != rec["commitment"]:
        sys.exit("record does not match its commitment — refusing to reveal")
    today = _dt.date.today().isoformat()
    if today < rec["resolves_on"] and not a.early:
        sys.exit(f"horizon not reached: resolves on {rec['resolves_on']}")
    os.makedirs(REVEALED, exist_ok=True)
    out = {"record": rec, "realized": {"loss": a.loss == "true", "summary": a.summary,
                                       "evidence_url": a.evidence_url, "revealed_on": today,
                                       "early": bool(a.early)}}
    path = os.path.join(REVEALED, f"{rec['id']}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"revealed -> {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="commit-reveal pre-registration")
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("commit")
    c.add_argument("--id", required=True)
    c.add_argument("--chain", required=True)
    c.add_argument("--t0", required=True)
    c.add_argument("--t0-block", type=int)
    c.add_argument("--horizon", type=int, required=True)
    c.add_argument("--model", required=True)
    c.add_argument("--model-cutoff", required=True)
    c.add_argument("--verdict", required=True)
    c.add_argument("--facts")
    c.add_argument("--private-dir", required=True)
    v = sp.add_parser("verify")
    v.add_argument("--record", required=True)
    r = sp.add_parser("reveal")
    r.add_argument("--record", required=True)
    r.add_argument("--loss", choices=["true", "false"], required=True)
    r.add_argument("--summary", required=True)
    r.add_argument("--evidence-url")
    r.add_argument("--early", action="store_true", help="reveal before horizon (flagged)")
    a = ap.parse_args()
    {"commit": commit, "verify": verify, "reveal": reveal}[a.cmd](a)


if __name__ == "__main__":
    main()
