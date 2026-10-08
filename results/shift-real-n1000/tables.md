# Real-applicant track — 90 runs

## Gate

| Arm | Proposed | Admitted | Harmful (H_val) | Runs with missed flags > 10% |
|---|---|---|---|---|
| dual | 1639 | 124 | 0 | 0 |
| no_gate | 868 | 241 | 126 | 63 |
| stale_gate | 2469 | 0 | 0 | 0 |
| global_only | 624 | 20 | 0 | 1 |
| local_only | 1349 | 99 | 0 | 0 |

## Dual loop reached the oracle harness

| Cell | Seeds |
|---|---|
| scope-high | 0/10 |
| scope-low | 3/10 |
| scope-mid | 3/10 |
| struct-high | 8/10 |
| struct-low | 2/10 |
| struct-mid | 7/10 |
| thr-high | 7/10 |
| thr-low | 7/10 |
| thr-mid | 9/10 |

## Held-out error by subgroup (pooled over runs, 95% Wilson)

| Arm | Group | FP rate | Missed-flag rate |
|---|---|---|---|
| degraded | female | 0.240 [0.224, 0.258] | 0.016 [0.012, 0.024] |
| degraded | male | 0.264 [0.251, 0.276] | 0.018 [0.015, 0.023] |
| degraded | under25 | 0.159 [0.140, 0.180] | 0.011 [0.006, 0.021] |
| degraded | 25plus | 0.277 [0.266, 0.289] | 0.019 [0.016, 0.023] |
| oracle | female | 0.014 [0.010, 0.020] | 0.016 [0.012, 0.024] |
| oracle | male | 0.028 [0.023, 0.033] | 0.018 [0.015, 0.023] |
| oracle | under25 | 0.008 [0.004, 0.015] | 0.011 [0.006, 0.021] |
| oracle | 25plus | 0.027 [0.023, 0.031] | 0.019 [0.016, 0.023] |
| manual | female | 0.240 [0.224, 0.258] | 0.016 [0.012, 0.024] |
| manual | male | 0.264 [0.251, 0.276] | 0.018 [0.015, 0.023] |
| manual | under25 | 0.159 [0.140, 0.180] | 0.011 [0.006, 0.021] |
| manual | 25plus | 0.277 [0.266, 0.289] | 0.019 [0.016, 0.023] |
| no_gate | female | 0.027 [0.021, 0.035] | 0.390 [0.367, 0.413] |
| no_gate | male | 0.049 [0.044, 0.056] | 0.327 [0.314, 0.340] |
| no_gate | under25 | 0.011 [0.007, 0.019] | 0.403 [0.368, 0.439] |
| no_gate | 25plus | 0.049 [0.043, 0.054] | 0.336 [0.324, 0.349] |
| stale_gate | female | 0.240 [0.224, 0.258] | 0.016 [0.012, 0.024] |
| stale_gate | male | 0.264 [0.251, 0.276] | 0.018 [0.015, 0.023] |
| stale_gate | under25 | 0.159 [0.140, 0.180] | 0.011 [0.006, 0.021] |
| stale_gate | 25plus | 0.277 [0.266, 0.289] | 0.019 [0.016, 0.023] |
| dual | female | 0.075 [0.065, 0.087] | 0.016 [0.012, 0.024] |
| dual | male | 0.101 [0.093, 0.110] | 0.018 [0.015, 0.023] |
| dual | under25 | 0.048 [0.038, 0.062] | 0.011 [0.006, 0.021] |
| dual | 25plus | 0.102 [0.095, 0.110] | 0.019 [0.016, 0.023] |

## Gap between groups beyond the oracle's own gap (per run)

| Arm | Pair | Metric | Mean excess gap | Max abs excess gap |
|---|---|---|---|---|
| degraded | female-male | fp | -0.0087 | 0.2421 |
| degraded | female-male | miss | +0.0000 | 0.0000 |
| degraded | under25-25plus | fp | -0.0967 | 0.3333 |
| degraded | under25-25plus | miss | +0.0000 | 0.0000 |
| oracle | female-male | fp | +0.0000 | 0.0000 |
| oracle | female-male | miss | +0.0000 | 0.0000 |
| oracle | under25-25plus | fp | +0.0000 | 0.0000 |
| oracle | under25-25plus | miss | +0.0000 | 0.0000 |
| manual | female-male | fp | -0.0087 | 0.2421 |
| manual | female-male | miss | +0.0000 | 0.0000 |
| manual | under25-25plus | fp | -0.0967 | 0.3333 |
| manual | under25-25plus | miss | +0.0000 | 0.0000 |
| no_gate | female-male | fp | -0.0088 | 0.1481 |
| no_gate | female-male | miss | +0.0678 | 0.3828 |
| no_gate | under25-25plus | fp | -0.0198 | 0.1515 |
| no_gate | under25-25plus | miss | +0.0705 | 0.4792 |
| stale_gate | female-male | fp | -0.0087 | 0.2421 |
| stale_gate | female-male | miss | +0.0000 | 0.0000 |
| stale_gate | under25-25plus | fp | -0.0967 | 0.3333 |
| stale_gate | under25-25plus | miss | +0.0000 | 0.0000 |
| dual | female-male | fp | -0.0068 | 0.1786 |
| dual | female-male | miss | +0.0000 | 0.0000 |
| dual | under25-25plus | fp | -0.0346 | 0.1951 |
| dual | under25-25plus | miss | +0.0000 | 0.0000 |

Oracle harness, realised bad-credit rate: flagged 0.267, cleared 0.354.
Unique applicants per run: pool [700], held-out [150].
