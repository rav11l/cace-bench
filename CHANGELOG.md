# Changelog

All notable changes to CACE-Bench are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

The concept DOI [10.5281/zenodo.21394049](https://doi.org/10.5281/zenodo.21394049) always
resolves to the latest version.

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
