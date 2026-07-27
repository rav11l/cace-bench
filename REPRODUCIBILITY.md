# Reproducibility

> Scaffold. The point of this file is that any reader — including a supervisor — can
> regenerate every published number. Fill the `‹FILL›` markers with the real steps.

## Environment

- Language / runtime: `‹FILL: e.g., Python ≥3.12›`
- Package manager: `‹FILL: e.g., uv›`
- Lockfile: `‹FILL: uv.lock / requirements.txt committed for exact versions›`
- Hardware used for published results: `‹FILL›`

## Data

- How to obtain: `‹FILL: download script or source URLs›`
- Version / snapshot date: `‹FILL›`
- Checksums: `‹FILL: hashes so reviewers confirm identical inputs›`

## Steps

```bash
# 1. Set up
‹FILL›

# 2. Fetch / prepare data
‹FILL›

# 3. Run baseline
‹FILL›

# 4. Run CASE-governed pipeline
‹FILL›

# 5. Compute metrics and generate the report
‹FILL›
```

## Expected output

- A dated report in `results/` matching the headline table in the README (within
  `‹FILL: tolerance / confidence interval›`).

## Provenance

Each published result records: data version, code commit hash, config file, run date.
`‹FILL: where these are stored — e.g., results/<date>/run.json›`
