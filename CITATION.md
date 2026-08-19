## How to cite

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21394049.svg)](https://doi.org/10.5281/zenodo.21394049)

If you use CACE-Bench, please cite:

Akhtyamov, R. (2026). *CACE-Bench: A Synthetic Agentic Evaluation Benchmark for LLM Credit-Pipeline Agents* (v0.4.1) [Software]. Zenodo. https://doi.org/10.5281/zenodo.21394049

Repository: https://github.com/rav11l/cace-bench

### Which DOI to use

- **`10.5281/zenodo.21394049`** — concept DOI. Always resolves to the latest version. Use this in papers, letters, slides and profile links, so the reference never goes stale.
- **Version DOI** — shown on each individual Zenodo record. Use this only when you need to pin a specific release, for example to reproduce a published result.

### BibTeX

```bibtex
@software{akhtyamov_cace_bench_2026,
  author    = {Akhtyamov, Ravil},
  title     = {{CACE-Bench: A Synthetic Agentic Evaluation Benchmark
               for LLM Credit-Pipeline Agents}},
  year      = {2026},
  version   = {0.4.1},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21394049},
  url       = {https://doi.org/10.5281/zenodo.21394049},
  note      = {Repository: \url{https://github.com/rav11l/cace-bench}}
}
```

### Citing the results — two different experiments

**This repository.** The reference run in [results/](results/) is the two-condition
auto-evolution ablation produced by [`cace_bench.py`](cace_bench.py): compliance
false-positive rate **22.51% → 4.96%** (−77.9% relative) on 23,000 synthetic cases at
seed 0, registry `2026-08-03`. Cite the software record above for this figure — it
regenerates from the code in one command.

**The accompanying paper.** A different experiment, whose harness is not part of this
release:

Akhtyamov, R. (2026). *Compliance-Bounded Self-Evolution of LLM Agents in Regulated Credit Pipelines: A Dual-Loop Harness Architecture with Three-Level Quality Metrics*.

It simulates a regulatory re-interpretation at the 70% mark of the stream and compares
four conditions; there the compliance false-positive rate recovers from **23.7% to 5.1%**
(−78% relative), counted over ~23,000 labelled trace steps for 3,000 applications. Cite
the paper for that figure, not this repository.

Either way, state that the figure is measured on a **synthetic** benchmark. It is
illustrative of the method, not of production performance.
