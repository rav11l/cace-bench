
### thr / mid  (seeds = 10)

| arm | FP % | miss % | recall % | regress. on C_E % | excess adapt. errors | recovery window | proposed | admitted | rejected (no gain / regression) | false adm. (H_val) |
|---|---|---|---|---|---|---|---|---|---|---|
| healthy | 2.0 [1.6, 2.3] | 1.9 [1.6, 2.1] | 98.1 [97.9, 98.4] | 0.0 [0.0, 0.0] | 498 [484, 513] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| degraded | 28.0 [27.3, 28.7] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [484, 513] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| oracle | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 0 [0, 0] | 0.0 | 0 | 0 | 0 / 0 | 0 |
| manual | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 295 [282, 308] | 4.0 | 0 | 0 | 0 / 0 | 0 |
| no_gate | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 139 [83, 194] | 2.5 | 784 | 30 | 754 (trace check) | 6 |
| stale_gate | 28.0 [27.3, 28.7] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [484, 513] | 7.0 | 948 | 0 | 948 / 0 | 0 |
| global_only | 28.0 [27.3, 28.7] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [484, 513] | 7.0 | 360 | 0 | 95 / 265 | 0 |
| local_only | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 81 [70, 93] | 1.3 | 566 | 18 | 516 / 32 | 0 |
| local_only_cm | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 74 [69, 80] | 1.0 | 1519 | 20 | 1470 / 29 | 0 |
| dual | 1.9 [1.6, 2.2] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 82 [71, 93] | 1.3 | 834 | 21 | 774 / 39 | 0 |

### scope / mid  (seeds = 10)

| arm | FP % | miss % | recall % | regress. on C_E % | excess adapt. errors | recovery window | proposed | admitted | rejected (no gain / regression) | false adm. (H_val) |
|---|---|---|---|---|---|---|---|---|---|---|
| healthy | 2.0 [1.6, 2.3] | 1.9 [1.6, 2.1] | 98.1 [97.9, 98.4] | 0.0 [0.0, 0.0] | 780 [763, 797] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| degraded | 36.9 [36.1, 37.7] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.0 [0.0, 0.0] | 780 [763, 797] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| oracle | 2.0 [1.7, 2.2] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.6 [0.5, 0.7] | 0 [0, 0] | 0.0 | 0 | 0 | 0 / 0 | 0 |
| manual | 2.0 [1.7, 2.2] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.6 [0.5, 0.7] | 455 [443, 467] | 4.0 | 0 | 0 | 0 / 0 | 0 |
| no_gate | 2.0 [1.7, 2.2] | 79.7 [51.9, 107.6] | 20.3 [-7.6, 48.1] | 38.1 [24.6, 51.5] | 940 [740, 1139] | 6.9 | 536 | 68 | 468 (trace check) | 50 |
| stale_gate | 36.9 [36.1, 37.7] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.0 [0.0, 0.0] | 780 [763, 797] | 7.0 | 921 | 0 | 921 / 0 | 0 |
| global_only | 36.9 [36.1, 37.7] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.0 [0.0, 0.0] | 780 [763, 797] | 7.0 | 360 | 0 | 99 / 261 | 0 |
| local_only | 3.7 [-0.2, 7.7] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.6 [0.4, 0.7] | 266 [198, 333] | 3.0 | 590 | 19 | 402 / 169 | 0 |
| local_only_cm | 2.0 [1.7, 2.2] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.6 [0.5, 0.7] | 111 [105, 118] | 1.0 | 1306 | 20 | 1231 / 55 | 0 |
| dual | 2.0 [1.7, 2.2] | 1.8 [1.6, 2.1] | 98.2 [97.9, 98.4] | 0.6 [0.5, 0.7] | 236 [199, 274] | 2.8 | 789 | 20 | 612 / 157 | 0 |

### struct / mid  (seeds = 10)

