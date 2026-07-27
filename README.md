# CACE-Bench

**Compliance-Aware Credit-agent Evaluation** — *a synthetic agentic evaluation
benchmark for LLM credit-pipeline agents.* A fully synthetic, reproducible benchmark
and generator for evaluating and auto-evolving LLM-agent credit pipelines under
auditability constraints.

> ⚠️ **Work in progress.** The methodology and framing are real and match the published
> v0.1.0 metadata. Headline figures below are Digital Economy Lab's published synthetic-run
> results; **95% confidence intervals and sample size (n) are still pending** a signed,
> dated report ([results/REPORT_TEMPLATE.md](results/REPORT_TEMPLATE.md)). Remaining
> `‹FILL›` markers are not yet-published values — do not cite them as results.

---

## What CACE-Bench is

CACE-Bench evaluates **LLM-agent credit pipelines** — systems that ingest a credit
application, reason over it across stages (`intake → extraction → profiling →
compliance → routing → dispatch`), and produce decisions — against **auditability
constraints**: can each decision be explained, traced and reproduced, and are the
agent's own statements checked before they reach a lender or a borrower?

It has two parts:

- **A generator** that produces *fully synthetic* credit cases, populations and
  multi-agent traces. No real personal or company data is used, so the benchmark is
  shareable, privacy-safe and reproducible by anyone.
- **A benchmark** that scores a pipeline on decision quality *and* on auditability,
  and supports **auto-evolving** agents (iterative self-improvement under the same
  constraints) — shipped with an **auto-evolution ablation** on ~23k labelled
  multi-agent traces.

**Why it exists.** Regulators and bank risk committees across LatAm are moving toward
requiring explainable, auditable AI in credit. CACE-Bench is a common, open yardstick —
evidence you can put in front of a risk committee or supervisor *before* requirements
are formalised, rather than a vendor claim. It is the public, synthetic counterpart of
the **CASE** LLM-as-a-judge compliance check that runs inside the Cauce pipeline, whose
metrics map to regional frameworks (Bacen · BR, CNBV · MX, SFC · CO, SB · EC).

## What it measures

CACE-Bench reports four quantities (per the v0.1.0 metadata):

- **Hallucination rate** — share of the agent's statements that are fabricated or
  factually wrong (the *auditable-error* rate a supervisor cares about most).
- **Recovery rate** — share of detected errors that the verification / self-evolution
  cycle (`execute → evaluate → modify → verify → retain`) corrects before dispatch.
- **Compliance false-positive rate** — share of correct outputs wrongly flagged
  (the cost of the safety net).
- **Step-level correctness** — quality of the decision measured step-by-step across the
  multi-agent trace, not only at the final answer.

Every figure regenerates from the synthetic generator with fixed seeds; every decision
retains a reasoning trace a human reviewer can check.

## Headline results

> Reproducible per [REPRODUCIBILITY.md](REPRODUCIBILITY.md). **Fill from a signed, dated
> run**; a number without baseline, dataset, 95% CI and n is not defensible in front of a
> supervisor. The auto-evolution ablation defines the baseline (self-evolution **off**)
> vs. CACE (self-evolution **on**).

| Metric | Baseline (evolution off) | With CACE (evolution on) | Δ | 95% CI | n |
|---|---|---|---|---|---|
| Hallucination rate | 8.6% | 5.4% | −37% | `‹FILL›` | `‹FILL›` |
| Recovery rate | `‹FILL›` | `‹FILL›` | `‹FILL›` | `‹FILL›` | `‹FILL›` |
| Compliance false-positive rate | 23.7% | 5.1% | **−78%** | `‹FILL›` | `‹FILL›` |
| Step-level correctness | `‹FILL›` | `‹FILL›` | no regression on already-correct cases | `‹FILL›` | `‹FILL›` |

*Figures published by Digital Economy Lab (digitaleconomylab.org); data 100% synthetic.
95% confidence intervals and per-comparison n are still pending a signed report.*

**The −78% headline.** Under a rule-reinterpretation stress scenario on synthetic data, the
**compliance false-positive rate** was **23.7%** with self-evolution off and was brought
back to **5.1%** with self-evolution on — a **78% relative reduction** — while the
**hallucination rate** fell from **8.6%** to **5.4%**, with no regression on already-correct
cases. Baseline = evolution off; CACE = evolution on. Still needed for full defensibility:
95% confidence intervals and per-comparison sample size (n) from the signed run; the dataset
is ~23k labelled synthetic traces.

## Repository structure

```
cace-bench/
├── README.md              — this document (public compliance artifact)
├── METHODOLOGY.md         — full methodology (definitions, protocol, governance)
├── REPRODUCIBILITY.md     — environment, seeds and steps to reproduce
├── CITATION.cff           — how to cite
├── .zenodo.json           — Zenodo archiving metadata (DOI)
├── LICENSE                — MIT
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
- CACE-Bench measures auditability and decision quality; it does **not** by itself
  certify regulatory compliance in any jurisdiction.
- This is an evidence and methodology tool, not legal or regulatory advice.

## How to cite

See [CITATION.cff](CITATION.cff). A citable release (v0.1.0) and Zenodo metadata are
included in the repository.

## License

**MIT** — see [LICENSE](LICENSE). Chosen so the benchmark can be freely adopted as an
open standard.

---

*Maintained by Digital Economy Lab · cauceia.com · digitaleconomylab.org*
