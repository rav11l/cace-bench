# Real-applicant track — 90 runs

## Gate

| Arm | Proposed | Admitted | Harmful (H_val) | Runs with missed flags > 10% |
|---|---|---|---|---|
| dual | 6874 | 171 | 0 | 0 |
| no_gate | 5653 | 539 | 228 | 29 |
| stale_gate | 8769 | 0 | 0 | 0 |
| global_only | 2151 | 29 | 0 | 0 |
| local_only | 5122 | 133 | 0 | 0 |

## Dual loop reached the oracle harness

| Cell | Seeds |
|---|---|
| scope-high | 0/10 |
| scope-low | 10/10 |
| scope-mid | 10/10 |
| struct-high | 10/10 |
| struct-low | 10/10 |
| struct-mid | 10/10 |
| thr-high | 10/10 |
| thr-low | 10/10 |
| thr-mid | 10/10 |

## Held-out error by subgroup (pooled over runs, 95% Wilson)

| Arm | Group | FP rate | Missed-flag rate |
|---|---|---|---|
| degraded | female | 0.225 [0.222, 0.229] | 0.021 [0.020, 0.023] |
| degraded | male | 0.253 [0.250, 0.255] | 0.018 [0.017, 0.019] |
| degraded | under25 | 0.171 [0.167, 0.176] | 0.019 [0.018, 0.022] |
| degraded | 25plus | 0.259 [0.256, 0.261] | 0.019 [0.018, 0.020] |
| oracle | female | 0.021 [0.020, 0.022] | 0.021 [0.020, 0.023] |
| oracle | male | 0.020 [0.020, 0.021] | 0.018 [0.017, 0.019] |
| oracle | under25 | 0.022 [0.020, 0.023] | 0.019 [0.018, 0.022] |
| oracle | 25plus | 0.020 [0.020, 0.021] | 0.019 [0.018, 0.020] |
| manual | female | 0.021 [0.020, 0.022] | 0.021 [0.020, 0.023] |
| manual | male | 0.020 [0.020, 0.021] | 0.018 [0.017, 0.019] |
| manual | under25 | 0.022 [0.020, 0.023] | 0.019 [0.018, 0.022] |
| manual | 25plus | 0.020 [0.020, 0.021] | 0.019 [0.018, 0.020] |
| no_gate | female | 0.022 [0.021, 0.023] | 0.198 [0.194, 0.202] |
| no_gate | male | 0.024 [0.023, 0.025] | 0.189 [0.187, 0.191] |
| no_gate | under25 | 0.023 [0.021, 0.024] | 0.192 [0.186, 0.198] |
| no_gate | 25plus | 0.023 [0.022, 0.024] | 0.192 [0.189, 0.194] |
| stale_gate | female | 0.225 [0.222, 0.229] | 0.021 [0.020, 0.023] |
| stale_gate | male | 0.253 [0.250, 0.255] | 0.018 [0.017, 0.019] |
| stale_gate | under25 | 0.171 [0.167, 0.176] | 0.019 [0.018, 0.022] |
| stale_gate | 25plus | 0.259 [0.256, 0.261] | 0.019 [0.018, 0.020] |
| dual | female | 0.072 [0.070, 0.074] | 0.021 [0.020, 0.023] |
| dual | male | 0.070 [0.069, 0.072] | 0.018 [0.017, 0.019] |
| dual | under25 | 0.075 [0.072, 0.078] | 0.019 [0.018, 0.022] |
| dual | 25plus | 0.070 [0.069, 0.071] | 0.019 [0.018, 0.020] |

## Gap between groups beyond the oracle's own gap (per run)

| Arm | Pair | Metric | Mean excess gap | Max abs excess gap |
|---|---|---|---|---|
| degraded | female-male | fp | -0.0229 | 0.1537 |
| degraded | female-male | miss | +0.0000 | 0.0000 |
| degraded | under25-25plus | fp | -0.0864 | 0.2713 |
| degraded | under25-25plus | miss | +0.0000 | 0.0000 |
| oracle | female-male | fp | +0.0000 | 0.0000 |
| oracle | female-male | miss | +0.0000 | 0.0000 |
| oracle | under25-25plus | fp | +0.0000 | 0.0000 |
| oracle | under25-25plus | miss | +0.0000 | 0.0000 |
| manual | female-male | fp | +0.0000 | 0.0000 |
| manual | female-male | miss | +0.0000 | 0.0000 |
| manual | under25-25plus | fp | +0.0000 | 0.0000 |
| manual | under25-25plus | miss | +0.0000 | 0.0000 |
| no_gate | female-male | fp | -0.0024 | 0.1103 |
| no_gate | female-male | miss | -0.0012 | 0.2879 |
| no_gate | under25-25plus | fp | -0.0018 | 0.0426 |
| no_gate | under25-25plus | miss | -0.0010 | 0.2785 |
| stale_gate | female-male | fp | -0.0229 | 0.1537 |
| stale_gate | female-male | miss | +0.0000 | 0.0000 |
| stale_gate | under25-25plus | fp | -0.0864 | 0.2713 |
| stale_gate | under25-25plus | miss | +0.0000 | 0.0000 |
| dual | female-male | fp | +0.0025 | 0.0843 |
| dual | female-male | miss | +0.0000 | 0.0000 |
| dual | under25-25plus | fp | +0.0046 | 0.1133 |
| dual | under25-25plus | miss | +0.0000 | 0.0000 |

Oracle harness, realised bad-credit rate: flagged 0.268, cleared 0.350.
Unique applicants per run: pool [700], held-out [300].