| arm | FP % | miss % | recall % | regress. on C_E % | excess adapt. errors | recovery window | proposed | admitted | rejected (no gain / regression) | false adm. (H_val) |
|---|---|---|---|---|---|---|---|---|---|---|
| healthy | 2.1 [1.7, 2.5] | 1.9 [1.7, 2.2] | 98.1 [97.8, 98.3] | 0.0 [0.0, 0.0] | 498 [475, 521] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| degraded | 27.4 [26.8, 28.0] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [475, 521] | 7.0 | 0 | 0 | 0 / 0 | 0 |
| oracle | 2.0 [1.7, 2.3] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 0 [0, 0] | 0.0 | 0 | 0 | 0 / 0 | 0 |
| manual | 2.0 [1.7, 2.3] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 293 [282, 304] | 4.0 | 0 | 0 | 0 / 0 | 0 |
| no_gate | 2.0 [1.7, 2.3] | 32.7 [11.4, 53.9] | 67.3 [46.1, 88.6] | 16.9 [5.4, 28.4] | 1126 [999, 1252] | 6.8 | 478 | 88 | 390 (trace check) | 63 |
| stale_gate | 27.4 [26.8, 28.0] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [475, 521] | 7.0 | 954 | 0 | 954 / 0 | 0 |
| global_only | 2.0 [1.7, 2.3] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 156 [134, 179] | 2.1 | 43 | 10 | 2 / 31 | 0 |
| local_only | 27.4 [26.8, 28.0] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [475, 521] | 7.0 | 630 | 0 | 0 / 630 | 0 |
| local_only_cm | 27.4 [26.8, 28.0] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.0 [0.0, 0.0] | 498 [475, 521] | 7.0 | 2133 | 0 | 33 / 2100 | 0 |
| dual | 2.0 [1.7, 2.3] | 1.9 [1.6, 2.2] | 98.1 [97.8, 98.4] | 0.3 [0.3, 0.4] | 228 [212, 244] | 3.1 | 878 | 10 | 609 / 259 | 0 |

### Full grid, mean over seeds: FP % / miss %

| family | severity | degraded | no_gate | global_only | local_only | dual | oracle |
|---|---|---|---|---|---|---|---|
| thr | low | 13.1 / 1.9 | 2.0 / 1.9 | 13.1 / 1.9 | 2.0 / 1.9 | 2.0 / 1.9 | 2.0 / 1.9 |
| thr | mid | 28.0 / 1.9 | 1.9 / 1.9 | 28.0 / 1.9 | 1.9 / 1.9 | 1.9 / 1.9 | 1.9 / 1.9 |
| thr | high | 38.0 / 2.0 | 1.9 / 3.1 | 38.0 / 2.0 | 1.9 / 2.0 | 1.9 / 2.0 | 1.9 / 2.0 |
| scope | low | 23.1 / 1.8 | 2.0 / 69.2 | 23.1 / 1.8 | 2.0 / 1.8 | 2.0 / 1.8 | 2.0 / 1.8 |
| scope | mid | 36.9 / 1.8 | 2.0 / 79.7 | 36.9 / 1.8 | 3.7 / 1.8 | 2.0 / 1.8 | 2.0 / 1.8 |
| scope | high | 46.3 / 1.9 | 1.9 / 78.8 | 46.3 / 1.9 | 1.9 / 1.9 | 1.9 / 1.9 | 1.9 / 1.9 |
| struct | low | 18.9 / 1.9 | 2.1 / 36.1 | 2.0 / 1.9 | 18.9 / 1.9 | 2.0 / 1.9 | 2.0 / 1.9 |
| struct | mid | 27.4 / 1.9 | 2.0 / 32.7 | 2.0 / 1.9 | 27.4 / 1.9 | 2.0 / 1.9 | 2.0 / 1.9 |
| struct | high | 34.5 / 1.8 | 2.1 / 48.0 | 18.1 / 1.8 | 34.5 / 1.8 | 18.1 / 1.8 | 2.1 / 1.8 |

### Gate statistics over all cells

