# Language-model vs seeded proposer — C:\Users\ravil_akhtyamov\Documents\Codex\2026-11-02\del-digital-economy-lab-claude-c\work\cace-sol-pilot\results\combined vs C:\Users\ravil_akhtyamov\Claude\Projects\DEL\cace-bench-git\results\shift

| Severity | Family | Proposer | Arm | Runs | Proposed | Admitted | Harmful | Reached oracle | Final FP % | Final miss % | Miss during adaptation % | Worst window % | Excess errors | Oracle admitted in window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mid | thr | LLM | no_gate | 5 | 69 | 21 | 6 | 3/5 | 1.9 | 9.3 | 13.6 | 59.8 | 258 | 0–4 |
| mid | thr | LLM | dual | 5 | 54 | 7 | 0 | 5/5 | 1.9 | 1.7 | 2.0 | 4.5 | 77 | 0–1 |
| mid | thr | seeded | no_gate | 5 | 417 | 12 | 2 | 5/5 | 1.9 | 1.7 | 3.8 | 24.0 | 103 | 0–2 |
| mid | thr | seeded | dual | 5 | 421 | 9 | 0 | 5/5 | 1.9 | 1.7 | 2.0 | 4.5 | 85 | 0–1 |
| mid | scope | LLM | no_gate | 5 | 42 | 10 | 0 | 5/5 | 1.9 | 1.8 | 6.1 | 25.0 | 159 | 0–2 |
| mid | scope | LLM | dual | 5 | 107 | 8 | 0 | 4/5 | 8.9 | 1.8 | 2.0 | 4.7 | 349 | 0–4 |
| mid | scope | seeded | no_gate | 5 | 273 | 31 | 22 | 1/5 | 1.9 | 79.1 | 63.9 | 100.0 | 910 | 5–5 |
| mid | scope | seeded | dual | 5 | 392 | 10 | 0 | 5/5 | 1.9 | 1.8 | 2.0 | 4.7 | 243 | 1–3 |
| mid | struct | LLM | no_gate | 5 | 58 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 70 | 0–0 |
| mid | struct | LLM | dual | 5 | 58 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 70 | 0–0 |
| mid | struct | seeded | no_gate | 5 | 229 | 49 | 36 | 2/5 | 2.0 | 38.0 | 70.3 | 100.0 | 1137 | 5–6 |
| mid | struct | seeded | dual | 5 | 439 | 5 | 0 | 5/5 | 2.0 | 1.8 | 1.9 | 3.3 | 222 | 2–2 |

Total LLM no_gate: 15 runs, proposed 169, admitted 36, harmful 6, reached oracle 13

Total LLM dual: 15 runs, proposed 219, admitted 20, harmful 0, reached oracle 14

Total seeded no_gate: 15 runs, proposed 919, admitted 92, harmful 60, reached oracle 8

Total seeded dual: 15 runs, proposed 1252, admitted 24, harmful 0, reached oracle 15

Proposer: {'kind': 'llm', 'max_tokens': 700, 'model': 'gpt-6.1-sol via Codex CLI isolated sessions (unpinned, low effort)', 'n_examples': 6, 'temperature': None}; stats: {'api_errors': 0, 'cache_hits': 726, 'calls': 726, 'duplicate': 42, 'invalid': 0, 'returned': 470}
