# CACE-Bench

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21394049.svg)](https://doi.org/10.5281/zenodo.21394049)

**Compliance-Aware Credit-agent Evaluation** — *a synthetic agentic evaluation
benchmark for LLM credit-pipeline agents.* A fully synthetic, reproducible benchmark
and generator for evaluating and auto-evolving LLM-agent credit pipelines under
auditability constraints.

> ✅ **Reference run included.** The generator, judge and ablation are implemented in a
> single dependency-free file, [`cace_bench.py`](cace_bench.py); a signed, dated reference
> run on 23,000 synthetic cases is in [results/](results/). The figures below are the
> **actual output of that run** (seed 0), reproducible by anyone. They characterise a
> reference agent + judge on the synthetic distribution — **not** a production LLM
> pipeline; swap `first_pass`/`recover` for a live adapter to benchmark a real system.

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

> Reproducible per [REPRODUCIBILITY.md](REPRODUCIBILITY.md): `python cace_bench.py --n
> 23000 --seed 0`. Full report: [results/REPORT-2026-07-27.md](results/REPORT-2026-07-27.md).
> The auto-evolution ablation defines the baseline (self-evolution **off**) vs. CACE
> (self-evolution **on**).

**Reference run — seed 0, N = 23,000 synthetic cases:**

| Metric | Baseline (evolution off) | With CACE (evolution on) | Δ | 95% CI (Δ, abs) | n |
|---|---|---|---|---|---|
| Compliance false-positive rate | 22.25% | 4.80% | **−78.4%** | [16.78, 18.14] pp | 18,073 |
| Hallucination rate | 2.80% | 0.56% | −79.9% | [2.00, 2.47] pp | 23,000 |
| Recovery rate | — | 78.8% | — | — | 6,169 first-pass errors |
| Step-level correctness | 87.94% | 97.44% | +9.49 pp | — | 23,000 |

Per-arm 95% Wilson intervals — compliance FP: baseline [21.65%, 22.87%], CACE [4.50%, 5.12%].

**The −78% headline is a measured, reproducible result of the harness**, not a claim: on
23,000 synthetic cases the judge + recovery loop cut the compliance false-positive rate from
22.25% to 4.80% (−78.4%; the 95% CI on the absolute reduction excludes zero), with step-level
correctness rising to 97.44%. These figures characterise the **reference agent + judge** on
the synthetic distribution (error and recovery parameters documented in
[configs/default.json](configs/default.json)); to measure a production pipeline, swap the
agent module for a live adapter and re-run.

## Repository structure

```
cace-bench/
├── README.md              — this document (public compliance artifact)
├── METHODOLOGY.md         — full methodology (definitions, protocol, governance)
├── REPRODUCIBILITY.md     — environment, seeds and steps to reproduce
├── CITATION.cff           — how to cite
├── .zenodo.json           — Zenodo archiving metadata (DOI)
├── LICENSE                — MIT
├── configs/default.json   — run config (n, seed, reference-agent parameters)
├── cace_bench.py          — single-file benchmark: generator + reference agent +
│                            deterministic ground-truth judge + ablation + metrics + CLI
└── results/               — signed, dated result reports
    ├── REPORT-2026-07-27.md — reference run (seed 0, N=23,000)
    ├── run-seed0.json     — machine-readable results
    └── REPORT_TEMPLATE.md — template for each run
```

## Quickstart

Pure Python standard library — no dependencies to install.

```bash
python cace_bench.py --n 23000 --seed 0 --out results
# writes results/run-seed0.json and results/REPORT-<date>.md
```

## Scope and honesty

- Data is **fully synthetic** by design: this maximises reproducibility and removes
  privacy risk, but results are on synthetic populations. The reference run also uses a
  **reference agent + judge**, not a production LLM pipeline — state both plainly to any
  supervisor; swap in a live adapter to benchmark a real system.
- CACE-Bench measures auditability and decision quality; it does **not** by itself
  certify regulatory compliance in any jurisdiction.
- This is an evidence and methodology tool, not legal or regulatory advice.

## How to cite

Archived on Zenodo with a DOI. Cite **10.5281/zenodo.21394049** (concept DOI — always
resolves to the latest version; v0.1.0 = 10.5281/zenodo.21394051). Machine-readable
metadata in [CITATION.cff](CITATION.cff).

## License

**MIT** — see [LICENSE](LICENSE). Chosen so the benchmark can be freely adopted as an
open standard.

---

*Maintained by Digital Economy Lab · cauceia.com · digitaleconomylab.org*
