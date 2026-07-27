# CACE-Bench — Methodology

> Compliance-Aware Credit-agent Evaluation. The definitions, metrics and protocol below
> are real and match the published v0.1.0 metadata; figures marked `‹FILL: …›` are
> placeholders pending a signed, dated run.

## 1. Purpose

CACE-Bench evaluates LLM-agent credit pipelines on the three axes a regulator or risk
committee actually asks about: **is the decision correct, is it explainable, and is it
auditable after the fact.** CACE-Bench turns those axes into measurable quantities on
fully synthetic data, comparing an auto-evolving (CACE-governed) pipeline against a
non-evolving baseline under identical auditability constraints. It is the public,
synthetic counterpart of the **CASE** LLM-as-a-judge compliance check inside the Cauce
pipeline, whose verdict is written to `Decision.case_verdict` with a configurable pass
threshold and a regression block on self-evolution deployment.

## 2. Definitions

- **Decision under test:** an output of the LLM-agent credit pipeline at a stage that
  produces a `Decision` with an explanation — primarily the **compliance** stage
  (KYC/KYB, AML/sanctions/PEP, unauthorised-entity checks) and the routing decision.
  Each `Decision` carries a reasoning trace and a `case_verdict`.
- **Baseline (ablation, evolution off):** the pipeline **without** the self-evolution /
  recovery cycle — single-pass agent output that reaches dispatch unchecked.
- **CACE-governed pipeline (evolution on):** the same pipeline **with** the LLM-as-a-judge
  audit (control cases + judge-prompts) **and** the self-evolution recovery cycle
  (`execute → evaluate → modify → verify → retain`), with the verdict gating dispatch.

## 3. Metrics

| Metric | Definition | How computed |
|---|---|---|
| Hallucination rate | Share of the agent's statements that are fabricated or factually wrong (auditable-error rate). | Judge evaluates each statement in the trace against synthetic ground truth; wrong ÷ total. |
| Recovery rate | Share of detected errors corrected by the verification / self-evolution cycle before dispatch. | Errors fixed after `modify → verify` ÷ errors detected. |
| Compliance false-positive rate | Share of correct outputs wrongly flagged (cost of the safety net). | Judge flags disagreeing with ground truth ÷ correct outputs. |
| Step-level correctness | Decision quality scored step-by-step across the multi-agent trace, not only at the final answer. | Correct steps ÷ total steps against the synthetic ground-truth trace. |

**The −78% headline.** On synthetic data under a rule-reinterpretation stress scenario, the
**compliance false-positive rate** was 23.7% with self-evolution off and 5.1% with
self-evolution on — a 78% relative reduction — while the hallucination rate fell from 8.6%
to 5.4% with no regression on already-correct cases. Baseline = evolution off; CACE =
evolution on. Still to attach for full defensibility: 95% confidence interval and sample
size (n) from the signed run (published by Digital Economy Lab; data 100% synthetic).

## 4. Dataset

- **Source:** fully synthetic. A generator produces credit cases, populations and
  **~23k labelled multi-agent traces** that reflect real credit distributions — no real
  personal or company data. `‹FILL: describe how the generator's distributions are
  calibrated / validated›`
- **Size:** ~23,000 labelled multi-agent traces (v0.1.0).
- **Splits:** `‹FILL: generation / control / test, with seeds›`
- **Access & licensing:** synthetic data is shareable; released under MIT.
- **Known biases / limits:** results are on synthetic populations by design — be explicit
  about where the generator may diverge from LatAm reality. `‹FILL — regulators trust
  honesty about limits›`

## 5. Protocol

1. Generate the synthetic case set, populations and labelled traces with fixed seeds.
2. Run the **baseline** arm (self-evolution off) and log every `Decision` and step.
3. Run the **CACE-governed** arm (judge + control cases + self-evolution cycle) and log
   every `Decision`, `case_verdict` and step.
4. Compute hallucination rate, recovery rate, compliance false-positive rate and
   step-level correctness with 95% confidence intervals and sample sizes.
5. Produce a signed, dated report (see [results/REPORT_TEMPLATE.md](results/REPORT_TEMPLATE.md)).

## 6. Governance & auditability

- Every run is logged with data version, code commit hash and config.
- Every decision retains a reasoning trace that a human reviewer can check.
- The `case_verdict` gates dispatch; a configurable threshold and a regression block on
  self-evolution deployment keep an unverified change from reaching production.
- Metrics map to regional frameworks (Bacen · BR, CNBV · MX, SFC · CO, SB · EC) to support
  explainability (XAI) and model-risk-management audits.
- Reports are dated and versioned so a supervisor can reproduce any published figure.

## 7. Limitations

CACE-Bench measures auditability and decision quality on **synthetic** data; it does not
certify regulatory compliance in any jurisdiction, does not replace human judgement on
individual credit decisions, and its regional mapping is an aid to audits, not a legal
opinion. `‹FILL: add any jurisdiction-specific caveats surfaced during the published run.›`
