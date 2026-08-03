# Reproducibility

Any reader — including a supervisor — can regenerate every published number from the
synthetic generator. The reference run is deterministic and dependency-free.

## Environment

- Language / runtime: Python ≥ 3.10 (tested on 3.11).
- Dependencies: **none** — standard library only (`random`, `math`, `json`, `argparse`,
  `datetime`). No install step, no lockfile needed.
- Hardware: irrelevant — the run is deterministic and CPU-only (finishes in seconds).

## Data

Data is **fully synthetic** — there is nothing to download. Every case is produced by the
generator from a fixed seed, so identical inputs regenerate anywhere.

- Generator: `generate(n, seed, registry)` in `cace_bench.py`.
- Reference set: `n = 23000`, `seed = 0` (see `configs/default.json`).
- Provider registry: `configs/providers.json`, version `2026-08-03`. It supplies the
  per-country provider chains and the coverage/partial rates that decide which cases are
  *undecidable*. **Changing the registry changes every reported rate**, so a published
  figure must name the registry version alongside the seed.
- Population base rates (documented at the top of `cace_bench.py`): P(sanctions)=0.05,
  P(PEP)=0.03, P(AML alert)=0.20, P(KYC verified)=0.85; difficulty ~ Uniform(0,1).
- Consent grant rates: open banking 0.90, alt data 0.85, screening 1.00.
- Country mix: EC 0.30, MX 0.30, CO 0.15, BR 0.10, CL 0.05, PE 0.05, AR 0.05.

## Steps

```bash
python cace_bench.py --n 23000 --seed 0 --providers configs/providers.json --out results
```

This single command: generates the synthetic set, resolves each source class against the
country's provider chain, runs both ablation arms (self-evolution OFF = single,
availability-blind pass; ON = judge + recovery loop) through the deterministic
ground-truth judge, aggregates the metrics with 95% Wilson intervals, and writes:

- `results/run-seed0.json` — machine-readable counts, rates and CIs;
- `results/REPORT-<date>.md` — the signed, dated report.

Determinism: re-running with the same `--seed` and the same registry yields a
byte-identical `run-seed*.json` (verified). Change `--seed` to obtain independent
replications.

`--providers` may be omitted: an equivalent registry is embedded in `cace_bench.py` under
the version string `embedded-default`, so the file runs standalone. `configs/providers.json`
is regenerated from the product-side registry with
`python tools/providers_yaml_to_json.py <path-to>/providers.yaml configs/providers.json`.

## Expected output (v0.3.0, seed 0, N = 23,000, registry `2026-08-03`)

- Undecidable cases: 3,582 (15.57%) of 23,000.
- Silent-decision rate 55.11% → 6.53% (−88.1%), counts 1,974 → 234 of 3,582.
- Compliance false-positive rate 22.51% → 4.96% (−77.9%), counts 3,365 → 742 of 14,948.
- Hallucination rate 2.55% → 0.62% (−75.8%).
- Over-escalation rate 3.60% → 0.53%; provenance completeness 93.40% → 99.33%.
- Recovery rate 81.81% (9,898 first-pass errors); step-level correctness 86.98% → 97.70%.

Replication on `--seed 1`: undecidable 16.23%, silent-decision 55.65% → 6.59%,
compliance false-positive 22.49% → 5.08%.

## Expected output (v0.2.0, seed 0, N = 23,000)

Reproducible at tag `v0.2.0`, where the harness had no availability axis:

- Compliance false-positive rate 22.25% → 4.80% (−78.4%), counts 4,022 → 867 of 18,073
  compliant cases.
- Hallucination rate 2.80% → 0.56% (−79.9%), counts 643 → 129 of 23,000.
- Recovery rate 78.8% (6,169 first-pass errors); step-level correctness 87.94% → 97.44%.

## Provenance

Each `run-*.json` records the benchmark version, seed, n, the registry version and the
full parameter set. The signed report additionally records the run date. The figures
characterise the **reference agent + judge** on the synthetic distribution; to benchmark a
production pipeline, replace the `first_pass` / `recover` functions in `cace_bench.py`
with a live adapter exposing the same interface and re-run.

Coverage numbers in the registry are working assumptions until the provider confirms them
(`verified: false` on the product side). They are not measurements, and a report published
from an unverified registry must say so.
