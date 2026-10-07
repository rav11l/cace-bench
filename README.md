# BENCH

[![DOI](https://zenodo.org/badge/DOI/[anonymized DOI].svg)]([anonymized DOI])
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.6.0--unreleased-informational.svg)](CHANGELOG.md)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20dataset-anonymous%2Fbench--bench-yellow.svg)]([anonymized dataset])

**Compliance-Aware Credit-agent Evaluation** — *a synthetic agentic evaluation
benchmark for LLM credit-pipeline agents.* A fully synthetic, reproducible benchmark
and generator for evaluating and auto-evolving LLM-agent credit pipelines under
auditability constraints.

> ✅ **Reference run included.** The generator, judge and ablation are implemented in a
> single dependency-free file, [`bench.py`](bench.py); a dated reference
> run on 23,000 synthetic cases — 23,000 *cases*, a population size, not a step count — is
> in [results/](results/). The figures below are the **actual output of that run** (seed 0),
> reproducible by anyone. They characterise a reference agent + judge on the synthetic
> distribution — **not** a production LLM pipeline. To measure a real system, substitute
> your pipeline for `first_pass` / `recover`; the judge and every metric stay unchanged —
> see [Benchmark your own pipeline](#benchmark-your-own-pipeline).

---

## What BENCH is

BENCH evaluates **LLM-agent credit pipelines** — systems that ingest a credit
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
today there is no answer that is not the vendor's own word. BENCH is an attempt at a
common, open yardstick instead.

The obligation behind that question is uneven across the region as of August 2026. Brazil
is furthest along: Res. CMN 4.557/2017 (arts. 9 and 12) already requires lenders to
document model assumptions and limitations, validate independently and backtest, and LGPD art. 20
gives the borrower the right to have an automated decision reviewed; PL 2.338/2023 would
classify credit scoring as high-risk AI. In Ecuador, Resolución SPDP-SPD-2026-0009-R
requires that the data subject be told AI took part in the processing, and recognises the
right not to be subject to a decision based wholly *or partly* on automated processing.
Elsewhere the requirement is not yet formalised — which is precisely when evidence is worth
having, whether the reader is a supervisor or a client's vendor-risk team.

BENCH is the public, synthetic counterpart of the **CASE** LLM-as-a-judge compliance
check that runs inside the host pipeline, whose metrics map to regional frameworks
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
> `python bench.py --n 23000 --seed 0 --providers configs/providers.json`.
> Full report: [results/REPORT-2026-08-03.md](results/REPORT-2026-08-03.md).
> The auto-evolution ablation defines the baseline (self-evolution **off**) vs. BENCH
> (self-evolution **on**).

**Reference run — v0.6.0, seed 0, N = 23,000 synthetic cases, registry `2026-08-03`** (the generator and agent are unchanged since v0.3.0; v0.6.0 adds the missed-flag rate and replication on seeds 0–4, [results/run-seed0.json](results/run-seed0.json) … [run-seed4.json](results/run-seed4.json)):

Of 23,000 cases, **3,582 (15.57%) are undecidable** — the consented sources needed for the
compliance conclusion did not all respond — so `ESCALATE` is the correct outcome for them.

| Metric | Baseline (evolution off) | With BENCH (evolution on) | Δ | 95% CI (Δ, abs) | n |
|---|---|---|---|---|---|
| Silent-decision rate | 55.11% | 6.53% | **−88.1%** | [46.76, 50.39] pp | 3,582 |
| Compliance false-positive rate | **22.51%** | **4.96%** | **−77.9%** | [16.79, 18.30] pp | 14,948 |
| Compliance missed-flag rate (truly flaggable, cleared) | 15.30% | 3.47% | −77.3% | [10.65, 13.02] pp | 4,470 |
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

**v0.2.0** — archived under [DOI [anonymized DOI]]([anonymized DOI])
and reproducible at tag `v0.2.0` — measured the same ablation without the availability
axis: compliance false-positive rate 22.25% → 4.80% (−78.4%), hallucination 2.80% → 0.56%,
recovery 78.8%, step-level correctness 87.94% → 97.44%
([results/REPORT-2026-07-27.md](results/REPORT-2026-07-27.md),
[results/run-seed0-v0.2.0.json](results/run-seed0-v0.2.0.json)). v0.3's compliance
false-positive figure (22.51% → 4.96%) reproduces it within sampling noise on the new,
harder population.

## The false-positive reduction is not bought by flagging less

Every false-positive figure above now has its miss rate beside it. On seed 0 the missed-flag
rate falls with the false-positive rate (15.30% → 3.47%), and the same holds on seeds 1–4
(false positives 22.19–22.71% → 4.85–5.08%; missed flags 14.62–15.34% → 3.08–3.47%). The
recovery layer is still a documented parametric model (detection 0.85, correction 0.92), so
these figures locate the failure, they do not measure any particular judge.

## Regulatory-shift track (v0.6) — the gate, measured

[`evolve.py`](evolve.py) runs the experiment the accompanying paper describes: a supervisory
re-interpretation at 70% of the stream, a dual-loop engine that may change only the runtime
harness, and an admission gate whose every decision is written to a hash-chained log
before deployment. Three families of re-interpretation (threshold, scope, structural) at
three severities, 10 seeds each, ten arms — including **no gate**, **gate on stale labels**,
**oracle**, **manual update** and **compute-matched local-only**.

```bash
python evolve.py --seeds 10 --out results/shift            # ~7 min, standard library only
python evolve.py --seeds 10 --families struct --eps 0.01 --out results/shift-eps010
python tools/shift_tables.py results/shift                 # results/shift/tables.md
```

Over all 90 runs ([results/shift/tables.md](results/shift/tables.md)):

| Arm | Proposed | Admitted | Harmful admissions (held-out pool) | Runs with missed flags > 10% |
|---|---|---|---|---|
| Dual loop, gated | 7,449 | 144 | 0 | 0 |
| Same loops, no gate (admit if fewer errors visible in the latest window) | 5,353 | 550 | 309 | 49 |
| Gate on pre-shift labels | 8,490 | 0 | 0 | 0 |

Without the gate, false positives fall because the screen is loosened. With labels from
before the re-interpretation, the gate refuses every correct change — so after a shift the
retrospective pool is **relabelled by applying the new rule to the stored facts**; the
adaptation is supervised at the level of the rule and autonomous at the level of the
harness. Known failure: at the highest structural severity the fixed non-regression
tolerance (ε = 0.005) rejects the correct primitive replacement in 5 of 10 seeds;
ε = 0.010 recovers all 10 with no harmful admission.

**The proposer is a seeded search over a stated edit space, not a language model**, and the
typed library contains the correct primitive by construction. The track measures the bound
and the gate, not proposal quality.

The figures in the earlier conference submission (compliance FP 23.7% → 13.5% → 5.1%) were
not produced by code in this repository and are superseded by this track; do not cite them.

## Real-dataset baselines (optional, added in v0.4)

For baseline comparison the generator can optionally read public credit datasets:
German Credit, Taiwan default, Australian and Japanese credit, plus Home Credit,
GiveMeSomeCredit and Lending Club. These are **not** required to run the benchmark and are
**not** redistributed here — the [`real_data/`](real_data/) module reads locally provided
copies only, through a common column schema. See
[real_data/README.md](real_data/README.md).

## DeFi track (v0.5, draft)

A second domain on the **same judge**: agents that issue GO / NO-GO verdicts on lending
markets, curated vaults and tokenized collateral. `judge()`, `aggregate()`, `wilson()`,
`diff_ci()` and `_walk_chain()` are imported from `bench.py` unchanged; only the case
generator, the source registry and the ground-truth rule are new. NO-GO / GO /
INSUFFICIENT_DATA map onto FLAG / CLEAR / ESCALATE. Full design, rules and open questions:
[METHODOLOGY-DeFi.md](METHODOLOGY-DeFi.md).

- **Synthetic split.** `python defi_track.py --n 23000 --seed 0` — 16.88% of cases are
  undecidable; the reference agent's silent-decision rate falls from 59.71% to 7.26% with
  its verification loop on. Like the credit run, this checks the pipeline, not a real agent.
- **Historical split.** 13 cases from 12 public incidents (2022–2026), each labelled by
  the rule at a reference block *before* the event; 12 have reconstruction files from an
  archive node (one non-EVM case has no reader yet). Every re-derived
  fact carries an evidence capsule (chain, block, contract, call, SHA-256 of
  the response), so anyone can re-issue the read. `python defi_track.py --check-historical
  data/defi_historical_v0.json` prints the rule labels and their calibration against
  realised outcomes, including the one known false negative (H11).
- **Microstructure.** Exit-cost curves around three market-depth incidents and the cost of
  moving an oracle against what it lets an attacker borrow (H12), read at the block:
  `tools/microstructure.py`, results and figures in [results/defi/micro/](results/defi/micro/).
- **Prospective split.** Verdicts are committed by hash before the outcome is known
  (`prereg.py`, ledger in [data/prospective/](data/prospective/)). First commitment: P01,
  1 October 2026, block 26,097,498, 90-day horizon — a rules baseline, no language model.
- **Your agent.** `examples/defi_adapter.py` runs any agent that reads JSON on stdin and
  writes a verdict on stdout, with a model-cutoff gate, anonymised cases and a recall probe
  for the historical split. `examples/claude_code_agent.py` is a bridge for agents built on
  Claude Code.

Archive reads need your own RPC endpoints in environment variables (see `rpc.py`); nothing
in the repository holds a key. The track is a draft: thresholds are policy choices, the
historical cases were chosen after their outcomes were known, and no external agent has
been scored yet.

## Repository structure

```
bench/
├── README.md                     — this document (public compliance artifact)
├── METHODOLOGY.md                — full methodology (definitions, protocol, governance)
├── DATASHEET.md                  — datasheet for the synthetic data (both credit tracks)
├── evolve.py                     — regulatory-shift track: dual loop, gate, hash-chained log (v0.6)
├── paper/                        — LaTeX source of the accompanying paper; numbers generated from results/
├── REPRODUCIBILITY.md            — environment, seeds and steps to reproduce
├── CHANGELOG.md                  — version history
├── CITATION.cff / CITATION.md    — how to cite (machine-readable + BibTeX and DOI guidance)
├── .zenodo.json                  — Zenodo archiving metadata (DOI)
├── LICENSE                       — MIT
├── configs/
│   ├── default.json              — run config (n, seed, reference-agent parameters)
│   ├── providers.json            — provider registry: per-country chains and coverage
│   └── defi_sources.json         — DeFi source registry: per-chain sources and coverage
├── real_data/                    — optional public-dataset integration (v0.4)
│   ├── loaders.py                — readers for locally provided public credit datasets
│   ├── schema.py                 — common column schema
│   ├── download_data.py          — helper for fetching those datasets locally
│   └── requirements.txt          — dependencies for this module only
├── tools/
│   ├── shift_tables.py           — tables for the regulatory-shift track
│   ├── paper_numbers.py          — writes paper/generated/*.tex from the result files
│   ├── providers_yaml_to_json.py — regenerates configs/providers.json from the registry
│   ├── reconstruct_historical.py — DeFi: re-derives each historical label at its t0 block
│   ├── microstructure.py         — DeFi: exit-cost curves, oracle-manipulation economics
│   ├── fig_exit_curves.py        — DeFi: figure from results/defi/micro/exit_curves.csv
│   ├── fig_manipulation.py       — DeFi: figure from results/defi/micro/manipulation_h12.csv
│   ├── snapshot_p01.py           — DeFi: facts at t0 for prospective case P01
│   └── export_hf_defi.py         — DeFi: builds the DeFi configs of the HF dataset
├── examples/
│   ├── benchmark_your_pipeline.py — credit track: plug in your own pipeline
│   ├── defi_adapter.py           — DeFi: run an external agent (cutoff gate, anonymisation)
│   └── claude_code_agent.py      — DeFi: bridge for agents built on Claude Code
├── METHODOLOGY-DeFi.md           — DeFi track: design, rules, historical cases, leakage
├── defi_track.py                 — DeFi: generator, ground-truth rule, reference agent, CLI
├── rpc.py                        — DeFi: point-in-time archive reads with evidence capsules
├── prereg.py                     — DeFi: commit-reveal pre-registration for the prospective split
├── data/
│   ├── defi_historical_v0.json   — DeFi historical split, controls and prospective slots
│   ├── reconstructed/            — per-case reconstruction at t0 with capsules
│   └── prospective/ledger.jsonl  — public commitments (hashes only)
├── bench.py                 — single-file benchmark: generator + reference agent +
│                                   deterministic ground-truth judge + ablation + metrics + CLI
└── results/                      — dated result reports
    ├── REPORT-2026-10-02.md      — v0.6 reference run (seed 0, N=23,000), with missed-flag rate
    ├── run-seed0..4.json         — machine-readable results (v0.6), seeds 0–4
    ├── shift/                    — regulatory-shift track: 90 cells, gate logs, tables.md
    ├── shift-eps010/             — tolerance sensitivity (structural family, ε = 0.010)
    ├── REPORT-2026-08-03.md      — v0.3 reference run (seed 0, N=23,000)
    ├── REPORT-2026-07-27.md      — v0.2 reference run
    ├── run-seed0-v0.2.0.json     — machine-readable results (v0.2)
    ├── REPORT_TEMPLATE.md        — template for each run
    └── defi/micro/               — DeFi microstructure results and figures
```

## Quickstart

Pure Python standard library — no dependencies to install.

```bash
python bench.py --n 23000 --seed 0 --providers configs/providers.json --out results
# writes results/run-seed0.json and results/REPORT-<date>.md
```

`--providers` is optional: an equivalent registry is embedded in `bench.py`, so the
file still runs standalone. Passing it explicitly is what makes a published figure
traceable to a registry version.

Prefer to inspect the data without running code? The 23,000 reference cases (seed 0), with the reference agent's outputs and the judge's verdicts, are on Hugging Face: [anonymous/bench]([anonymized dataset]) — `load_dataset("anonymous/bench", split="test")`. The DeFi track is in two configs, `defi` (split `synthetic`) and `defi_historical` (split `historical`): `load_dataset("anonymous/bench", "defi_historical", split="historical")`.

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
  metric has small support. The missed-flag rate (all truly flaggable cases) is reported
  from v0.6.0.
- Fairness auditing requires an extended schema with protected attributes, which this
  benchmark **deliberately omits**. That work is required before any deployment.
- Validation on production data is the natural next step and has not been done.
- In the regulatory-shift track the proposer is not an LLM; see above.
- BENCH measures auditability and decision quality; it does **not** by itself
  certify regulatory compliance in any jurisdiction.
- This is an evidence and methodology tool, not legal or regulatory advice.

Any external communication reusing a headline figure must carry the synthetic-benchmark
qualifier. Quoting it as a production result is a misstatement.

## How to cite

Archived on Zenodo with a DOI. Cite **[anonymized DOI]** (concept DOI — always
resolves to the latest version; v0.1.0 = [anonymized DOI]). Machine-readable
metadata in [CITATION.cff](CITATION.cff); BibTeX and DOI guidance in
[CITATION.md](CITATION.md).

## License

**MIT** — see [LICENSE](LICENSE). Chosen so the benchmark can be freely adopted as an
open standard.

---

*Maintained by Anonymous Lab · anonymous.com · anonymous.org*
