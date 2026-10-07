# Changelog

All notable changes to CACE-Bench are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

The concept DOI [10.5281/zenodo.21394049](https://doi.org/10.5281/zenodo.21394049) always
resolves to the latest version.

---

## [0.6.0] — 2026-10-07 — Regulatory-shift track

Answers the review of the accompanying paper (ACM ICAIF 2026 submission #103): every number
the revised paper reports is now produced by code in this repository.

### Added
- `evolve.py` — regulatory-shift track. A screening-alert stream with a versioned
  compliance rule; three families of supervisory re-interpretation (threshold, scope,
  structural) at three severities; a dual-loop engine that may change only the runtime
  harness; an admission gate (paired 95% lower bound of improvement > 0, regression on
  previously correct cases ≤ ε = 0.005) evaluated on half of the relabelled pre-shift pool;
  the other half used only to audit admissions; a held-out post-shift window for
  evaluation. Ten arms: healthy, degraded, oracle, manual update, no gate, gate on stale
  labels, global only, local only, compute-matched local only, dual loop.
- Hash-chained, append-only gate log: every admission and rejection is written, with the
  SHA-256 digests of the harness before and after, before anything is deployed;
  `AuditLog.verify()` checks the chain.
- `results/shift/` — 90 runs (9 cells × 10 seeds) with full gate logs for the dual, no-gate
  and global-only arms; `results/shift-eps010/` — tolerance sensitivity.
- `tools/shift_tables.py`, `tools/paper_numbers.py` — tables and the paper's numbers are
  generated from result files, never typed.
- `paper/` — LaTeX source of the revised paper.
- `DATASHEET.md`.
- Reference run replicated on seeds 0–4 (`results/run-seed0.json` … `run-seed4.json`).

### Changed
- `cace_bench.py`: the judge now records missed flags (a truly flaggable case cleared);
  `aggregate()` reports `n_flag`, `miss_count`, `miss_rate` and its Wilson interval; the
  report adds a missed-flag row. Seed-0 headline figures are unchanged.
- `step_correct` is summed with `math.fsum`, so `run-seed*.json` no longer differs in the
  15th digit between Python versions (the earlier "byte-identical" claim held only on one
  interpreter).
- `__version__` corrected: it read 0.3.0 through releases 0.4.0 and 0.4.1.
- README: the section stating that the paper's regulatory-shift figures were not produced
  by this repository is replaced by the track itself; the earlier figures are superseded.
- METHODOLOGY.md: placeholders filled.
- Reports are described as dated, not signed: the word "signed" referred to a text line,
  not a cryptographic signature.

---

## [0.5.0-draft] — DeFi track (draft; first archived as part of 0.6.0)

**No changes to `cace_bench.py`, the credit-track generator, the reference agent, the judge
or the published data.** The DeFi track imports the judge and metrics unchanged.

### Added
- `METHODOLOGY-DeFi.md` — field and outcome mapping (`FLAG`/`CLEAR`/`ESCALATE` read as
  NO-GO / GO / INSUFFICIENT_DATA), DeFi ground-truth rules, splits, labelling protocol,
  model-knowledge-leakage rules (§5a), open questions.
- `defi_track.py` — DeFi generator, `ground_truth_defi`, reference DeFi agent,
  `--check-historical`.
- `configs/defi_sources.json` — source registry: 16 sources, 4 classes, 5 chains; every
  coverage figure unverified.
- `data/defi_historical_v0.json` — 10 historical cases (draft), 2 unscored controls,
  1 prospective slot.
- `rpc.py` — point-in-time reads with citation capsules; archive gaps reported as partial.
- `tools/reconstruct_historical.py` — re-derives H06, H07, H10 facts at `t0_block`.
- `examples/defi_adapter.py` — subprocess adapter for external agents, anonymisation,
  recall probe and model-cutoff gate.
- `prereg.py`, `data/prospective/` — commit-reveal pre-registration of verdicts.

### Known gaps
- Historical facts are draft (read from post-mortems) until reconstructed at `t0_block`.
- No false-negative historical cases yet; thresholds not yet in a versioned config.

---

## [0.4.1] — 2026-08-19

Documentation and metadata release. **No changes to the benchmark, the generator, the
reference agent, the judge or the data.**

### Added
- `CHANGELOG.md` (this file).
- `CITATION.md` — BibTeX entry and explicit guidance on when to use the concept DOI versus
  a version DOI.
- **A section separating this repository's results from the paper's.** The README now
  states plainly that the four-condition regulatory-shift experiment reported in the
  accompanying paper (compliance false-positive rate 23.7% → 5.1%) is *not* produced by the
  code in this repository, and that the reproducible figure here is 22.51% → 4.96% from the
  two-condition auto-evolution ablation. Each figure is attributed to the artefact that can
  actually support it.
- **Documentation for the `real_data/` module**, added in v0.4 but never described in the
  README or reflected in the repository-structure listing.
- License and version badges.

### Fixed
- `.zenodo.json` description opened with "v0.3 adds the data-availability axis…", so the
  published record described the previous version rather than the one being archived.
  Rewritten to describe the archived contents directly, with the reference-run figures and
  the relation to the paper stated explicitly.
- Version strings in `.zenodo.json` and `CITATION.cff` bumped to 0.4.1; `CITATION.cff`
  abstract now mentions the optional public-dataset module.
- Repository-structure listing in the README brought back in line with the actual tree.

### Known gaps
- The regulatory-shift harness and its four-condition protocol are not included; they are
  planned for a later release.
- Provider-coverage numbers in `configs/providers.json` carry a `verified` flag; those
  still `false` have not been confirmed by the provider, and they drive the undecidable
  share and therefore every per-country rate reported.

---

## [0.4.0] — 2026-08-06

### Added
- Optional `real_data/` module: integration of public credit datasets for baseline
  comparison — German Credit, Taiwan default, Australian and Japanese credit, plus Home
  Credit, GiveMeSomeCredit and Lending Club — behind a common column schema. Not
  redistributed; the module reads locally provided copies.

---

## [0.3.0] — 2026-08-03

### Added
- **Data-availability axis.** Cases are drawn per country and each of three source classes
  (open banking, alternative data, sanctions/PEP screening) is resolved by walking that
  country's provider fallback chain from a registry (`configs/providers.json`). Only the
  structure of the registry is used; no provider data enters the benchmark.
- **Consent as a separate gate**, indistinguishable downstream from an unavailable
  provider — both must lead to escalation rather than a guess.
- **Third ground-truth outcome `ESCALATE`** — the correct answer when the facts a decision
  needed were not obtainable. A pipeline that never escalates is now measurably wrong.
- **Provenance tracking.** Citing a provider that did not respond is a separately reported
  error class.
- New metrics: silent-decision rate, provenance completeness, over-escalation rate.
- Reference run at seed 0 on 23,000 synthetic cases, with 95% Wilson confidence intervals
  from genuine counts (`results/REPORT-2026-08-03.md`, `results/run-seed0.json`).

---

## [0.2.0] — 2026-07-27

### Added
- Auto-evolution ablation (self-evolution off vs on) through a deterministic ground-truth
  judge, with a dated reference run (`results/REPORT-2026-07-27.md`,
  `results/run-seed0-v0.2.0.json`).

---

## [0.1.1] — 2026-07-27

### Added
- Zenodo DOI: badge, citation identifiers and release date.

---

## [0.1.0] — 2026-07-06

### Added
- Initial release: synthetic generator, reference agent, deterministic judge, methodology
  and reproducibility documentation, MIT license.
