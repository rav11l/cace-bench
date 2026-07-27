# CASE-bench

**An open, auditable benchmark for compliance-grade AI decisions in finance.**

> ⚠️ **Scaffold / plantilla.** This README is a structure to be filled with the real
> method and results. Every `‹FILL: …›` marker is a placeholder — replace it with
> verified content before making the repository public. Do not publish placeholder
> figures as if they were results.

---

## What is CASE?

CASE (`‹FILL: full expansion of the acronym — e.g., "Compliance-Aware Scoring Evaluation"›`)
is a methodology and benchmark for making automated financial decisions
**auditable, explainable and reproducible** — so that a bank risk committee or a
supervisor can inspect *why* a decision was made, not just *what* it was.

CASE-bench is the public, reproducible harness that measures how much the CASE
methodology improves `‹FILL: the target metric — e.g., auditable-error rate /
false-decision rate / reviewability›` over a defined baseline.

**Why this exists.** Regulators and risk committees are moving toward requiring
explainability and auditability of AI-driven decisions. CASE-bench is designed to
be handed to them *before* those requirements are formalised — a common, open
yardstick rather than a vendor claim.

## Headline result

| Metric | Baseline | CASE | Δ |
|---|---|---|---|
| `‹FILL: metric name›` | `‹FILL›` | `‹FILL›` | **‹FILL: e.g., −78%›** |
| `‹FILL: e.g., AUC›` | `‹FILL›` | `‹FILL: e.g., 0.887›` | `‹FILL›` |

*All figures are reproducible from the steps in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).*

## What CASE-bench measures

- **Auditability** — `‹FILL: how you quantify that a decision can be traced/explained›`
- **Error / reliability** — `‹FILL: the error metric and how CASE reduces it›`
- **Explainability** — `‹FILL: how each decision exposes its reasoning (e.g., reasoning trace)›`
- **Reproducibility** — every result in this repo can be regenerated from public inputs.

## Repository structure

```
cace-bench/
├── README.md              — this document (public compliance artifact)
├── METHODOLOGY.md         — full methodology
├── REPRODUCIBILITY.md     — environment, data and steps to reproduce
├── CITATION.cff           — how to cite CASE-bench
├── LICENSE                — ‹FILL: Apache-2.0 recommended›
├── methodology/           — detailed specs, definitions, decision rubric
├── data/                  — dataset description and access (‹FILL›)
├── src/                   — benchmark code (‹FILL›)
└── results/               — signed, dated result reports
    └── REPORT_TEMPLATE.md — template for each benchmark run
```

## Quickstart

```bash
‹FILL: e.g., uv sync›
‹FILL: e.g., python -m case_bench.run --config configs/default.yaml›
```

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the full protocol.

## Scope and honesty

- CASE-bench measures `‹FILL›`. It does **not** claim `‹FILL: state explicit limits —
  e.g., "to certify regulatory compliance in any jurisdiction"›`.
- Results depend on the dataset and baseline defined here; other datasets may differ.
- This benchmark is a methodology and evidence tool, not legal or regulatory advice.

## How to cite

See [CITATION.cff](CITATION.cff).

## License

`‹FILL: Apache-2.0 recommended (same as Perseus), or your choice›`

---

*Maintained by Digital Economy Lab · cauceia.com · digitaleconomylab.org*
