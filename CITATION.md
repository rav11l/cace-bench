## How to cite

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21394049.svg)](https://doi.org/10.5281/zenodo.21394049)

If you use CACE-Bench, please cite:

Akhtyamov, R. (2026). *CACE-Bench: A Synthetic Agentic Evaluation Benchmark for LLM Credit-Pipeline Agents* (v0.6.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.21394049

Repository: https://github.com/rav11l/cace-bench

### Which DOI to use

- **`10.5281/zenodo.21394049`** — concept DOI. Always resolves to the latest version. Use this in papers, letters, slides and profile links, so the reference never goes stale.
- **Version DOI** — shown on each individual Zenodo record. Use this only when you need to pin a specific release, for example to reproduce a published result. v0.6.0 = `10.5281/zenodo.23207546`; the full list is in [CITATION.cff](CITATION.cff).

### BibTeX

```bibtex
@software{akhtyamov_cace_bench_2026,
  author    = {Akhtyamov, Ravil},
  title     = {{CACE-Bench: A Synthetic Agentic Evaluation Benchmark
               for LLM Credit-Pipeline Agents}},
  year      = {2026},
  version   = {0.6.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21394049},
  url       = {https://doi.org/10.5281/zenodo.21394049},
  note      = {Repository: \url{https://github.com/rav11l/cace-bench}}
}
```

### Citing the results

**This repository** produces two experiments, each regenerated from the code in one command:

- *Reference run* ([`cace_bench.py`](cace_bench.py)): compliance false-positive rate
  **22.51% → 4.96%** with the missed-flag rate **15.30% → 3.47%** beside it, on 23,000
  synthetic cases, seed 0, registry `2026-08-03`; replicated on seeds 0–4.
- *Regulatory-shift track* ([`evolve.py`](evolve.py), v0.6.0): over 90 runs the gated
  dual loop admitted **144 of 7,449** candidate harness changes with no harmful
  admission; the same loops without the gate admitted **309** harmful changes and left
  missed flags above 10% in **49 of 90** runs.

**The accompanying paper** reports the regulatory-shift track and is built from
[`paper/`](paper/), with every number generated from the result files in this release:

Akhtyamov, R. (2026). *The Harness as the Only Mutable Surface: Compliance-Bounded
Self-Evolution of LLM Agents in Credit Pipelines, with a Measured Admission Gate*.
arXiv:2610.10629. https://arxiv.org/abs/2610.10629

```bibtex
@misc{akhtyamov2026harness,
  author        = {Akhtyamov, Ravil},
  title         = {The Harness as the Only Mutable Surface: Compliance-Bounded Self-Evolution
                   of {LLM} Agents in Credit Pipelines, with a Measured Admission Gate},
  year          = {2026},
  eprint        = {2610.10629},
  archivePrefix = {arXiv},
  url           = {https://arxiv.org/abs/2610.10629}
}
```

arXiv v1 reports the v0.6.0 results; the real-applicant and language-model proposer tracks
added in 0.7.0-dev are not in it.

Figures from an earlier version of that paper (compliance false-positive rate
23.7% → 13.5% → 5.1%) were not produced by code in this repository and are superseded;
do not cite them.

Either way, state that the figure is measured on a **synthetic** benchmark. It is
illustrative of the method, not of production performance.
