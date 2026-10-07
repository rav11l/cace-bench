# BENCH — Methodology

> BENCH (full name withheld for review). The definitions, metrics and protocol below
> are those of the reference run in `bench.py`; the regulatory-shift track is
> specified in `evolve.py` and the accompanying paper. Every figure cited here is an output
> of a dated run in `results/`.

## 1. Purpose

BENCH evaluates LLM-agent credit pipelines on the three axes a regulator or risk
committee actually asks about: **is the decision correct, is it explainable, and is it
auditable after the fact.** BENCH turns those axes into measurable quantities on
fully synthetic data, comparing an auto-evolving (BENCH-governed) pipeline against a
non-evolving baseline under identical auditability constraints. It is the public,
synthetic counterpart of the **CASE** LLM-as-a-judge compliance check inside the host
pipeline, whose verdict is written to `Decision.case_verdict` with a configurable pass
threshold and a regression block on self-evolution deployment.

## 2. Definitions

- **Decision under test:** an output of the LLM-agent credit pipeline at a stage that
  produces a `Decision` with an explanation — primarily the **compliance** stage
  (KYC/KYB, AML/sanctions/PEP, unauthorised-entity checks) and the routing decision.
  Each `Decision` carries a reasoning trace and a `case_verdict`.
- **Baseline (ablation, evolution off):** the pipeline **without** the self-evolution /
  recovery cycle — single-pass agent output that reaches dispatch unchecked.
- **BENCH-governed pipeline (evolution on):** the same pipeline **with** the LLM-as-a-judge
  audit (control cases + judge-prompts) **and** the self-evolution recovery cycle
  (`execute → evaluate → modify → verify → retain`), with the verdict gating dispatch.

## 3. Metrics

| Metric | Definition | How computed |
|---|---|---|
| Hallucination rate | Share of the agent's statements that are fabricated or factually wrong (auditable-error rate). | Judge evaluates each statement in the trace against synthetic ground truth; wrong ÷ total. |
| Recovery rate | Share of detected errors corrected by the verification / self-evolution cycle before dispatch. | Errors fixed after `modify → verify` ÷ errors detected. |
| Compliance false-positive rate | Share of correct outputs wrongly flagged (cost of the safety net). | Judge flags disagreeing with ground truth ÷ correct outputs. |
| Step-level correctness | Decision quality scored step-by-step across the multi-agent trace, not only at the final answer. | Correct steps ÷ total steps against the synthetic ground-truth trace. |

**The −78% headline.** In the reference run (seed 0, N = 23,000; see `results/`), the
**compliance false-positive rate** was **22.25%** with self-evolution off and **4.80%** with
self-evolution on — a **78.4% relative reduction**, 95% CI on the absolute reduction
[16.78, 18.14] pp (excludes zero) — while the hallucination rate fell from 2.80% to 0.56%.
Baseline = evolution off; BENCH = evolution on. These figures characterise the **reference
agent + judge** on the synthetic distribution (parameters in `configs/default.json`); swap
in a live adapter to benchmark a production pipeline.

## 4. Dataset

- **Source:** fully synthetic. A generator produces credit cases, populations and
  **~23k labelled multi-agent traces** that reflect real credit distributions — no real
  personal or company data. The distributions are **not calibrated** to any portfolio: base rates,
  provider coverage and injected first-pass error rates are documented parameters chosen
  to exercise the pipeline (see `configs/` and DATASHEET.md). Only contrasts between arms
  are informative; absolute levels are set by the parameters.
- **Size:** 23,000 synthetic cases per reference run; 23,000 screening alerts per run in
  the regulatory-shift track (90 runs).
- **Splits:** reference run — one population per seed (seeds 0–4 published), both arms
  scored on the same cases. Regulatory-shift track — pre-shift pool split by case index
  into a gate half (even) and an audit half (odd, never seen by the gate); adaptation on
  [70%, 85%) of the stream; held-out evaluation on [85%, 100%]; seeds 0–9 per cell.
- **Access & licensing:** synthetic data is shareable; released under MIT.
- **Known biases / limits:** results are on synthetic populations by design — be explicit
  about where the generator may diverge from LatAm reality. Known divergences: provider
  coverage is assumed, not vendor-confirmed; sanctions and PEP base rates are illustrative;
  ownership chains in the shift track are drawn from simple parametric distributions; no
  protected attributes, so no fairness analysis is possible.

## 5. Protocol

1. Generate the synthetic case set, populations and labelled traces with fixed seeds.
2. Run the **baseline** arm (self-evolution off) and log every `Decision` and step.
3. Run the **BENCH-governed** arm (judge + control cases + self-evolution cycle) and log
   every `Decision`, `case_verdict` and step.
4. Compute hallucination rate, recovery rate, compliance false-positive rate and
   step-level correctness with 95% confidence intervals and sample sizes.
5. Produce a dated report (see [results/REPORT_TEMPLATE.md](results/REPORT_TEMPLATE.md)).

## 6. Governance & auditability

- Every run is logged with data version, code commit hash and config.
- Every decision retains a reasoning trace that a human reviewer can check.
- The `case_verdict` gates dispatch; a configurable threshold and a regression block on
  self-evolution deployment keep an unverified change from reaching production.
- Metrics map to regional frameworks (Bacen · BR, CNBV · MX, SFC · CO, SB · EC) to support
  explainability (XAI) and model-risk-management audits.
- Reports are dated and versioned so a supervisor can reproduce any published figure.

## 7. Limitations

BENCH measures auditability and decision quality on **synthetic** data; it does not
certify regulatory compliance in any jurisdiction, does not replace human judgement on
individual credit decisions, and its regional mapping is an aid to audits, not a legal
opinion. Jurisdiction-specific caveat: the undecidable share per country (10.8–23.1% on
  seed 0) is driven entirely by assumed provider coverage and must be re-estimated before
  it is quoted for any market.
