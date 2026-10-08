# Real-applicant track — 30 runs

## Gate

| Arm | Proposed | Admitted | Harmful (H_val) | Runs with missed flags > 10% |
|---|---|---|---|---|
| dual | 2215 | 89 | 0 | 0 |
| no_gate | 1700 | 219 | 94 | 19 |
| stale_gate | 2919 | 0 | 0 | 0 |
| global_only | 1056 | 0 | 0 | 0 |
| local_only | 1656 | 88 | 0 | 0 |

## Dual loop reached the oracle harness

| Cell | Seeds |
|---|---|
| scope-high | 9/10 |
| scope-low | 10/10 |
| scope-mid | 10/10 |

## Held-out error by subgroup (pooled over runs, 95% Wilson)

| Arm | Group | FP rate | Missed-flag rate |
|---|---|---|---|
| degraded | female | 0.268 [0.262, 0.275] | 0.021 [0.018, 0.023] |
| degraded | male | 0.321 [0.317, 0.326] | 0.017 [0.015, 0.018] |
| degraded | under25 | 0.203 [0.196, 0.211] | 0.020 [0.017, 0.024] |
| degraded | 25plus | 0.324 [0.320, 0.328] | 0.018 [0.016, 0.019] |
| oracle | female | 0.022 [0.020, 0.024] | 0.021 [0.018, 0.023] |
| oracle | male | 0.021 [0.020, 0.022] | 0.017 [0.015, 0.018] |
| oracle | under25 | 0.021 [0.019, 0.024] | 0.020 [0.017, 0.024] |
| oracle | 25plus | 0.021 [0.020, 0.022] | 0.018 [0.016, 0.019] |
| manual | female | 0.022 [0.020, 0.024] | 0.021 [0.018, 0.023] |
| manual | male | 0.021 [0.020, 0.022] | 0.017 [0.015, 0.018] |
| manual | under25 | 0.021 [0.019, 0.024] | 0.020 [0.017, 0.024] |
| manual | 25plus | 0.021 [0.020, 0.022] | 0.018 [0.016, 0.019] |
| no_gate | female | 0.024 [0.022, 0.026] | 0.467 [0.458, 0.476] |
| no_gate | male | 0.029 [0.027, 0.031] | 0.448 [0.443, 0.454] |
| no_gate | under25 | 0.024 [0.021, 0.027] | 0.455 [0.442, 0.468] |
| no_gate | 25plus | 0.028 [0.027, 0.029] | 0.454 [0.449, 0.459] |
| stale_gate | female | 0.268 [0.262, 0.275] | 0.021 [0.018, 0.023] |
| stale_gate | male | 0.321 [0.317, 0.326] | 0.017 [0.015, 0.018] |
| stale_gate | under25 | 0.203 [0.196, 0.211] | 0.020 [0.017, 0.024] |
| stale_gate | 25plus | 0.324 [0.320, 0.328] | 0.018 [0.016, 0.019] |
| dual | female | 0.035 [0.033, 0.038] | 0.021 [0.018, 0.023] |
| dual | male | 0.032 [0.031, 0.034] | 0.017 [0.015, 0.018] |
| dual | under25 | 0.035 [0.032, 0.039] | 0.020 [0.017, 0.024] |
| dual | 25plus | 0.033 [0.031, 0.034] | 0.018 [0.016, 0.019] |

## Gap between groups beyond the oracle's own gap (per run)

| Arm | Pair | Metric | Mean excess gap | Max abs excess gap |
|---|---|---|---|---|
| degraded | female-male | fp | -0.0496 | 0.1537 |
| degraded | female-male | miss | +0.0000 | 0.0000 |
| degraded | under25-25plus | fp | -0.1269 | 0.2713 |
| degraded | under25-25plus | miss | +0.0000 | 0.0000 |
| oracle | female-male | fp | +0.0000 | 0.0000 |
| oracle | female-male | miss | +0.0000 | 0.0000 |
| oracle | under25-25plus | fp | +0.0000 | 0.0000 |
| oracle | under25-25plus | miss | +0.0000 | 0.0000 |
| manual | female-male | fp | +0.0000 | 0.0000 |
| manual | female-male | miss | +0.0000 | 0.0000 |
| manual | under25-25plus | fp | +0.0000 | 0.0000 |
| manual | under25-25plus | miss | +0.0000 | 0.0000 |
| no_gate | female-male | fp | -0.0061 | 0.1103 |
| no_gate | female-male | miss | +0.0124 | 0.2879 |
| no_gate | under25-25plus | fp | -0.0044 | 0.0426 |
| no_gate | under25-25plus | miss | +0.0141 | 0.1295 |
| stale_gate | female-male | fp | -0.0496 | 0.1537 |
| stale_gate | female-male | miss | +0.0000 | 0.0000 |
| stale_gate | under25-25plus | fp | -0.1269 | 0.2713 |
| stale_gate | under25-25plus | miss | +0.0000 | 0.0000 |
| dual | female-male | fp | +0.0015 | 0.0456 |
| dual | female-male | miss | +0.0000 | 0.0000 |
| dual | under25-25plus | fp | +0.0019 | 0.0562 |
| dual | under25-25plus | miss | +0.0000 | 0.0000 |

Oracle harness, realised bad-credit rate: flagged 0.260, cleared 0.348.
Unique applicants per run: pool [700], held-out [300].
