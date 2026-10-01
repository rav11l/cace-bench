# Prospective split

Verdicts issued **before** the outcome exists. The cleanest split in the DeFi track: no
model can have seen how these cases end (METHODOLOGY-DeFi.md §5a).

- `ledger.jsonl` — one public commitment per case: id, chain, T0, horizon, model cutoff,
  SHA-256 of the private record. Appended by `prereg.py commit`; never edited.
- `revealed/<id>.json` — the full record plus the realised outcome, written by
  `prereg.py reveal` after `resolves_on`.
- Private records live **outside the repository** (`--private-dir`). Do not commit them
  before reveal.

The private record carries a random salt, so a short verdict ("NO-GO") cannot be
recovered by hashing candidate answers.

Third-party agents can be registered without disclosing their output or their client's
position until the horizon. Early reveal is possible with `--early` and is flagged in the
revealed file.
