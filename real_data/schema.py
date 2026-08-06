"""Unified credit-application schema (best-effort harmonisation target).

Only German and Taiwan expose labelled features; Australian/Japanese are anonymised.
Extend the maps below as harmonisation is defined for the CACE baseline.
"""
UNIFIED_COLUMNS = [
    "dataset", "target",        # target: 1 = bad/default, 0 = good
    "amount", "term_months", "income", "age", "employment_years", "purpose",
]

# Example column map for German Credit (Statlog) — extend/verify against the UCI card.
GERMAN_MAP = {
    "Attribute5": "amount",         # credit amount
    "Attribute2": "term_months",    # duration in month
    "Attribute13": "age",           # age in years
}
