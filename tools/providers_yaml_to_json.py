#!/usr/bin/env python3
"""Export Cauce's config/providers.yaml into the flat registry the benchmark reads.

The benchmark stays dependency-free (stdlib only), so the YAML lives on the
product side and this one-shot converter — which may use PyYAML — produces
configs/providers.json. Run it whenever the registry changes; commit both files
so a published result can be traced to the exact coverage assumptions behind it.

    python tools/providers_yaml_to_json.py ../cauce/config/providers.yaml configs/providers.json
"""
from __future__ import annotations

import json
import sys

import yaml


def convert(src: str) -> dict:
    raw = yaml.safe_load(open(src, encoding="utf-8"))
    providers = {}
    for p in raw["providers"]:
        providers[p["id"]] = {
            "class": p["class"],
            "partial_rate": (p.get("partial_rate") or {}).get("value", 0.0),
            "p95_latency_ms": (p.get("p95_latency_ms") or {}).get("value", 0),
            "cost_usd_per_pull": (p.get("cost_usd_per_pull") or {}).get("value", 0.0),
            "countries": {c: v["coverage"] for c, v in (p.get("countries") or {}).items()},
            # carried through so a report can state which numbers are confirmed
            "unverified_fields": sorted(
                k for k in ("p95_latency_ms", "partial_rate", "cost_usd_per_pull")
                if isinstance(p.get(k), dict) and not p[k].get("verified", False)
            ),
        }
    return {
        "version": raw.get("version", "unknown"),
        "providers": providers,
        "chains": raw.get("chains", {}),
        "budgets": raw.get("budgets", {}),
    }


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "../cauce/config/providers.yaml"
    dst = sys.argv[2] if len(sys.argv) > 2 else "configs/providers.json"
    out = convert(src)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"{src} -> {dst}: {len(out['providers'])} providers, {len(out['chains'])} countries")
