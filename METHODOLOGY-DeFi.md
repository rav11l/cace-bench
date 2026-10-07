# [v0.5] DeFi track: same judge, new domain — methodology draft

**Status:** proposal / draft · **Proposed version:** 0.5.0 · **Author:** Anonymous, Anonymous Lab
**Files in this proposal:** `METHODOLOGY-DeFi.md` · `defi_track.py` · `rpc.py` · `prereg.py` · `tools/reconstruct_historical.py` · `examples/defi_adapter.py` · `configs/defi_sources.json` · `data/defi_historical_v0.json` · `data/prospective/`

## TL;DR

BENCH measures whether an agent (a) reaches the right outcome, (b) escalates when the facts were unobtainable instead of guessing, and (c) cites only sources that actually answered. DeFi risk agents fail in exactly these ways. The DeFi track reuses **`judge()`, `aggregate()`, `wilson()`, `diff_ci()` and `_walk_chain()` unchanged**; only the generator, the source registry and `ground_truth_defi()` are new. A working draft reproduces the credit-track shape on 23,000 synthetic DeFi cases and adds a historical split of 13 incidents, 11 of them read from chain state at the block before the event.

The judge is the asset. Nothing in this proposal modifies `bench.py` (verified by hash before and after the run below).

## 1. Why DeFi

Agents that issue GO / NO-GO verdicts on lending markets, curated vaults, LP/PT positions and RWA tokens show the same three failure families the v0.3 axis was built for. Observed in a live DeFi risk agent (anonymised):

| Failure seen in practice | BENCH metric that captures it |
|---|---|
| Confident verdict while the oracle type was only inferred ("heuristic"), admin/timelock unread | **silent-decision rate** |
| Grade F issued with nine open data gaps and no "insufficient data" state | **silent-decision rate** / missing `ESCALATE` |
| "Multiple audits claimed ✓" with no audit among the cited sources | **hallucination rate** |
| Protocol API queried with the zero address; sources cited without block or retrieval time | **provenance completeness** |
| Panic NO-GO on an off-venue price move | **compliance false-positive rate** |

**What DeFi adds that credit cannot:** the "production data" is public. Archive RPC reconstructs state at any past block, so the track can carry a **historical split with realised outcomes** — the external validation the credit track's README lists as not yet done.

## 2. Design: the judge does not change

The DeFi generator emits ordinary `Case` objects. Field names stay as the judge reads them; their meaning is re-read:

| `Case` field (read by `judge`) | DeFi meaning |
|---|---|
| `country` | chain: `ethereum` · `base` · `arbitrum` · `monad` · `solana` |
| `sanctions_hit` | **gate_fail** — a dispositive hard gate fails: exit depth at position size, reflexive backing, manipulable oracle, **structural absence** of backing evidence |
| `pep_match` | **concentration_breach** — top-1 borrower/depositor share, or a depositor↔borrower loop, above threshold with thin health factor |
| `aml_alert` | **anomaly_alert** — non-dispositive anomaly the narrative must explain with a stated basis (reward-APY jump, supply spike, pending change, off-venue dislocation) |
| `kyc_verified` | **controls_safe** — oracle configuration and admin controls (timelock, multisig, upgradeability) verified and within policy |
| `consent` | access — source classes the agent can query (keys, archive); a missing scope behaves like an outage |
| `truth` / `decidable` | as in v0.3 |

| `Narrative` field | DeFi meaning |
|---|---|
| `outcome` | `FLAG` = **NO-GO** · `CLEAR` = **GO** · `ESCALATE` = **INSUFFICIENT_DATA** |
| `claims_kyc_verified` | `claims_controls_verified` |
| `cites_aml_basis` | `cites_anomaly_basis` |
| `cited` | claim → source id. The full *citation capsule* `(chain, block, contract, fn)` or `(url, retrieved_at, sha256)` travels alongside; the judge checks the id only |

