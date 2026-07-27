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

- Generator: `generate(n, seed)` in `cace_bench.py`.
- Reference set: `n = 23000`, `seed = 0` (see `configs/default.json`).
- Population base rates (documented at the top of `cace_bench.py`): P(sanctions)=0.05,
  P(PEP)=0.03, P(AML alert)=0.20, P(KYC verified)=0.85; difficulty ~ Uniform(0,1).

## Steps

```bash
python cace_bench.py --n 23000 --seed 0 --out results
```

This single command: generates the synthetic set, runs both ablation arms
(self-evolution OFF = single pass; ON = judge + recovery loop) through the deterministic
ground-truth judge, aggregates the four metrics with 95% Wilson intervals, and writes:

- `results/run-seed0.json` — machine-readable counts, rates and CIs;
- `results/REPORT-<date>.md` — the signed, dated report.

Determinism: re-running with the same `--seed` yields a byte-identical `run-seed*.json`
(verified). Change `--seed` to obtain independent replications.

## Expected output (seed 0, N = 23,000)

- Compliance false-positive rate 22.25% → 4.80% (−78.4%), counts 4022 → 867 of 18,073
  compliant cases.
- Hallucination rate 2.80% → 0.56% (−79.9%), counts 643 → 129 of 23,000.
- Recovery rate 78.8% (6,169 first-pass errors); step-level correctness 87.94% → 97.44%.

## Provenance

Each `run-*.json` records the benchmark version, seed, n and the full parameter set. The
signed report additionally records the run date. The figures characterise the **reference
agent + judge** on the synthetic distribution; to benchmark a production pipeline, replace
the `first_pass` / `recover` functions in `cace_bench.py` with a live adapter exposing the
same interface and re-run.
