| Family | Proposer | Arm | Final miss % | Miss during adaptation % | Worst window % | Harmful adm. | Excess errors |
|---|---|---|---|---|---|---|---|
| thr | LLM | no_gate | 1.7 | 7.1 | 31.7 | 4 | 154 |
| thr | LLM | dual | 1.7 | 2.0 | 4.5 | 0 | 76 |
| thr | seeded | no_gate | 1.7 | 3.8 | 24.0 | 2 | 103 |
| thr | seeded | dual | 1.7 | 2.0 | 4.5 | 0 | 85 |
| scope | LLM | no_gate | 1.8 | 22.3 | 87.9 | 9 | 375 |
| scope | LLM | dual | 1.8 | 2.0 | 4.7 | 0 | 552 |
| scope | seeded | no_gate | 79.1 | 63.9 | 100.0 | 22 | 910 |
| scope | seeded | dual | 1.8 | 2.0 | 4.7 | 0 | 243 |
| struct | LLM | no_gate | 1.8 | 1.9 | 3.3 | 0 | 70 |
| struct | LLM | dual | 1.8 | 1.9 | 3.3 | 0 | 70 |
| struct | seeded | no_gate | 38.0 | 70.3 | 100.0 | 36 | 1137 |
| struct | seeded | dual | 1.8 | 1.9 | 3.3 | 0 | 222 |

Proposer: {'kind': 'llm', 'max_tokens': 700, 'model': 'claude-haiku-4-5 via session subagent (unpinned)', 'n_examples': 6, 'temperature': None}; stats: {'api_errors': 0, 'cache_hits': 714, 'calls': 714, 'duplicate': 11, 'invalid': 0, 'returned': 2245}
