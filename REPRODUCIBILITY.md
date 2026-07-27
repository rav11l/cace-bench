# Reproducibility

> The point of this file is that any reader — including a supervisor — can regenerate
> every published number from the synthetic generator. Fill the `‹FILL›` markers with
> the real commands once the code is public.

## Environment

- Language / runtime: `‹FILL: e.g., Python ≥3.12›`
- Package manager: `‹FILL: e.g., uv›`
- Lockfile: `‹FILL: uv.lock / requirements.txt committed for exact versions›`
- Hardware used for published results: `‹FILL›`

## Data

Data is **fully synthetic** — there is nothing to download. Every case, population and
multi-agent trace is produced by the generator from fixed seeds, so identical inputs
regenerate anywhere.

- Generator entry point: `‹FILL: e.g., python -m cace_bench.generate›`
- Seeds: `‹FILL: list the seeds used for the published v0.1.0 set (~23k labelled traces)›`
- Checksums: `‹FILL: hashes of the generated set so reviewers confirm identical inputs›`

## Steps

```bash
# 1. Set up
‹FILL: e.g., uv sync›

# 2. Generate the synthetic dataset (fixed seeds)
‹FILL: e.g., python -m cace_bench.generate --seed 0›

# 3. Run the baseline arm (self-evolution OFF)
‹FILL›

# 4. Run the CACE-governed arm (self-evolution ON: judge + recovery cycle)
‹FILL›

# 5. Compute metrics (95% CI, n) and generate the report
‹FILL›
```

## Expected output

- A dated report in `results/` matching the headline table in the README (within
  `‹FILL: tolerance / confidence interval›`), for all four metrics: hallucination rate,
  recovery rate, compliance false-positive rate, step-level correctness.

## Provenance

Each published result records: data version (seeds + checksum), code commit hash, config
file and run date. `‹FILL: where these are stored — e.g., results/<date>/run.json›`