- **dual**: {"cells": 90, "proposed": 7449, "admitted": 144, "rejected": {"no_significant_improvement": 5640, "regression_on_C": 1665}, "false_admissions_on_H_val": 0, "escalations": 377, "cells_miss_over_10pct": 0, "logs_verified": true, "max_admitted_per_cell": 4}
- **local_only**: {"cells": 90, "proposed": 5315, "admitted": 111, "rejected": {"no_significant_improvement": 2745, "regression_on_C": 2459}, "false_admissions_on_H_val": 0, "escalations": 0, "cells_miss_over_10pct": 0, "logs_verified": true, "max_admitted_per_cell": 3}
- **global_only**: {"cells": 90, "proposed": 2443, "admitted": 25, "rejected": {"no_significant_improvement": 500, "regression_on_C": 1918}, "false_admissions_on_H_val": 0, "escalations": 418, "cells_miss_over_10pct": 0, "logs_verified": true, "max_admitted_per_cell": 1}
- **stale_gate**: {"cells": 90, "proposed": 8490, "admitted": 0, "rejected": {"no_significant_improvement": 8490}, "false_admissions_on_H_val": 0, "escalations": 480, "cells_miss_over_10pct": 0, "logs_verified": true, "max_admitted_per_cell": 0}
- **no_gate**: {"cells": 90, "proposed": 5353, "admitted": 550, "rejected": {"no_trace_improvement": 4803}, "false_admissions_on_H_val": 309, "escalations": 223, "cells_miss_over_10pct": 49, "logs_verified": true, "max_admitted_per_cell": 13}

### Worked rejection (struct / mid / seed 0, dual loop)

```
{
 "H_sel": {
  "C_regressed": 864,
  "C_regression_rate": 0.12903225806451613,
  "C_size": 6696,
  "gain": 0.0620477965358474,
  "gain_ci": [
   0.054941891200204686,
   0.06915370187149011
  ],
  "improved": 287,
  "improvement_ok": true,
  "n_target": 4561,
  "regression_ok": false,
  "target": "fp",
  "worsened": 4
 },
 "cause": [
  "designation",
  "fp"
 ],
 "decision": "regression_on_C",
 "diff": "scope -designation",
 "h": "95e9db810817305bed33a2551b03c9c9f2c5294fa0af7a2682f739ef614a9cee",
 "h_prime": "cc769fb26601af4ceffbffda032da80d314bdda21bda446832fe1f22b1486e20",
 "h_prime_text": "[direct_stake_check] Flag the applicant if the name hit is one of adverse_media_high, adverse_media_low, pep_domestic, pep_foreign and the stake held through the first-layer vehicle is at least 25%. Otherwise clear.",
 "hash": "0f6978c250794ce9ea2e603e31fb883910c0bfa541725441280c20ac4c6473a4",
 "identity": "gate@bench",
 "loop": "local",
 "prev": "0000000000000000000000000000000000000000000000000000000000000000",
 "seq": 0,
 "t": 16099
}
```
Admitted later:
```
{
 "H_sel": {
  "C_regressed": 21,
  "C_regression_rate": 0.0031362007168458782,
  "C_size": 6696,
  "gain": 0.26266169699627273,
  "gain_ci": [
   0.2495898594443891,
   0.27573353454815636
  ],
  "improved": 1219,
  "improvement_ok": true,
  "n_target": 4561,
  "regression_ok": true,
  "target": "fp",
  "worsened": 21
 },
 "cause": [
  "designation",
  "fp"
 ],
 "decision": "admitted",
 "diff": "primitive direct_stake_check -> effective_stake_check",
 "h": "95e9db810817305bed33a2551b03c9c9f2c5294fa0af7a2682f739ef614a9cee",
 "h_prime": "e8c8091279cf76556f78e717e3d772ee8209ec2ef3bc2472d53510f4570942ea",
 "h_prime_text": "[effective_stake_check] Flag the applicant if the name hit is one of adverse_media_high, adverse_media_low, designation, pep_domestic, pep_foreign and the effective stake, the product of stakes along the ownership chain is at least 25%. Otherwise clear.",
 "hash": "42296978e505226caf076969303bfea9a3b6048025e1d84fc25d6cb39c42c1e7",
 "identity": "gate@bench",
 "loop": "global",
 "prev": "cf5da8092868b046eb8cbcfe7078b650bab3dd48b4c25e4f50a297e58ef4ca1e",
 "seq": 25,
 "t": 17099
}
```
