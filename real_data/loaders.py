"""
CACE-Bench · real-dataset loaders (OPTIONAL module)
===================================================
Loads the downloaded *real* credit datasets into pandas DataFrames with a
NORMALISED target column `target` where **1 = bad credit / default** and
**0 = good / no default**.

The "enrichment" here is harmonisation: each classic dataset uses a different
target encoding; this module unifies them so a single baseline can run across
all of them, alongside the fully-synthetic CACE-Bench core (../cace_bench.py).

Run download_data.py first. These loaders read raw/uci/*.
Semantic feature harmonisation is only possible where features are labelled
(German, Taiwan). Australian and Japanese ("crx") are anonymised — features are
masked — so only the target is meaningful for an AUC/error baseline.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
UCI = ROOT / "raw" / "uci"


def _read(name: str) -> pd.DataFrame:
    p = UCI / f"{name}.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found. Run: python download_data.py --uci")
    return pd.read_csv(p)


def load_german() -> pd.DataFrame:
    """Statlog German Credit — target_raw: 1=good, 2=bad → target: 1=bad."""
    df = _read("german_credit")
    tgt = df.columns[-1]
    df["target"] = (df[tgt].astype(int) == 2).astype(int)
    df["dataset"] = "german_credit"
    return df


def load_taiwan() -> pd.DataFrame:
    """Default of Credit Card Clients — target_raw: 1=default → target: 1=bad."""
    df = _read("taiwan_default")
    tgt = df.columns[-1]
    df["target"] = df[tgt].astype(int)
    df["dataset"] = "taiwan_default"
    return df


def load_australian() -> pd.DataFrame:
    """Statlog Australian Credit Approval — anonymised. target_raw: 1=approved/good? .
    Convention here: 1 = bad (rejected/negative). Verify against the UCI card."""
    df = _read("australian_credit")
    tgt = df.columns[-1]
    # UCI encodes class as {0,1}; treat the minority/"1" as positive-default per the card.
    df["target"] = df[tgt].astype(int)
    df["dataset"] = "australian_credit"
    return df


def load_japanese() -> pd.DataFrame:
    """Credit Approval ("crx") — anonymised. target_raw: '+'/'-' → target: 1 for '-' (rejected)."""
    df = _read("japanese_credit")
    tgt = df.columns[-1]
    s = df[tgt].astype(str).str.strip()
    df["target"] = (s == "-").astype(int)
    df["dataset"] = "japanese_credit"
    return df


LOADERS = {
    "german_credit": load_german,
    "taiwan_default": load_taiwan,
    "australian_credit": load_australian,
    "japanese_credit": load_japanese,
}


def load_all() -> dict[str, pd.DataFrame]:
    """Return {name: DataFrame} for every available UCI dataset (skips missing)."""
    out = {}
    for name, fn in LOADERS.items():
        try:
            out[name] = fn()
        except FileNotFoundError as e:
            print(f"skip {name}: {e}")
    return out


if __name__ == "__main__":
    for name, df in load_all().items():
        print(f"{name:20s} shape={df.shape}  bad-rate={df['target'].mean():.3f}")
