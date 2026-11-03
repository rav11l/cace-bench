# Preliminary Sol pilot and regression-gate diagnostics

This folder records a synthetic mid-severity pilot, not a product validation or a
pinned API comparison. The original benchmark source at commit
69fdf032e1b0f389f421a3ce56a26e389c186a12 is unchanged.

## Original run

15 cells: thr/scope/struct, seeds 0–4. 499 fresh Codex CLI calls to gpt-6.1-sol,
low effort, isolated ephemeral sessions. Runtime about 38 minutes. Model snapshot
and temperature were not fixed. The original proposer metadata max_tokens=700
belongs to its Anthropic path; this CLI pilot did not enforce that cap.
See manifest.json and PROTOCOL_LIMITATIONS.json. Raw synthetic request journals,
verbatim response cache and cell audit logs are included. The journals are gzip
compressed for archival storage; decompress them to inspect prompts/responses.

Original dual arm: oracle reached 14/15, harmful admissions on H_val 0. Historical
Haiku session run: 15/15 and 0. These unpinned runs do not establish model superiority.

## Findings

In scope/mid/seed4 Sol proposed the exact oracle nine times. The gate rejected it
because 37/6101 previously correct cases regressed (0.606%), above EPS=0.5%.
Haiku reached the identical final harness in two admitted edits (0.410%, 0.172%).
The current gate recomputes the protected set relative to the current harness:
per-step compliance is not a cumulative regression bound.

On 30 frozen cell proposal streams, adding a fixed-H0 regression check eliminated
selection-limit breaches (11 -> 0), but oracle reach dropped to 9/15 for each model.
Two held-out validation breaches remained. This check does not guarantee unseen
data performance.

Noise ablation reached 15/15 for both models. It uses simulator-only information
and is not deployable. All oracle selection regressions occurred on simulated slip
cases; unchanged noisy validation still exceeded the bound in 10/30 cells.

Repeated-execution study uses new independent simulator execution draws and a
majority vote at 1, 5 and 11 repeats. The gate sees vote aggregates, never original
slip flags or an oracle harness. Existing supervised selection labels remain.
At one repeat both models reached 10/15; at 5 and 11, both reached 15/15. Harmful
admissions on original noisy H_val were zero. The original noisy validation bound
was still exceeded in 10/30 cells at 5/11 repeats.

This assumes independent symmetric 2% execution noise, with one draw seed per
scenario. It is not repeated live LLM execution, has no calibrated error guarantee,
and does not cover correlated model errors. Replaying proposals after changing a
gate decision is off-policy: a newly queried proposer could respond differently.

## Reproduce diagnostics (standard-library Python)

Run from the repository root:

```
python experiments/sol-pilot/diagnose_scope.py
python experiments/sol-pilot/check_fixed_baseline.py
python experiments/sol-pilot/check_execution_noise.py
python experiments/sol-pilot/check_repeated_execution.py
```

Original proposal evaluation can be reproduced without model access using the
released combined cache and the same source version. run_pilot.py is the original
live CLI driver with its source location made repository-relative; do not run it
unless fresh paid/account-backed model calls are intended.

## Full pinned run: deferred

The planned 90 synthetic + 90 German Credit cells with
claude-haiku-4-5-20251001, temperature 0, have NOT been run. On 2026-11-03 the user
confirmed no API access and asked to continue without it. Codex authentication is
not substituted for that protocol. When access exists: run one smoke cell, check
model identity/API errors, run both full grids in new result folders, replay from
cache without network calls and compare decompressed cell hashes. Do not overwrite
historical results, alter the paper, or claim completion before these checks pass.

The Cauce shadow integration is a separate observation-only research feature.
No result here authorizes automatic rule changes or lending decisions.