Consequence: the seven metrics keep their definitions, their Wilson intervals and their comparability with v0.3.

## 3. Source classes and ground truth

Four classes replace the three credit classes (the judge iterates `case.sources.values()`, so the count is free):

| Class | Contents | Role |
|---|---|---|
| `onchain_state` | positions, HF, utilisation, supply, reserves, oracle addresses (RPC / archive / indexer) | screening-equivalent: without it nothing is decidable |
| `contract_meta` | verified source, oracle config, `getMinDelay`, Safe owners/threshold, upgradeability | strong control verification |
| `offchain_meta` | protocol APIs, docs, curator reports, issuer attestations | weak control verification |
| `market_depth` | live aggregator quotes; **pool reserves at a past block** for the historical split | exit gate |

```
ground_truth_defi(gate_fail, concentration_breach, controls_safe, sources):
  onchain_state missing or partial          -> ESCALATE (undecidable)
  concentration_breach                      -> FLAG     (readable from state alone)
  market_depth missing or partial           -> ESCALATE (exit gate cannot be evaluated)
  gate_fail                                 -> FLAG
  no complete contract_meta / offchain_meta -> ESCALATE
  not controls_safe                         -> FLAG
  otherwise                                 -> CLEAR
```

Two rules are specific to DeFi and should be reviewed before anything else:

1. **Outage vs structural absence.** A source that timed out makes the case undecidable → `ESCALATE`. An issuer that *publishes nothing* is not an outage: the absence is the risk → `gate_fail` → `FLAG`. Without this rule an opaque issuer would escalate forever instead of failing (H09).
2. **A hardcoded price is a control, not a fact.** Pricing collateral at a fixed reference is safe only when par redemption to that reference is open and backing is verifiable. H08 (USDe valued at the USDT feed, redemption open → no bad debt) and H09 (xUSD priced by a feed reporting issuer-side value, no open redemption and no verifiable backing → losses) share the mechanism — a price that does not come from a market — and have opposite outcomes; the pair is in the set on purpose. See §10, 1a.

## 4. Metrics

Unchanged, read in DeFi terms:

| Metric | DeFi reading |
|---|---|
| Silent-decision rate | verdict issued although state, depth or controls were unobtainable |
| Compliance false-positive rate | NO-GO on a position that is GO under the rules (opportunity cost; panic on off-venue prices) |
| Hallucination rate | claims controls verified when they are not (oracle, audits, timelock) |
| Over-escalation rate | INSUFFICIENT_DATA on a decidable case |
| Provenance completeness | every cited source answered (null-address queries and dead endpoints count as not answered) |
| Recovery rate | as in v0.3; requires both ablation arms |
| Step-level correctness | as in v0.3 |

**Supplementary, outside the judge** (reported separately, never folded into headline figures): double-count index (categories penalised by one fact), cluster exposure (issuer / chain / curator), rule calibration on the historical split.

## 5. Splits

| Split | What | Scored by |
|---|---|---|
| `synthetic` | generated populations, `configs/defi_sources.json` | `judge` |
| `historical` | point-in-time incidents, `data/defi_historical_v0.json` | `judge` on `rule_truth`; realised outcome → calibration only |
| `prospective` | verdicts hashed at T0, scored after the horizon | `judge` + calibration |

**Labelling protocol.** `rule_truth = ground_truth_defi(facts, sources)` at `t0_block`, with pre-registered rules. The realised outcome is recorded separately and used only to test whether the rules are right. This keeps the judge deterministic while anchoring the rules to what actually happened.

**Hindsight is the main threat to validity.** Draft `facts` are read from post-mortems. Before a historical case is scored, each fact behind its label is re-derived from chain state at `t0_block` via archive RPC, with one capsule per fact (`tools/reconstruct_historical.py`); a case whose reconstruction disagrees with the draft is reviewed, never overwritten. Cases that cannot be reconstructed keep `status = draft` and are not cited. Reconstruction changed three draft labels' reasons (§7).

