#!/usr/bin/env python3
"""
CACE-Bench · real-dataset downloader (OPTIONAL module)
======================================================
Fetches public *real* credit datasets used as external INPUTS for a real-data
baseline alongside the fully-synthetic CACE-Bench core. This module is optional:
the synthetic benchmark (see ../cace_bench.py) needs no external data. Run this on
a machine WITH network access.

  pip install -r requirements.txt
  # For the Kaggle datasets, place your token at ~/.kaggle/kaggle.json (chmod 600)
  python download_data.py            # all
  python download_data.py --uci      # only open UCI datasets (no login)
  python download_data.py --kaggle   # only Kaggle (needs your token + rules acceptance)

Outputs:
  raw/uci/*.csv          harmonised (features + column 'target_raw')
  raw/kaggle/<slug>/...  extracted as provided by Kaggle
  checksums.sha256       SHA-256 of every downloaded file (for reproducibility)

Nothing here fabricates results. These are public *inputs*; the CACE compliance
metrics are computed separately (see ../METHODOLOGY.md).
"""
from __future__ import annotations
import argparse, hashlib, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
UCI_DIR = RAW / "uci"
KAG_DIR = RAW / "kaggle"

# UCI ML Repository dataset IDs (archive.ics.uci.edu/dataset/<id>/...)
UCI = {
    "german_credit":     144,  # Statlog (German Credit Data) — 1000 x 20, target good/bad
    "taiwan_default":     350,  # Default of Credit Card Clients (Taiwan) — 30000 x 23
    "australian_credit":  143,  # Statlog (Australian Credit Approval) — 690 (anonymised)
    "japanese_credit":     27,  # Credit Approval (Japanese / "crx") — 690 (anonymised)
}

# Kaggle slugs. competitions require accepting the competition rules once (in the UI).
KAGGLE_COMPETITIONS = {
    "home-credit-default-risk": "home-credit-default-risk",
    "GiveMeSomeCredit":         "GiveMeSomeCredit",
}
KAGGLE_DATASETS = {
    "lending-club": "wordsforthewise/lending-club",
}


def fetch_uci():
    from ucimlrepo import fetch_ucirepo
    import pandas as pd
    UCI_DIR.mkdir(parents=True, exist_ok=True)
    for name, idn in UCI.items():
        print(f"[UCI] {name} (id={idn}) …", flush=True)
        ds = fetch_ucirepo(id=idn)
        X = ds.data.features.copy()
        y = ds.data.targets.copy()
        y.columns = ["target_raw"] * len(y.columns) if len(y.columns) == 1 else y.columns
        df = pd.concat([X, y], axis=1)
        out = UCI_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"       saved {out.relative_to(ROOT)}  shape={df.shape}")


def _kaggle_ok() -> bool:
    token = Path.home() / ".kaggle" / "kaggle.json"
    if not token.exists():
        print("[Kaggle] No ~/.kaggle/kaggle.json found. Skipping Kaggle datasets.\n"
              "         Get your token: kaggle.com → Account → Create New API Token.", file=sys.stderr)
        return False
    return True


def _run(cmd):
    print("       $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def fetch_kaggle():
    if not _kaggle_ok():
        return
    KAG_DIR.mkdir(parents=True, exist_ok=True)
    for slug, comp in KAGGLE_COMPETITIONS.items():
        d = KAG_DIR / slug; d.mkdir(exist_ok=True)
        print(f"[Kaggle competition] {comp} …")
        try:
            _run(["kaggle", "competitions", "download", "-c", comp, "-p", str(d)])
            _unzip_all(d)
        except subprocess.CalledProcessError:
            print(f"       !! Failed. Accept the rules once at kaggle.com/c/{comp}/rules and retry.", file=sys.stderr)
    for slug, ref in KAGGLE_DATASETS.items():
        d = KAG_DIR / slug; d.mkdir(exist_ok=True)
        print(f"[Kaggle dataset] {ref} …")
        try:
            _run(["kaggle", "datasets", "download", "-d", ref, "-p", str(d)])
            _unzip_all(d)
        except subprocess.CalledProcessError:
            print(f"       !! Failed for {ref}.", file=sys.stderr)


def _unzip_all(d: Path):
    for z in d.glob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(d)
        print(f"       unzipped {z.name}")


def write_checksums():
    out = ROOT / "checksums.sha256"
    lines = []
    for f in sorted(RAW.rglob("*")):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            lines.append(f"{h}  {f.relative_to(ROOT)}")
    out.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"[checksums] {len(lines)} files → {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uci", action="store_true")
    ap.add_argument("--kaggle", action="store_true")
    a = ap.parse_args()
    do_all = not (a.uci or a.kaggle)
    if a.uci or do_all:
        fetch_uci()
    if a.kaggle or do_all:
        fetch_kaggle()
    write_checksums()
    print("\nDone. Review checksums.sha256 and commit it (NOT the raw data — see .gitignore).")


if __name__ == "__main__":
    main()
