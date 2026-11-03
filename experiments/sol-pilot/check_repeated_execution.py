"""Frozen-proposal sensitivity study. Estimator consumes repeat votes, not slip flags."""
import gzip
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1]
sys.path.insert(0, str(SOURCE))
import evolve as E

class SimulatedExecutor:
    """Data-generating mechanism only; common draws across candidate versions.

    Fresh independent execution draws, unrelated to the original case.u_slip.
    No ground truth, oracle or slip flags are exposed to the estimator.
    """
    def __init__(self, cases, seed):
        self.cases = cases
        rng = random.Random(f"repeat-execution-v1:{seed}")
        self.flips = [[rng.random() < E.SLIP for _ in range(11)] for _ in cases]

    def votes(self, harness, repeats):
        result = []
        for case, flips in zip(self.cases, self.flips):
            stake = case.s1 if harness.primitive == "direct_stake_check" else case.eff
            flag = case.hit in harness.scope and stake >= harness.theta - 1e-12
            errors = sum(flips[:repeats])
            result.append(repeats - errors if flag else errors)
        return result

def gate(before, after, baseline, labels, kind):
    b = c = n = reg = size = cumulative = base_size = 0
    for old, new, initial, y in zip(before, after, baseline, labels):
        if old == y:
            size += 1
            reg += new != y
        if initial == y:
            base_size += 1
            cumulative += new != y
        if (kind == "fp" and not y) or (kind == "miss" and y):
            n += 1
            b += old != y and new == y
            c += old == y and new != y
    if not n:
        return False
    gain = (b-c)/n
    se = math.sqrt(max(0, (b+c)/n**2 - (b-c)**2/n**3))
    return (gain - E.Z*se > 0 and reg/max(size,1) <= E.EPS
            and cumulative/max(base_size,1) <= E.EPS)

rows = []
for model, folder in [('Sol', ROOT/'results/combined'), ('Haiku', SOURCE/'results/shift-llm')]:
    for path in sorted(folder.glob('cell-*-mid-seed*.json.gz')):
        with gzip.open(path, 'rt') as f:
            cell = json.load(f)
        cases = E.generate(cell['seed'], cell['family'], cell['severity'], cell['n'])
        selection = [c for c in cases[:cell['T']] if c.idx % 2 == 0]
        validation = [c for c in cases[:cell['T']] if c.idx % 2 == 1]
        labels = [E.truth(c,cell['family'],cell['severity'],'v2') for c in selection]
        vl = [E.truth(c,cell['family'],cell['severity'],'v2') for c in validation]
        executor = SimulatedExecutor(selection, f"{cell['family']}:{cell['seed']}")
        for repeats in (1,5,11):
            cache = {}
            def observed(h):
                key = h.digest()
                if key not in cache:
                    cache[key] = [count > repeats//2 for count in executor.votes(h,repeats)]
                return cache[key]
            current = E.H0
            admitted = harmful = 0
            for rec in cell['arms']['dual']['log']:
                candidate = E._harness_from_text(rec)
                assert candidate.digest() == rec['h_prime']
                if gate(observed(current), observed(candidate), observed(E.H0),labels,rec['cause'][1]):
                    harmful += E._err(candidate, validation, vl) > E._err(current, validation, vl)
                    current = candidate
                    admitted += 1
            reg,size=E.regression(E.H0,current,validation,vl)
            rows.append({'model':model,'family':cell['family'],'seed':cell['seed'],
                         'repeats':repeats,'admitted':admitted,'harmful_on_original_validation':harmful,
                         'oracle_reached':current.digest()==E.oracle_harness(cell['family'],cell['severity']).digest(),
                         'original_validation_regression':reg/max(size,1),
                         'final_harness':json.loads(current.key())})
        print(f"Completed {model} {cell['family']}/{cell['seed']}",flush=True)
summary={}
for model in ('Sol','Haiku'):
    summary[model]={}
    for repeats in (1,5,11):
        group=[r for r in rows if r['model']==model and r['repeats']==repeats]
        summary[model][repeats]={'cells':len(group),'oracle_reached':sum(r['oracle_reached'] for r in group),
            'harmful_on_original_validation':sum(r['harmful_on_original_validation'] for r in group),
            'original_validation_limit_exceeded':sum(r['original_validation_regression']>E.EPS for r in group)}
report={'protocol':'Fresh synthetic execution votes; majority at 1,5,11 repeats; per-step plus fixed-H0 regression <=0.005; unchanged gain confidence bound. Estimator never reads original u_slip or oracle. Ground-truth labels remain the existing supervised selection labels.',
        'limitations':'One repeat-draw seed per scenario; independent symmetric 2% noise assumed by simulator. Frozen proposals after changed decisions are off-policy. No fresh LLM calls; majority vote has no calibrated safety guarantee and correlated LLM errors may persist. Original noisy held-out metrics remain reported.',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'summary':summary,'cells':rows}
(ROOT/'results/repeated-execution-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
