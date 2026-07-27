# CACE — Methodology

> Compliance-Aware Credit-agent Evaluation. The framing is real; figures marked
> `‹FILL: …›` are placeholders pending the published run.

## 1. Purpose

CACE evaluates LLM-agent credit pipelines on three axes that regulators and risk
committees actually ask about: **is the decision correct, is it explainable, and is
it auditable after the fact.** CACE-bench turns those axes into measurable quantities
on fully synthetic data, and compares a CACE-governed pipeline against a defined
baseline — supporting auto-evolving agents under the same auditability constraints.

## 2. Definitions

- **Decision under test:** `‹FILL: what a single "decision" is — e.g., a credit-routing
  decision, a KYC/AML flag, a sponsor-fragility alert›`
- **Baseline:** `‹FILL: the reference approach CASE is compared against — e.g., a rule-based
  or single-pass model with no verification/explainability layer›`
- **CASE-governed pipeline:** `‹FILL: describe the CASE method — e.g., reasoning trace +
  independent verifier pass + audit log›`

## 3. Metrics

| Metric | Definition | How computed |
|---|---|---|
| `‹FILL: auditable-error rate›` | `‹FILL›` | `‹FILL›` |
| `‹FILL: explainability coverage›` | `‹FILL: % of decisions with a complete, checkable rationale›` | `‹FILL›` |
| `‹FILL: reviewer agreement›` | `‹FILL: agreement between the system's rationale and an independent reviewer›` | `‹FILL›` |
| `‹FILL: discrimination — e.g., AUC›` | `‹FILL›` | `‹FILL›` |

**The −78% headline.** State precisely what fell by 78%, against which baseline, on which
dataset, with confidence interval and sample size: `‹FILL›`. A single number without
these four elements is not defensible in front of a supervisor.

## 4. Dataset

- Source(s): `‹FILL: public sources — e.g., SEC EDGAR + FRED for Faro; describe for Cauce›`
- Size / period: `‹FILL›`
- Splits: `‹FILL: train / validation / test›`
- Access & licensing: `‹FILL›`
- Known biases / limits: `‹FILL — be explicit; regulators trust honesty about limits›`

## 5. Protocol

1. `‹FILL: data preparation›`
2. `‹FILL: run baseline›`
3. `‹FILL: run CASE-governed pipeline›`
4. `‹FILL: compute metrics + confidence intervals›`
5. `‹FILL: produce a signed, dated report (see results/REPORT_TEMPLATE.md)›`

## 6. Governance & auditability

- Every run is logged with data version, code commit hash and config.
- Every decision retains a reasoning trace that a human reviewer can check.
- Reports are dated and versioned so a supervisor can reproduce any published figure.

## 7. Limitations

`‹FILL: what CASE does not measure or guarantee; jurisdictional caveats; where human
judgement remains required.›`
