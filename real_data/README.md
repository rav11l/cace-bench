# CACE-Bench · real-dataset module (optional)

**This module is optional and separate from the fully-synthetic CACE-Bench core.**
The benchmark in [`../cace_bench.py`](../cace_bench.py) needs **no external data** — that
is a deliberate design choice (fully reproducible, no licensing entanglements). This
folder adds an *optional* real-data axis: classic, widely-cited public credit datasets
that can serve as external inputs for a real-data baseline alongside the synthetic run.

Nothing here is committed as data. Only a **downloader** and **loaders** live in the
repo; you fetch the datasets yourself under their own terms.

## Quick start

```bash
cd real_data
pip install -r requirements.txt
python download_data.py --uci      # open UCI datasets, no login
python download_data.py --kaggle   # needs ~/.kaggle/kaggle.json + rules acceptance
python loaders.py                  # sanity-check: prints shapes + bad-rate per dataset
```

Load with a normalised target (`1 = bad/default`, `0 = good`):

```python
from loaders import load_all
frames = load_all()   # {name: DataFrame}
```

Raw data lands in `raw/` and is git-ignored; `checksums.sha256` (written by the
downloader) is what makes a run reproducible.

## Open datasets — UCI ML Repository (no login)

| Dataset | ID | Rows × cols | Target | Notes |
|---|---|---|---|---|
| **Statlog — German Credit** | 144 | 1000 × 20 | good / **bad** | Labelled features; the canonical credit-scoring benchmark. |
| **Default of Credit Card Clients (Taiwan)** | 350 | 30000 × 23 | **default** next month | Labelled features (limit, age, pay history, bill/pay amounts). |
| **Statlog — Australian Credit Approval** | 143 | 690 × 14 | approve / reject | **Anonymised** (features masked) → target-only baseline. |
| **Credit Approval (Japanese, "crx")** | 27 | 690 × 15 | + / − | **Anonymised** (features masked) → target-only baseline. |

Source pages: `archive.ics.uci.edu/dataset/144`, `/dataset/350`, `/dataset/143`,
`/dataset/27`. Normalised in `loaders.py` so **target = 1 = bad/default** across all four.

## Restricted datasets — Kaggle (need your token + rules acceptance)

| Dataset | Kaggle | Size | Target | License / caveat |
|---|---|---|---|---|
| **Home Credit Default Risk** | `c/home-credit-default-risk` | ~2.5 GB, multi-table | default | **Competition rules** — accept once; not an open/commercial licence. |
| **Give Me Some Credit** | `c/GiveMeSomeCredit` | ~7 MB, 150k | 90+ delinquency in 2y | Competition rules — accept once. |
| **Lending Club (2007–2018)** | `d/wordsforthewise/lending-club` | ~1.7 GB | loan status | Community mirror; LC withdrew official downloads — check terms before commercial use. |

> ⚠️ **Licensing.** The Kaggle datasets carry usage restrictions (competition rules /
> mirror terms). Do **not** redistribute them in this repo, and confirm terms before any
> commercial use. That is why only a *downloader* is committed here, not the data.

## Role in the pipeline

These feed a real-data variant of the **Perfilado → Enrutamiento → Decisión** stages as
the "decision under test". The baseline is a standard scorer over each dataset; the
CASE-governed run adds the reasoning trace + independent verifier + audit log that
CACE-Bench measures. Feature harmonisation is meaningful for German and Taiwan (labelled
columns); Australian and Japanese are anonymised and serve only as discrimination
(AUC/error) baselines.

*Business/technical documentation, not legal advice. Verify each dataset's card and
licence before publishing results.*
