# CACE-bench

**Compliance-Aware Credit-agent Evaluation** — a fully synthetic, reproducible
benchmark and generator for evaluating and auto-evolving LLM-agent credit
pipelines under auditability constraints.

> ⚠️ **Work in progress.** The methodology and framing below are real; the
> quantitative results marked `‹FILL: …›` are placeholders pending the published
> run. Do not cite placeholder figures as results.

---

## What CACE-bench is

CACE-bench evaluates **LLM-agent credit pipelines** — systems that ingest a credit
application, reason over it, and produce a decision — against **auditability
constraints**: can each decision be explained, traced and reproduced?

It has two parts:

- **A generator** that produces *fully synthetic* credit cases and populations. No
  real personal or financial data is used, so the benchmark is shareable, privacy-safe
  and reproducible by anyone.
- **A benchmark** that scores a pipeline on decision quality *and* on auditability /
  explainability, and supports **auto-evolving** agents (iterative self-improvement
  under the same constraints).

**Why it exists.** Regulators and bank risk committees are moving toward requiring
explainable, auditable AI in credit. CACE-bench is a common, open yardstick — evidence
you can put in front of a risk committee or supervisor *before* requirements are
formalised, rather than a vendor claim.

## Headline results

> Reproducible from [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Fill from the published run.

| Metric | Baseline | With CACE | Δ |
|---|---|---|---|
| `‹FILL: auditable-error / review-failure rate›` | `‹FILL›` | `‹FILL›` | **`‹FILL: e.g., −78%›`** |
| `‹FILL: decision quality — e.g., AUC›` | `‹FILL›` | `‹FILL›` | `‹FILL›` |

## What it measures

- **Decision quality** — `‹FILL: how correctness is scored on synthetic cases›`
- **Auditability** — `‹FILL: how you quantify that a decision can be traced/explained›`
- **Explainability** — each decision exposes a checkable reasoning trace (`‹FILL: format›`)
- **Reproducibility** — every figure regenerates from the synthetic generator + fixed seeds.

## Repository structure

```
cace-bench/
├── README.md              — this document (public compliance artifact)
├── METHODOLOGY.md         — full methodology
├── REPRODUCIBILITY.md     — environment, seeds and steps to reproduce
├── CITATION.cff           — how to cite
├── .zenodo.json           — Zenodo archiving metadata (DOI)
├── LICENSE                — ‹FILL: Apache-2.0 recommended›
├── src/                   — generator + benchmark code (‹FILL›)
└── results/               — signed, dated result reports
    └── REPORT_TEMPLATE.md — template for each run
```

## Quickstart

```bash
‹FILL: e.g., uv sync›
‹FILL: e.g., python -m cace_bench.generate --seed 0›
‹FILL: e.g., python -m cace_bench.run --config configs/default.yaml›
```

## Scope and honesty

- Data is **fully synthetic** by design: this maximises reproducibility and removes
  privacy risk, but results are on synthetic populations — state this plainly to any
  supervisor and describe how the generator reflects real credit distributions (`‹FILL›`).
- CACE-bench measures auditability and decision quality; it does **not** by itself
  certify regulatory compliance in any jurisdiction.
- This is an evidence and methodology tool, not legal or regulatory advice.

## How to cite

See [CITATION.cff](CITATION.cff). A citable release (v0.1.0) and Zenodo metadata are
included in the repository.

## License

`‹FILL: Apache-2.0 recommended (same as Perseus), or your choice›`

---

*Maintained by Digital Economy Lab · cauceia.com · digitaleconomylab.org*
