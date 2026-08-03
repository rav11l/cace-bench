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

## New in v0.3 — data availability

Through v0.2 every fact a compliance narrative needed was always present, so the only way
to be wrong was to reason badly. In production the dominant failure is different: a data
provider is not live in that country, times out, or returns a payload too thin to conclude
from — and the pipeline decides anyway, citing a source that never answered.

v0.3 adds that axis:

- **Countries and provider chains.** Each of three source classes (`open_banking`,
  `alt_data`, `screening`) is resolved by walking a country's fallback chain from a
  **provider registry** ([`configs/providers.json`](configs/providers.json)). Only the
  *structure* of the registry is used — which classes of signal exist, in which countries,
  with what failure rates. No provider data of any kind enters the benchmark.
- **Consent as a gate.** A declined scope is indistinguishable, downstream, from an
  unavailable provider, and both must lead to escalation rather than a guess.
- **A third ground-truth outcome: `ESCALATE`** — the *correct* answer when the facts the
  decision needed were not obtainable. A pipeline that never escalates is now measurably
  wrong.
- **Provenance.** Every claim carries the provider it came from; citing a provider that
  did not respond is a separately reported error class.

## What it measures

- **Silent-decision rate** *(v0.3)* — share of **undecidable** cases decided anyway: the
  rate at which the system asserts a conclusion it had no data for.
- **Provenance completeness** *(v0.3)* — share of decisions in which every cited source
  actually responded.
- **Over-escalation rate** *(v0.3)* — share of decidable cases escalated needlessly: the
  operational cost of the safety net.
- **Hallucination rate** — share of the agent's statements that are fabricated or
  factually wrong.
- **Recovery rate** — share of detected errors that the verification / self-evolution
  cycle (`execute → evaluate → modify → verify → retain`) corrects before dispatch.
- **Compliance false-positive rate** — share of correct outputs wrongly flagged.
- **Step-level correctness** — quality of the decision measured step-by-step across the
  multi-agent trace, not only at the final answer.

Every figure regenerates from the synthetic generator with fixed seeds; every decision
retains a reasoning trace a human reviewer can check.

## Headline results

> Reproducible per [REPRODUCIBILITY.md](REPRODUCIBILITY.md):
> `python cace_bench.py --n 23000 --seed 0 --providers configs/providers.json`.
> Full report: [results/REPORT-2026-08-03.md](results/REPORT-2026-08-03.md).
> The auto-evolution ablation defines the baseline (self-evolution **off**) vs. CACE
> (self-evolution **on**).

**Reference run — v0.3.0, seed 0, N = 23,000 synthetic cases, registry `2026-08-03`:**

Of 23,000 cases, **3,582 (15.57%) are undecidable** — the consented sources needed for the
compliance conclusion did not all respond — so `ESCALATE` is the correct outcome for them.

| Metric | Baseline (evolution off) | With CACE (evolution on) | Δ | 95% CI (Δ, abs) | n |
|---|---|---|---|---|---|
| Silent-decision rate | 55.11% | 6.53% | **−88.1%** | [46.76, 50.39] pp | 3,582 |
| Compliance false-positive rate | 22.51% | 4.96% | −77.9% | [16.79, 18.30] pp | 14,948 |
| Hallucination rate | 2.55% | 0.62% | −75.8% | [1.71, 2.16] pp | 23,000 |
| Over-escalation rate | 3.60% | 0.53% | −85.4% | [2.79, 3.36] pp | 19,418 |
| Provenance completeness *(higher is better)* | 93.40% | 99.33% | +5.93 pp | [5.59, 6.27] pp | 23,000 |
| Recovery rate | — | 81.81% | — | — | 9,898 first-pass errors |
| Step-level correctness | 86.98% | 97.70% | +10.72 pp | — | 23,000 |

The undecidable share is a property of the **provider chain**, not of the agent: it is
what the registry's coverage assumptions imply for that country. It is the number that
explains why a pipeline escalates more in one market than in another.

**v0.2.0** — archived under [DOI 10.5281/zenodo.21394049](https://doi.org/10.5281/zenodo.21394049)
and reproducible at tag `v0.2.0` — measured the same ablation without the availability
axis: compliance false-positive rate 22.25% → 4.80% (−78.4%), hallucination 2.80% → 0.56%,
recovery 78.8%, step-level correctness 87.94% → 97.44%
([results/REPORT-2026-07-27.md](results/REPORT-2026-07-27.md),
[results/run-seed0-v0.2.0.json](results/run-seed0-v0.2.0.json)). v0.3's compliance
false-positive figure (22.51% → 4.96%) reproduces it within sampling noise on the new,
harder population.

## Repository structure

```
cace-bench/
├── README.md                     — this document (public compliance artifact)
├── METHODOLOGY.md                — full methodology (definitions, protocol, governance)
├── REPRODUCIBILITY.md            — environment, seeds and steps to reproduce
├── CITATION.cff                  — how to cite
├── .zenodo.json                  — Zenodo archiving metadata (DOI)
├── LICENSE                       — MIT
├── configs/
│   ├── default.json              — run config (n, seed, reference-agent parameters)
│   └── providers.json            — provider registry: per-country chains and coverage
├── tools/
│   └── providers_yaml_to_json.py — regenerates configs/providers.json from the registry
├── cace_bench.py                 — single-file benchmark: generator + reference agent +
│                                   deterministic ground-truth judge + ablation + metrics + CLI
└── results/                      — signed, dated result reports
    ├── REPORT-2026-08-03.md      — v0.3 reference run (seed 0, N=23,000)
    ├── run-seed0.json            — machine-readable results (v0.3)
    ├── REPORT-2026-07-27.md      — v0.2 reference run
    ├── run-seed0-v0.2.0.json     — machine-readable results (v0.2)
    └── REPORT_TEMPLATE.md        — template for each run
```

## Quickstart

Pure Python standard library — no dependencies to install.

```bash
python cace_bench.py --n 23000 --seed 0 --providers configs/providers.json --out results
# writes results/run-seed0.json and results/REPORT-<date>.md
```

`--providers` is optional: an equivalent registry is embedded in `cace_bench.py`, so the
file still runs standalone. Passing it explicitly is what makes a published figure
traceable to a registry version.

## Scope and honesty

- Data is **fully synthetic** by design: this maximises reproducibility and removes
  privacy risk, but results are on synthetic populations. The reference run also uses a
  **reference agent + judge**, not a production LLM pipeline — state both plainly to any
  supervisor; swap in a live adapter to benchmark a real system.
- **Provider coverage figures are working assumptions, not vendor-confirmed data.** Every
  number in the source registry carries a `verified` flag; those still `false` have not
  been confirmed by the provider. Coverage drives the undecidable share and therefore
  every per-country rate reported, so a figure published from an unverified registry must
  say so.
- Population base rates (P(sanctions)=0.05, P(PEP)=0.03, …) are documented parameters
  chosen to exercise the harness, **not** estimates of any real portfolio.
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
