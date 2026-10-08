# Real applicants: Statlog (German Credit Data)

`german.data` is the original file of the Statlog (German Credit Data) set:
1,000 credit applications, 20 attributes and the realised outcome (1 = good, 2 = bad).

- Source: Hofmann, H. (1994). *Statlog (German Credit Data)* [Dataset]. UCI Machine
  Learning Repository. https://doi.org/10.24432/C5NC77
- Licence: CC BY 4.0. Redistributed here unchanged.
- SHA-256: `b21f3d81db8071257d5ff1deaeba1fd4303b62712e6fcc9715c7a86202cb5871`
  (79,793 bytes; checked by `evolve_real.py` at load time).

Attributes used by `evolve_real.py`: 2 (duration), 4 (purpose), 5 (credit amount),
6 (savings), 9 (personal status and sex; A92 = female), 10 (other debtors/guarantors),
13 (age), 21 (outcome, reported only).
