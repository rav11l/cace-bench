#!/usr/bin/env python3
"""BENCH — the regulatory-shift track with a language-model proposer.

``evolve.py`` proposes harness edits by seeded search over a stated edit space. This
module replaces only the two proposer functions (``local_candidates`` and
``global_candidates``) with calls to a language model; the world, the agent, the gate,
the arms that use a proposer, the audit log and every constant are unchanged.

What the model sees, per call
-----------------------------
* the deployed harness, as the instruction text the audit log records;
* the error cluster that triggered the call (hit type or loan purpose, and whether the
  visible errors are false positives or audited misses), with the window's counts of
  visible errors by cluster;
* up to ``N_EXAMPLES`` cases from that cluster, with the facts the primitive reads;
* the typed edit space: the primitives in the library, the threshold range and the
  admissible scope values.

It never sees ground-truth labels, the rule version, the shift family or severity,
the gate's pool or its statistics. It returns JSON; every candidate is validated
against the typed space, and invalid or duplicate candidates are counted and dropped,
never repaired.

Reproducibility
---------------
On the API path temperature is 0. Every response is stored in a cache keyed by the SHA-256 of
(model, system prompt, user prompt); a later run with the cache present makes no API
calls and reproduces the run exactly. The cache is released with the results.

Running it
----------
The API key is read from the environment variable ``ANTHROPIC_API_KEY`` and is never
written anywhere. Without a key, ``--mock`` replaces the model by a deterministic stub
(for testing the plumbing only; its results mean nothing).

    set ANTHROPIC_API_KEY=...            (Windows: $env:ANTHROPIC_API_KEY="..." in PowerShell)
    python proposer_llm.py --seeds 10 --out results/shift-llm
    python proposer_llm.py --world real --seeds 10 --out results/shift-llm-real

Without API access (out-of-process proposer)
--------------------------------------------
``--queue PATH`` makes no API call: each arm runs until its first cache miss, the missed
prompts are written to PATH, incomplete cells are skipped. Responses produced elsewhere
are added with ``--ingest`` and the pass is repeated until nothing is queued; a final run
without ``--queue`` then replays everything from the cache. ``results/shift-llm`` was
produced this way, with responses from Claude Haiku 4.5 run as isolated sub-agents that
saw only the system and user prompt of one call at a time; the model version and the
sampling temperature were not under our control, so the run is reproducible from the
released cache, not by re-querying the model.

    python proposer_llm.py --seeds 5 --severities mid \
        --model "claude-haiku-4-5 via session subagent (unpinned)" --out results/shift-llm
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request

import evolve as E

__version__ = "0.7.0-dev"

MODEL = "claude-haiku-4-5-20251001"
API_URL = "https://api.anthropic.com/v1/messages"
MAX_TOKENS = 700
N_EXAMPLES = 6
LIBRARY = {
    "direct_stake_check": "applies the threshold to the first-layer value (s1)",
    "effective_stake_check": "applies the threshold to the effective value (eff): s1 "
                             "multiplied by every further factor in the case's chain",
}
# Arms that need a proposer, plus the references they are compared with. The arms that
# differ from 'dual' only in which loops run (global_only, local_only, local_only_cm)
# and the stale-label arm are left to the seeded track to keep the API cost bounded.
ARMS_LLM = ("healthy", "degraded", "oracle", "manual", "no_gate", "dual")

SYSTEM = (
    "You maintain the runtime harness of a compliance-screening agent in a credit "
    "pipeline. The harness is a typed configuration: a primitive from a fixed library, "
    "a numeric threshold, and a set of categories that are in scope. You may change only "
    "these three fields. Operations has reported errors the deployed harness made. "
    "Propose candidate harnesses that you expect to remove the reported errors without "
    "introducing new ones. Every candidate will be tested by an independent gate before "
    "it is deployed; propose distinct candidates, most promising first. Reply with JSON "
    "only, no prose outside the JSON."
)


class Stats:
    calls = 0
    cache_hits = 0
    api_errors = 0
    returned = 0
    invalid = 0
    duplicate = 0


class Cache:
    def __init__(self, path):
        self.path = path
        self.d = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for ln in fh:
                    r = json.loads(ln)
                    self.d[r["key"]] = r["response"]

    def get(self, k):
        return self.d.get(k)

    def put(self, k, prompt_digest, resp):
        self.d[k] = resp
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": k, "prompt_sha256": prompt_digest,
                                 "response": resp}, ensure_ascii=False) + "\n")


CACHE: Cache | None = None
MOCK = False
QUEUE = None          # path: cache misses are queued for an out-of-process proposer
_PENDING = {}         # key -> (system, prompt) queued in this pass
_CELL_PENDING = False
_PENDING_POS = []


class Pending(Exception):
    """A cache miss in --queue mode: the arm stops here and is re-run on the next pass."""


def _call(user: str) -> str:
    key = hashlib.sha256(json.dumps([MODEL, SYSTEM, user]).encode()).hexdigest()
    hit = CACHE.get(key)
    Stats.calls += 1
    if hit is not None:
        Stats.cache_hits += 1
        return hit
    if QUEUE is not None:
        _PENDING[key] = user
        if _CTX["window"]:
            _PENDING_POS.append(_CTX["window"][-1].idx)
        raise Pending(key)
    if MOCK:
        text = _mock(user)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
        if not api_key:
            raise SystemExit("ANTHROPIC_API_KEY is not set (or use --mock)")
        if not api_key.isascii() or any(ch.isspace() for ch in api_key):
            raise SystemExit(f"ANTHROPIC_API_KEY contains spaces or non-Latin characters "
                             f"({len(api_key)} chars) - it holds some other text, not only the key. "
                             f"Copy just the key (sk-ant-api03-...) and set it again.")
        body = json.dumps({"model": MODEL, "max_tokens": MAX_TOKENS, "temperature": 0,
                           "system": SYSTEM,
                           "messages": [{"role": "user", "content": user}]}).encode()
        text = None
        for attempt in range(6):
            req = urllib.request.Request(API_URL, data=body, method="POST", headers={
                "x-api-key": api_key, "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                text = "".join(b.get("text", "") for b in data.get("content", []))
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 529):
                    time.sleep(2 ** attempt)
                    continue
                detail = e.read().decode("utf-8", "replace")[:300]
                if e.code in (401, 403):
                    raise SystemExit(f"API rejected the key (HTTP {e.code}): {detail}\n"
                                     f"Key seen by Python: {len(api_key)} chars, starts {api_key[:7]!r}, "
                                     f"ends ...{api_key[-2:]!r}. Expected 'sk-ant-api03-...' (about 108 chars).")
                raise SystemExit(f"API error HTTP {e.code}: {detail}")
            except (urllib.error.URLError, TimeoutError):
                time.sleep(2 ** attempt)
        if text is None:
            Stats.api_errors += 1
            text = '{"candidates": []}'
    CACHE.put(key, hashlib.sha256(user.encode()).hexdigest(), text)
    return text


def _temperature():
    """0 for the API path; unknown (None) when responses came from an out-of-process proposer."""
    return 0 if MODEL.startswith("claude-") and " " not in MODEL else None


def _mock(user: str) -> str:
    """Deterministic stub for plumbing tests: a few edits in the typed space."""
    r = random.Random(hashlib.sha256(user.encode()).hexdigest())
    spec = json.loads(user.split("EDIT SPACE (JSON):")[1].split("\n\n")[0])
    cur = json.loads(user.split("DEPLOYED HARNESS (JSON):")[1].split("\n\n")[0])
    cands = []
    for _ in range(spec["max_candidates"]):
        c = dict(cur)
        c["theta"] = round(min(0.95, max(0.05, cur["theta"] + r.choice([-0.1, -0.05, 0.05, 0.1, 0.15]))), 2)
        if r.random() < 0.3:
            c["primitive"] = r.choice(spec["primitives"])
        if r.random() < 0.3 and len(cur["scope"]) > 1:
            c["scope"] = sorted(set(cur["scope"]) - {r.choice(cur["scope"])})
        cands.append(c)
    return json.dumps({"candidates": cands})


def _case_facts(c):
    return {"category": c.hit, "s1": round(c.s1, 3), "eff": round(c.eff, 3),
            "chain_length": len(c.stakes)}


# the engine passes no window to the proposers; run_arm sets this before each window
_CTX = {"window": [], "labels": []}


def _prompt(h, cluster, kind, budget, loop):
    obs = []
    for c, y in zip(_CTX["window"], _CTX["labels"]):
        f = E.decide(h, c)
        if f and not y:
            obs.append((c, "false_positive"))
        elif (not f) and y and c.u_audit < E.AUDIT:
            obs.append((c, "audited_miss"))
    counts = {}
    for c, k in obs:
        counts[f"{c.hit}/{k}"] = counts.get(f"{c.hit}/{k}", 0) + 1
    want = "false_positive" if kind == "fp" else "audited_miss"
    ex = [_case_facts(c) for c, k in obs if (cluster is None or c.hit == cluster) and k == want]
    ex = ex[:N_EXAMPLES]
    spec = {"primitives": list(LIBRARY), "theta_range": [0.05, 0.95],
            "scope_values": list(E.HIT_TYPES), "max_candidates": budget,
            "change": ("any field" if loop == "local" else
                       "replace the primitive (the threshold and scope may change too)")}
    cur = json.loads(h.key())
    return (
        f"DEPLOYED HARNESS (TEXT):\n{h.render()}\n\n"
        f"DEPLOYED HARNESS (JSON):{json.dumps(cur)}\n\n"
        f"PRIMITIVE LIBRARY:\n" + "\n".join(f"- {k}: {v}" for k, v in LIBRARY.items()) + "\n\n"
        f"TRIGGER: the {'local' if loop == 'local' else 'global (escalated)'} loop was called for "
        f"{'category ' + cluster if cluster else 'the whole harness'}, error kind {want}.\n\n"
        f"VISIBLE ERRORS IN THE LAST WINDOW OF {len(_CTX['window'])} CASES (every flag is "
        f"reviewed; only {E.AUDIT:.0%} of clears are audited, so most misses are invisible):\n"
        f"{json.dumps(counts, sort_keys=True)}\n\n"
        f"EXAMPLES OF THE TRIGGERING ERRORS (facts the primitive reads):\n{json.dumps(ex)}\n\n"
        f"EDIT SPACE (JSON):{json.dumps(spec)}\n\n"
        f'Return {{"candidates": [{{"primitive": ..., "theta": ..., "scope": [...], '
        f'"rationale": "..."}}]}} with at most {budget} candidates.'
    )


def _parse(text, h, budget):
    try:
        s = text[text.index("{"): text.rindex("}") + 1]
        cands = json.loads(s).get("candidates", [])
    except (ValueError, json.JSONDecodeError, AttributeError):
        Stats.invalid += 1
        return []
    out, seen = [], {h.key()}
    for c in cands[:budget]:
        Stats.returned += 1
        try:
            prim, theta, scope = c["primitive"], float(c["theta"]), c["scope"]
            ok = (prim in LIBRARY and 0.05 <= theta <= 0.95 and isinstance(scope, list)
                  and scope and set(scope) <= set(E.HIT_TYPES))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            Stats.invalid += 1
            continue
        g = E.Harness(prim, round(theta, 2), frozenset(scope))   # render() prints whole percent
        if g.key() in seen:
            Stats.duplicate += 1
            continue
        seen.add(g.key())
        out.append(g)
    return out


def local_candidates(h, hit, kind, rng, budget):
    _CTX["cause"] = (hit, kind)
    return _parse(_call(_prompt(h, hit, kind, budget, "local")), h, budget)


def global_candidates(h, rng, budget):
    # the engine escalates the cluster whose local proposals it has just tried
    hit, kind = _CTX.get("cause", (None, "fp"))
    return _parse(_call(_prompt(h, hit, kind, budget, "global")), h, budget)


def _wrap_run_arm(orig):
    """Expose each window to the proposer without changing the engine's control flow:
    the engine calls observed_errors on the window before any proposer call."""
    def run_arm(arm, cases, family, severity, seed, budget_scale=1):
        orig_obs = E.observed_errors

        def observed_errors(h, window, labels):
            _CTX["window"], _CTX["labels"] = window, labels
            return orig_obs(h, window, labels)
        E.observed_errors = observed_errors
        try:
            return orig(arm, cases, family, severity, seed, budget_scale)
        except Pending:
            global _CELL_PENDING
            _CELL_PENDING = True
            return E.ArmResult(arm, E.H0)     # placeholder; the cell is not written
        finally:
            E.observed_errors = orig_obs
    return run_arm


def install(world):
    global CACHE
    if world == "real":
        import evolve_real
        evolve_real.install()
    E.local_candidates = local_candidates
    E.global_candidates = global_candidates
    E.ARMS = ARMS_LLM
    E.run_arm = _wrap_run_arm(E.run_arm)


def main():
    global CACHE, MOCK, MODEL, QUEUE, _CELL_PENDING
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--world", choices=("synthetic", "real"), default="synthetic")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--families", default="thr,scope,struct")
    ap.add_argument("--severities", default="low,mid,high")
    ap.add_argument("--n", type=int, default=E.N_CASES)
    ap.add_argument("--out", default="results/shift-llm")
    ap.add_argument("--mock", action="store_true", help="deterministic stub instead of the API")
    ap.add_argument("--model", default=MODEL,
                    help="model identifier recorded in the cache key and the results")
    ap.add_argument("--queue", metavar="PATH",
                    help="do not call the API: write cache misses to PATH (JSONL) and skip "
                         "incomplete cells; fill the cache with --ingest and run again")
    ap.add_argument("--ingest", metavar="PATH",
                    help="add responses (JSONL: key, response) to the cache, then exit")
    args = ap.parse_args()
    MODEL = args.model
    MOCK = args.mock
    QUEUE = args.queue
    os.makedirs(args.out, exist_ok=True)
    CACHE = Cache(os.path.join(args.out, "llm_cache.jsonl"))
    if args.ingest:
        n = 0
        with open(args.ingest, encoding="utf-8") as fh:
            for ln in fh:
                r = json.loads(ln)
                resp = r["response"]
                if not isinstance(resp, str):
                    resp = json.dumps(resp, ensure_ascii=False)
                if CACHE.get(r["key"]) is None:
                    CACHE.put(r["key"], r.get("prompt_sha256", ""), resp)
                    n += 1
        print(f"ingested {n} responses into {CACHE.path}")
        return
    install(args.world)
    n_incomplete = 0
    if args.world == "real":
        import evolve_real
        run_cell = evolve_real.run_cell
    else:
        run_cell = E.run_cell
    cells = []
    t0 = time.time()
    for fam in args.families.split(","):
        for sev in args.severities.split(","):
            for s in range(args.seeds):
                path = os.path.join(args.out, f"cell-{fam}-{sev}-seed{s}.json.gz")
                if QUEUE is not None and os.path.exists(path):
                    continue
                _CELL_PENDING = False
                cell = run_cell(s, fam, sev, args.n)
                if _CELL_PENDING:
                    n_incomplete += 1
                    continue
                cell["proposer"] = {"kind": "mock" if MOCK else "llm", "model": MODEL,
                                    "temperature": _temperature()}
                cells.append(cell)
                with gzip.open(path, "wt", encoding="utf-8") as fh:
                    json.dump(cell, fh, sort_keys=True, separators=(",", ":"))
                d, ng = cell["arms"]["dual"], cell["arms"]["no_gate"]
                print(f"{fam:6s} {sev:4s} seed {s}: degraded FP {cell['arms']['degraded']['fp_rate']:.3f}"
                      f" -> dual FP {d['fp_rate']:.3f} miss {d['miss_rate']:.3f} | no-gate FP "
                      f"{ng['fp_rate']:.3f} miss {ng['miss_rate']:.3f} | prop {d['proposed']} adm "
                      f"{d['admitted']} | calls {Stats.calls} (cache {Stats.cache_hits}) "
                      f"invalid {Stats.invalid} | {time.time() - t0:.0f}s", flush=True)
    if QUEUE is not None:
        with open(QUEUE, "w", encoding="utf-8") as fh:
            for k, u in _PENDING.items():
                fh.write(json.dumps({"key": k, "system": SYSTEM, "prompt": u},
                                    ensure_ascii=False) + "\n")
        print(f"queued {len(_PENDING)} prompts; {n_incomplete} cells incomplete; "
              f"{len(cells)} cells written this pass; stream positions "
              f"{sorted(_PENDING_POS)[:1] + sorted(_PENDING_POS)[len(_PENDING_POS)//2:][:1] + sorted(_PENDING_POS)[-1:]}")
        if n_incomplete:
            return
    summary = {"version": __version__, "engine_version": E.__version__, "world": args.world,
               "proposer": {"kind": "mock" if MOCK else "llm", "model": MODEL, "temperature": _temperature(),
                            "max_tokens": MAX_TOKENS, "n_examples": N_EXAMPLES},
               "proposer_stats": {k: getattr(Stats, k) for k in
                                  ("calls", "cache_hits", "api_errors", "returned", "invalid",
                                   "duplicate")},
               "arms": list(ARMS_LLM), "rows": E.summarise(cells)}
    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