### 5a. Model knowledge leakage

The historical split has a second contamination channel, on the agent side: **the LLM inside the agent may already know how the incident ended.** Given "xUSD, curated Morpho vault, 2 Nov 2025", a model trained after November 2025 can return NO-GO from memory, and the benchmark would score recall as risk judgement. The judge cannot detect this — the narrative looks correct.

Rules for any historical run:

1. **Cutoff gate.** Every adapter run declares the model(s) and their training cutoff. A historical case is *eligible* for that run only if `t0 > cutoff`. Cases with `t0 ≤ cutoff` may be run, but are reported in a separate `historical_seen` bucket and never in the headline.
2. **Anonymised presentation.** Eligible or not, cases are shown to the adapter through `anonymize()` (`examples/defi_adapter.py`): token and protocol names replaced by stable pseudonyms, addresses replaced by hashes, dates replaced by relative block offsets. Only state numbers at `t0_block` remain. Anonymisation lowers recall but does not remove it — distinctive numbers (a 20% deposit rate, a 4,000-share vault) still identify cases, which is why rule 1 exists.
3. **Recall probe.** Before scoring, the adapter is asked one question per case with the state withheld: *"Which incident is this?"* Cases the model names correctly are moved to `historical_seen`. The probe result is published with the run.
4. **Prospective split is the clean one.** Verdicts are hashed at T0 (`prereg.py`) and scored after the horizon. No model can have seen the outcome. This split is the one to quote externally.

Reporting: headline figures come from `synthetic` and `prospective`; `historical` (eligible, probe-negative) is reported beside them; `historical_seen` is reported only as a contamination measurement.

## 6. Source registry — `configs/defi_sources.json`

Same structure as `configs/providers.json`, so `_walk_chain` is reused; `countries` is keyed by chain. Sixteen sources across the four classes and five chains. **Every coverage and partial-rate figure is a working assumption (`verified: false`).** Notes worth reviewing:

- `public_rpc` has a high `partial_rate` because it has no archive: historical reads come back partial.
- `archive_pool_reserves` is the only depth source for the historical split — aggregator quotes cannot be replayed.
- `issuer_attestation` coverage is low by design; *structural* absence is modelled as a gate failure, not as coverage.
- `curve_api` gauge fields can return null; the reader must treat that as partial.

## 7. Historical cases

