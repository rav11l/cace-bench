# CACE-Bench

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21394049.svg)](https://doi.org/10.5281/zenodo.21394049)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.1-informational.svg)](CHANGELOG.md)

**Compliance-Aware Credit-agent Evaluation** — *a synthetic agentic evaluation
benchmark for LLM credit-pipeline agents.* A fully synthetic, reproducible benchmark
and generator for evaluating and auto-evolving LLM-agent credit pipelines under
auditability constraints.

> ✅ **Reference run included.** The generator, judge and ablation are implemented in a
> single dependency-free file, [`cace_bench.py`](cace_bench.py); a signed, dated reference
> run on 23,000 synthetic cases — 23,000 *cases*, a population size, not a step count — is
> in [results/](results/). The figures below are the **actual output of that run** (seed 0),
> reproducible by anyone. They characterise a reference agent + judge on the synthetic
> distribution — **not** a production LLM pipeline. To measure a real system, substitute
> your pipeline for `first_pass` / `recover`; the judge and every metric stay unchanged —
> see [Benchmark your own pipeline](#benchmark-your-own-pipeline).

---

## What CACE-Bench is

CACE-Bench evaluates **LLM-agent credit pipelines** — systems that ingest a credit
application, reason over it across stages (`intake → extraction → profiling →
compliance`), and hand a verified result and its evidence to the lender that decides —
against **auditability constraints**: can each decision be explained, traced and
reproduced, and are the agent's own statements checked before they reach a lender or a
borrower?

It has two parts:

- **A generator** that produces *fully synthetic* credit cases, populations and
  multi-agent traces. No real personal or company data is used, so the benchmark is
  shareable, privacy-safe and reproducible by anyone.
- **A benchmark** that scores a pipeline on decision quality *and* on auditability,
  and supports **auto-evolving** agents (iterative self-improvement under the same
  constraints) — shipped with an **auto-evolution ablation** on ~23k labelled
  multi-agent traces.

**Why it exists.** Vendors in this category publish bare percentages — 95% accuracy, 88%
auto-resolution, −78% false positives — with no case set, no protocol and no way for a
third party to repeat them. A bank's risk committee eventually asks *compared to what*, and
today there is no answer that is not the vendor's own word. CACE-Bench is an attempt at a
common, open yardstick instead.

The obligation behind that question is uneven across the region as of August 2026. Brazil
is furthest along: Res. CMN 4.966 and Res. BCB 4.557 already require lenders to document
model assumptions and limitations, validate independently and backtest, and LGPD art. 20
gives the borrower the right to have an automated decision reviewed; PL 2.338/2023 would
classify credit scoring as high-risk AI. In Ecuador, Resolución SPDP-SPD-2026-0009-R
requires that the data subject be told AI took part in the processing, and recognises the
right not to be subject to a decision based wholly *or partly* on automated processing.
Elsewhere the requirement is not yet formalised — which is precisely when evidence is worth
having, whether the reader is a supervisor or a client's vendor-risk team.

CACE-Bench is the public, synthetic counterpart of the **CASE** LLM-as-a-judge compliance
check that runs inside the Cauce pipeline, whose metrics map to regional frameworks
(Bacen · BR, CNBV · MX, SFC · CO, SB / SEPS / UAFE · EC).

**An open yardstick written by one vendor to measure itself is worth little.** If you run a
credit or compliance pipeline and would rather the case set were defined jointly than handed
down, that is the more useful version of this project — see
[Benchmark your own pipeline](#benchmark-your-own-pipeline).

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

All rates are reported with **95% Wilson confidence intervals**, computed from genuine
counts. Every figure regenerates from the synthetic generator with fixed seeds; every
decision retains a reasoning trace a human reviewer can check.

## Headline results — the reference run in this repository

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
| Compliance false-positive rate | **22.51%** | **4.96%** | **−77.9%** | [16.79, 18.30] pp | 14,948 |
| Hallucination rate | 2.55% | 0.62% | −75.8% | [1.71, 2.16] pp | 23,000 |
| Over-escalation rate | 3.60% | 0.53% | −85.4% | [2.79, 3.36] pp | 19,418 |
| Provenance completeness *(higher is better)* | 93.40% | 99.33% | +5.93 pp | [5.59, 6.27] pp | 23,000 |
| Recovery rate | — | 81.81% | — | — | 9,898 first-pass errors |
| Step-level correctness | 86.98% | 97.70% | +10.72 pp | — | 23,000 |

The undecidable share is a property of the **provider chain**, not of the agent: it is
what the registry's coverage assumptions imply for that country. It is the number that
explains why a pipeline escalates more in one market than in another.

**Note on "23,000".** In this repository 23,000 is the number of **synthetic cases** the
reference run generates (`--n 23000`) — a population size, not a step count. The figure
carries a different meaning in the accompanying paper; see the next section.

**v0.2.0** — archived under [DOI 10.5281/zenodo.21394049](https://doi.org/10.5281/zenodo.21394049)
and reproducible at tag `v0.2.0` — measured the same ablation without the availability
axis: compliance false-positive rate 22.25% → 4.80% (−78.4%), hallucination 2.80% → 0.56%,
recovery 78.8%, step-level correctness 87.94% → 97.44%
([results/REPORT-2026-07-27.md](results/REPORT-2026-07-27.md),
[results/run-seed0-v0.2.0.json](results/run-seed0-v0.2.0.json)). v0.3's compliance
false-positive figure (22.51% → 4.96%) reproduces it within sampling noise on the new,
harder population.

## Results reported in the accompanying paper — that harness is not in this repository

The paper *Compliance-Bounded Self-Evolution of LLM Agents in Regulated Credit Pipelines:
A Dual-Loop Harness Architecture with Three-Level Quality Metrics* reports a **different
experiment**: a simulated regulatory re-interpretation degrades the compliance beneficiary
primitive at the 70% mark of the stream, and four conditions are compared — pre-shift
healthy, post-shift degraded, a local-only ablation, and the full dual-loop architecture.
There the compliance false-positive rate rises to 23.7% after the shift, the local loop
recovers it to 13.5%, and the dual loop to 5.1% (−78% relative). That protocol counts
~23,000 labelled **trace steps** over 3,000 applications.

**That harness is not part of this repository yet.** The code here implements the
two-condition auto-evolution ablation above and reproduces 22.51% → 4.96% on 23,000
synthetic **cases**. The regulatory-shift harness and its four-condition protocol are
planned for a later release, so that every number published here can be regenerated from
the code beside it.

When quoting **23.7% → 5.1%**, cite the paper. When quoting **22.51% → 4.96%**, cite this
repository or its Zenodo record. Either way, state that the figure is measured on a
synthetic benchmark: it is illustrative of the method, not of production performance.

## Real-dataset baselines (optional, added in v0.4)

For baseline comparison the generator can optionally read public credit datasets:
German Credit, Taiwan default, Australian and Japanese credit, plus Home Credit,
GiveMeSomeCredit and Lending Club. These are **not** required to run the benchmark and are
**not** redistributed here — the [`real_data/`](real_data/) module reads locally provided
copies only, through a common column schema. See
[real_data/README.md](real_data/README.md).

## Repository structure

```
cace-bench/
├── README.md                     — this document (public compliance artifact)
├── METHODOLOGY.md                — full methodology (definitions, protocol, governance)
├── REPRODUCIBILITY.md            — environment, seeds and steps to reproduce
├── CHANGELOG.md                  — version history
├── CITATION.cff / CITATION.md    — how to cite (machine-readable + BibTeX and DOI guidance)
├── .zenodo.json                  — Zenodo archiving metadata (DOI)
├── LICENSE                       — MIT
├── configs/
│   ├── default.json              — run config (n, seed, reference-agent parameters)
│   └── providers.json            — provider registry: per-country chains and coverage
├── real_data/                    — optional public-dataset integration (v0.4)
│   ├── loaders.py                — readers for locally provided public credit datasets
│   ├── schema.py                 — common column schema
│   ├── download_data.py          — helper for fetching those datasets locally
│   └── requirements.txt          — dependencies for this module only
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

## Benchmark your own pipeline

The reference agent is deliberately the smallest part of this repository. Everything that
makes a figure comparable — the population, the provider chains, the ground truth and the
judge — is independent of whose agent produced the answer.

To measure a real system, replace `first_pass` (and, if you have a verification or
self-correction loop, `recover`) with an adapter that calls your pipeline. Both take a
`Case` and return a `Narrative`; nothing else changes. A ready-to-run adapter is in [`examples/benchmark_your_pipeline.py`](examples/benchmark_your_pipeline.py): change the two marked spots (`call_your_pipeline` and `OUTCOME_MAP`), sanity-check it with `--demo`, then point it at your system with `--endpoint`.

**What your adapter receives.** A `Case` carries the synthetic applicant and, importantly,
what was *obtainable* about them: `country`, `consent`, and `sources` — one `SourceState`
per source class (`open_banking`, `alt_data`, `screening`) recording whether the chain
responded, which provider answered, whether the payload was partial, and which providers
were tried in order. `truth` (`FLAG` / `CLEAR` / `ESCALATE`) and `decidable` are the ground
truth; an adapter must not read them.

**What your adapter returns.** A `Narrative` with the four fields the judge actually scores:

| Field | Meaning |
|---|---|
| `outcome` | `FLAG`, `CLEAR` or `ESCALATE`. `ESCALATE` is the correct answer when the facts the decision needed were not obtainable |
| `claims_kyc_verified` | whether the narrative asserts KYC was verified |
| `cites_aml_basis` | whether an AML conclusion is given a stated basis |
| `cited` | claim → provider name, or `None` for a claim asserted without a source |

`judge()` is deterministic and unchanged: it compares the narrative against the case's
ground truth and against the set of providers that actually responded. The `err_*` flags on
`Narrative` are internal bookkeeping for the reference agent's two-arm ablation — an
external adapter leaves them alone.

**What you get.** Six of the seven metrics — silent-decision rate, compliance
false-positive rate, hallucination rate, over-escalation rate, provenance completeness and
step-level correctness — compute for any adapter, with Wilson intervals, per country and in
aggregate. Recovery rate is the exception: it is defined by the off/on ablation and needs
both arms, so it is meaningful only for a system whose verification loop can be switched
off.

**What it will not tell you.** Anything about production performance. The population is
synthetic and the error rates are injected parameters; a result characterises how a pipeline
behaves on this distribution, not on a portfolio. That limit belongs in any figure published
from it.

To run this against a live compliance pipeline, or to co-define the case set so the
yardstick is not one vendor's, open an issue — that conversation is the point of publishing
it.

## Scope and honesty

- Data is **fully synthetic** by design: this maximises reproducibility and removes
  privacy risk, but results are on synthetic populations. External validity is limited and
  the headline numbers depend on the injected error rates. The reference run also uses a
  **reference agent + judge**, not a production LLM pipeline — state both plainly to any
  supervisor; swap in a live adapter to benchmark a real system.
- **Provider coverage figures are working assumptions, not vendor-confirmed data.** Every
  number in the source registry carries a `verified` flag; those still `false` have not
  been confirmed by the provider. Coverage drives the undecidable share and therefore
  every per-country rate reported, so a figure published from an unverified registry must
  say so.
- Population base rates (P(sanctions)=0.05, P(PEP)=0.03, …) are documented parameters
  chosen to exercise the harness, **not** estimates of any real portfolio.
- Agent-level metrics need large samples; sanctioned cases are rare, so the missed-check
  metric has small support.
- Fairness auditing requires an extended schema with protected attributes, which this
  benchmark **deliberately omits**. That work is required before any deployment.
- Validation on production data is the natural next step and has not been done.
- CACE-Bench measures auditability and decision quality; it does **not** by itself
  certify regulatory compliance in any jurisdiction.
- This is an evidence and methodology tool, not legal or regulatory advice.

Any external communication reusing a headline figure must carry the synthetic-benchmark
qualifier. Quoting it as a production result is a misstatement.

## How to cite

Archived on Zenodo with a DOI. Cite **10.5281/zenodo.21394049** (concept DOI — always
resolves to the latest version; v0.1.0 = 10.5281/zenodo.21394051). Machine-readable
metadata in [CITATION.cff](CITATION.cff); BibTeX and DOI guidance in
[CITATION.md](CITATION.md).

## License

**MIT** — see [LICENSE](LICENSE). Chosen so the benchmark can be freely adopted as an
open standard.

---

*Maintained by Digital Economy Lab · cauceia.com · digitaleconomylab.org*
