# Language-model vs seeded proposer — results/shift-llm vs results/shift

| Severity | Family | Proposer | Arm | Runs | Proposed | Admitted | Harmful | Reached oracle | Final FP % | Final miss % | Miss during adaptation % | Worst window % | Excess errors | Oracle admitted in window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mid | thr | LLM | no_gate | 5 | 322 | 22 | 4 | 5/5 | 1.9 | 1.7 | 7.1 | 31.7 | 154 | 1–1 |
| mid | thr | LLM | dual | 5 | 389 | 6 | 0 | 5/5 | 1.9 | 1.7 | 2.0 | 4.5 | 76 | 0–0 |
| mid | thr | seeded | no_gate | 5 | 417 | 12 | 2 | 5/5 | 1.9 | 1.7 | 3.8 | 24.0 | 103 | 0–2 |
| mid | thr | seeded | dual | 5 | 421 | 9 | 0 | 5/5 | 1.9 | 1.7 | 2.0 | 4.5 | 85 | 0–1 |
| mid | scope | LLM | no_gate | 5 | 292 | 32 | 9 | 5/5 | 1.9 | 1.8 | 22.3 | 87.9 | 375 | 3–6 |
| mid | scope | LLM | dual | 5 | 382 | 10 | 0 | 5/5 | 1.9 | 1.8 | 2.0 | 4.7 | 552 | 4–6 |
| mid | scope | seeded | no_gate | 5 | 273 | 31 | 22 | 1/5 | 1.9 | 79.1 | 63.9 | 100.0 | 910 | 5–5 |
| mid | scope | seeded | dual | 5 | 392 | 10 | 0 | 5/5 | 1.9 | 1.8 | 2.0 | 4.7 | 243 | 1–3 |
| mid | struct | LLM | no_gate | 5 | 368 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 70 | 0–0 |
| mid | struct | LLM | dual | 5 | 368 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 70 | 0–0 |
| mid | struct | seeded | no_gate | 5 | 229 | 49 | 36 | 2/5 | 2.0 | 38.0 | 70.3 | 100.0 | 1137 | 5–6 |
| mid | struct | seeded | dual | 5 | 439 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 222 | 2–2 |

Total LLM no_gate: 15 runs, proposed 982, admitted 59, harmful 13, reached oracle 15

Total LLM dual: 15 runs, proposed 1139, admitted 21, harmful 0, reached oracle 15

Total seeded no_gate: 15 runs, proposed 919, admitted 92, harmful 60, reached oracle 8

Total seeded dual: 15 runs, proposed 1252, admitted 24, harmful 0, reached oracle 15

Proposer: {'kind': 'llm', 'max_tokens': 700, 'model': 'claude-haiku-4-5 via session subagent (unpinned)', 'n_examples': 6, 'temperature': None}; stats: {'api_errors': 0, 'cache_hits': 714, 'calls': 714, 'duplicate': 11, 'invalid': 0, 'returned': 2245}