| ID | Incident | T0 | Chain | Rule | Realised | On chain at `t0_block` |
|---|---|---|---|---|---|---|
| H01 | UST / Anchor | 2022-05-06 | ethereum (Curve UST/3CRV) | NO-GO | loss | evidence only — pool balanced (UST 52%), $1M exit 0.09%; the label rests on reflexive backing on Terra, not observable here |
| H02 | stETH discount, Celsius/3AC | 2022-06-10 | ethereum | GO | no loss (365d) | confirmed — $1M exit 2.85% vs 3% threshold; stETH 73% of pool |
| H03 | Mango Markets | 2022-10-10 | solana | NO-GO | loss | draft — no Solana reader |
| H04 | USDC / SVB | 2023-03-09 | ethereum | GO | no loss (30d) | confirmed — 3pool 34/32/34, $1M exit 0.007% |
| H05 | CRV concentration | 2024-06-10 | ethereum | NO-GO | to verify | draft — founder's public address held 0.67% of LlamaLend CRV debt (§10, 1b) |
| H06 | Morpho PAXG/USDC oracle decimals | 2024-10-13 | ethereum | NO-GO | loss | confirmed — oracle 10¹² off Chainlink XAU/USD |
| H07 | Resupply fresh ERC-4626 market | 2025-06-26 | ethereum | NO-GO | loss | confirmed — collateral vault: zero supply, 472 blocks old |
| H08 | USDe single-CEX dislocation | 2025-10-10 | ethereum | GO | no loss | confirmed — Aave priced USDe off "Capped USDT/USD" |
| H09 | xUSD market oracle (re-scoped) | 2025-10-27 | arbitrum | NO-GO | loss | manual label — "xUSD/USD" feed reported issuer-side value 1.248 → 1.262; still 1.266 after the collapse (§10, 1a) |
| H10 | xUSD market concentration (re-scoped) | 2025-10-27 | arbitrum | NO-GO | loss | confirmed — one address 89.1% of debt (not today's sole borrower) |
| H11 | Term Finance removable timelock | 2026-08-23 | ethereum | **GO** | **loss** | confirmed — `txCooldown` = 608,400 s; **false negative of the rules** |
| H12 | Moonwell MAMO spot-priced collateral | 2026-08-26 | base | NO-GO | loss | confirmed — CF 0.5 on a token with $9.2M FDV; oracle ×9.5 before the exploit borrow |
| H13 | Edel wGOOGLx wrapper exchange rate | 2026-06-30 | ethereum | NO-GO | loss (absorbed) | confirmed — 0.12 wrapper shares outstanding; open: rate already 6.0 at T0 |

Plus two **unscored controls** (C01 Euler v1, C02 Balancer v2): code-level exploits outside the observable risk surface, listed so readers see what the track cannot catch. And one **prospective** slot (P01), not yet committed.

**Cutoff gate (§5a).** H11 and H12 have `t0` after 2026-06-30 and are eligible for models with a mid-2026 training cutoff. H13's `t0` (2026-06-30) sits on that boundary: eligible only for models whose cutoff is earlier. Everything before is reported for mid-2026 models only as a contamination measurement.

**Reconstruction status.** 11 of 13 cases were read from chain state at the block before the event, each fact with a capsule (contract, function, block, SHA-256 of the response): 9 labels confirmed by the automatic rules, H09 labelled by hand on recorded evidence, H01 evidence only. H03 and H05 remain drafts. Three draft labels were corrected by reconstruction (H05, H09, H10), and one case (H11) shows the rules failing.

**Worked example of a silent decision — H10.** The first reconstruction of H10 targeted the public "Elixir USDC" vault and returned `OK`: the reconstructor counted the vault's *idle* balance as a collateral and reported 100% concentration. The vault was in fact 100% idle at T0, i.e. not the lending channel at all. The reconstructor now refuses idle-only vaults, the artefact was removed, and H10 was re-scoped to the Arbitrum USDC/xUSD market found through the Morpho API (one borrower holding ~100% of debt; ~$136.9M bad debt reported). A confident verdict on the wrong object, with every number internally consistent, is exactly the failure this benchmark scores — it happened to the benchmark's own tooling first.

The re-scoped H10 then hit a second trap. Today the market has a single borrower holding ~100% of its debt, and the draft label was written from that. Read on chain at T0 (2025-10-27, block 393757551), the market held $26.2M supply / $23.1M debt, and today's sole borrower held only ~3%; a *different* address held 89.1% and closed its position before the collapse. The label survived (concentration was real at T0), but for a reason the draft had wrong. Rule adopted: **API data may supply candidate addresses, never amounts; every amount behind a label is read on chain at `t0_block`.**



## 8. Draft results (smoke test, not a finding)

`python defi_track.py --n 23000 --seed 0` with the reference DeFi agent:

| Metric | Evolution off | Evolution on |
|---|---|---|
| Undecidable share | 16.88% | — |
| Silent-decision rate | 59.71% | 7.26% |
| False-positive rate | 20.03% | 4.51% |
| Hallucination rate | 3.37% | 0.72% |
| Over-escalation rate | 3.59% | 0.44% |
| Provenance completeness | 99.19% | 99.92% |
| Step-level correctness | 88.75% | 97.94% |
| Recovery rate | — | 81.48% |

These numbers are **injected-parameter outputs of a reference agent on an unverified registry**. They show that the pipeline runs end-to-end on the unchanged judge; they say nothing about any real agent.

`python defi_track.py --check-historical data/defi_historical_v0.json` confirms every `rule_truth` is derivable from the recorded facts. Rule calibration (rule verdict × realised outcome): (NO-GO, loss) 8 · (GO, no loss) 3 · **(GO, loss) 1** · (NO-GO, unknown) 1. The separation is no longer perfect: H11 is a loss the rules call GO. That cell is what makes the table informative — a split on which the rules separated perfectly would prove nothing (§5, §10).

## 9. Benchmark your own DeFi agent

Use `examples/defi_adapter.py` (`--demo` for a dry run, `--cmd` to call your agent as a subprocess that reads a JSON case on stdin and prints a JSON verdict). Equivalently, replace `first_pass_defi` (and `recover_defi` if you have a verification loop). Input: a `Case`; do not read `truth` or `decidable`. Output: a `Narrative` with `outcome`, `claims_kyc_verified` (= controls verified), `cites_aml_basis` (= anomaly basis), `cited` (claim → source id). Everything else — population, registry, rules, judge, metrics — is fixed.

## 10. Open questions

1. **False-negative cases.** H11 (Term Finance) is the first: the timelock was 7 days at T0, so the rules return GO, yet a public proposal queued for six days removed it and drained the vault. Proposed rule change for review: *a queued change that lowers a control below policy sets `controls_safe = False`*. At least two more such cases are needed.
1a. **Issuer-reported price feeds (from H09).** The xUSD market was priced by an "xUSD/USD" feed that rose smoothly (1.248 → 1.262 over the 30 days before T0) and still read 1.266 a week after xUSD traded near $0.26. The rule "a hardcoded price is a control only with open par redemption and verifiable backing" should cover any price the issuer reports, not only constants. Until it is extended, H09 carries a manual label with the on-chain evidence attached.
1b. **Concentration by address vs by owner (from H05).** In the LlamaLend CRV market the founder's public address held 0.67% of debt at T0; the reported concentration sat across several wallets and venues. Per-address rules miss it; entity-level rules need address clustering, which brings its own error rate. Open.
2. **Thresholds.** Concentration, exit-depth and timelock thresholds are policy. Proposal: publish them as a versioned config next to the registry, never inside the generator.
3. **Position size.** Exit gates depend on size. Proposal: each case carries size as a fraction of the pool (`size_to_depth`), so a GO at 1% and a NO-GO at 30% of depth are both labelled correctly.
4. **Mandate.** Whether a speculative sleeve is allowed changes the right answer for incentive-only positions. Out of scope for v0.5; noted.
5. **Solana depth history.** No reserve-at-block reader for Solana AMMs in the registry yet; H03 depth is a placeholder.

## 11. Tasks

- [ ] Review the two DeFi-specific rules in §3 (structural absence; hardcode as control)
- [ ] Freeze field mapping and outcome mapping
- [x] Reconstruct at `t0_block` via archive RPC with capsules — 11/13 done (H03: no Solana reader; H05: address vs owner)
- [ ] Verify H05 bad debt, H06 recovery, C02 loss figure
- [ ] Add ≥ 3 false-negative historical cases (1 so far: H11)
- [ ] Verify registry coverage for the providers actually used; flip `verified` per field
- [ ] Thresholds config (`configs/defi_thresholds.json`)
- [x] Recall probe, cutoff gate and anonymisation (names, tx hashes, dates, block offsets) in the adapter (§5a)
- [ ] First external adapter run; results under `results/defi/`
- [x] Hugging Face config `defi`: export script `tools/export_hf_defi.py` (synthetic + historical splits, checked against `run_defi`); upload to the dataset repo pending
- [ ] Zenodo version bump

## 12. Affiliation and conflict of interest

The same disclosure as the credit track applies: the benchmark's author also works on agents of the kind it measures. The historical split is the mitigation — its outcomes are set by the chain, not by the author. Co-defining the case set with external DeFi risk teams is the intended next step.
