# CACE-Bench

**Compliance-Aware Credit-agent Evaluation** — a fully synthetic, reproducible benchmark and
generator for evaluating and *auto-evolving* LLM-agent credit pipelines under auditability
constraints.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/version-v0.1.0-informational)
<!-- After you mint a Zenodo DOI (see "How to cite"), add:
[![DOI](https://zenodo.org/badge/DOI/REPLACE_WITH_DOI.svg)](https://doi.org/REPLACE_WITH_DOI) -->

> **Fully synthetic — no real personal or company data.** Identifiers (INN/OGRN) are
> format-valid (correct checksums) but randomly generated; the "registry" is a self-authored
> oracle; sanctioned entities are fictitious. For methodology and benchmarking only.

CACE-Bench accompanies work on **compliance-bounded self-evolution** of LLM agents in regulated
credit pipelines. Standard tabular credit datasets (German Credit, Home Credit) give feature
distributions and a default label, but no dialogues, execution traces, or *labelled agent errors* —
so they cannot measure hallucination, recovery, or instruction adherence, nor demonstrate an
auto-evolution loop. CACE-Bench fills that gap with a controllable, reproducible **agentic** layer.

---

## What's inside

```
generate_dataset.py            # the generator (edit + rerun to regenerate; seed 20260701)
DATASHEET.md                   # dataset documentation (composition, limits, ethics)
requirements.txt               # numpy, pandas
data/
  applications.csv             # 3,000 applications + gold fields
  registry_oracle.json         # 4,200 companies = compliance ground truth (checksum-valid IDs)
  traces.jsonl                 # ~23,000 labelled multi-agent steps  <-- primary object
  consistency_set.jsonl        # 300 x 5 repeated score_pd (Consistency metric)
  splits.json                  # historical / dev / test, T_index, previously_correct
reports/
  metrics_report.md            # three-level metrics + auto-evolution ablation
  stats.json                   # machine-readable metrics
CITATION.cff  .zenodo.json  LICENSE
```

## Headline result

At time **T** (70% of the chronologically ordered stream) a simulated regulatory re-interpretation
degrades the compliance beneficiary primitive. Three conditions are compared on the post-T window:

| Condition | Compliance FP rate |
|---|---|
| pre-T (healthy) | ~3% |
| post-T baseline (degraded) | **23.7%** |
| post-T local-only (Self-Harness) | 13.5% (−43% rel.) |
| post-T dual-loop (+AEGIS) | **5.1% (−78% rel.)** |

Hallucination rate falls 8.6% -> 5.4%; step-level correctness returns to 0.995 (no regression on
previously correct cases). Full metrics in [`reports/metrics_report.md`](reports/metrics_report.md).

## Quick start

```bash
pip install -r requirements.txt
python generate_dataset.py        # deterministic; regenerates data/ and reports/
```

To scale or reshape: edit `N_APPS`, `SANCTION_RATE`, the error-rate dicts
(`BASE` / `DEGRADED` / `LOCAL_ONLY` / `DUAL_LOOP`) and `T_INDEX` at the top of the script.

## Trace schema (`data/traces.jsonl`)

```json
{"application_id":"APP-000013","step_id":4,"agent":"Agent-Compliance",
 "primitive":"check_beneficiary_115fz","gold":"clear","output":"flag",
 "injected_error":"false_positive","recovered":true,"final_correct":true,
 "period":"pre_T","variant":"baseline","split":"historical"}
```

- `variant` in {`baseline`, `local_only`, `dual_loop`} — `baseline` spans all applications;
  the two evolution variants span the post-T eval window (for the ablation).
- `period` in {`pre_T`, `post_T`} — split by the degradation time T.

## Recommended use

- Report the three-level metrics (dialogue / task / agent) from `traces.jsonl`.
- Demonstrate auto-evolution: pre-T retro-test -> post-T recovery; ablation
  `baseline vs local_only vs dual_loop`.
- Check **no regression on previously-correct** cases (`splits.json -> previously_correct_ids`).
- Calibrate an LLM-as-judge on a hand-labelled subset before trusting automated judging.

## Limitations

Synthetic -> limited external validity (numbers illustrate the *method*, not production
performance). Sanctioned cases are rare (~2%), so the missed-check metric has small support — raise
`SANCTION_RATE`. A real open base (German Credit / Home Credit) can be swapped under the agentic
layer for external validity; see `DATASHEET.md`.

## How to cite

After you create a GitHub **Release** from tag `v0.1.0` and archive it on **Zenodo**, a DOI is
minted. Add the DOI badge above and cite as:

> Akhtyamov, R. (2026). *CACE-Bench: A Synthetic Agentic Evaluation Benchmark for LLM
> Credit-Pipeline Agents* (v0.1.0) [Software]. Zenodo. https://doi.org/REPLACE_WITH_DOI

Repository: https://github.com/rav11l/cace-bench

## License

Code: **MIT** (see [`LICENSE`](LICENSE)). Generated synthetic data are released for reuse; if you
need an explicit data license, treat them as CC0-1.0. All data are synthetic; no real personal or
company data are used.
