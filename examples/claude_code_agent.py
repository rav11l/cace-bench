#!/usr/bin/env python3
"""Bridge: run a Claude Code-based DeFi risk agent as a BENCH adapter subprocess.

defi_adapter.py writes one JSON request to stdin; this script asks the agent (Claude Code
in non-interactive mode, started in the agent's own repository so its CLAUDE.md, skills
and framework load) for a verdict, and prints one JSON verdict on stdout.

    python examples/defi_adapter.py --n 30 --seed 0 \
        --cmd "python examples/claude_code_agent.py --agent-dir C:/path/to/silk-defi"

    python examples/defi_adapter.py --historical data/defi_historical_v0.json \
        --model-cutoff 2026-06-30 \
        --cmd "python examples/claude_code_agent.py --agent-dir C:/path/to/silk-defi"

Leakage guard (METHODOLOGY-DeFi.md §5a): web tools are disallowed, so the agent cannot
look up how a historical case ended. On-chain reads through the agent's own tools stay
available; give it an RPC that serves the case's t0_block, not "latest", if you want the
historical split to mean what it says.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["GO", "NO-GO", "INSUFFICIENT_DATA"]},
        "controls_verified": {"type": "boolean"},
        "anomaly_basis": {"type": "boolean"},
        "citations": {"type": "object", "additionalProperties": {"type": ["string", "null"]}},
        "rationale": {"type": "string"},
    },
    "required": ["verdict", "controls_verified", "anomaly_basis", "citations"],
}
PROBE_SCHEMA = {"type": "object", "properties": {"incident": {"type": ["string", "null"]}},
                "required": ["incident"]}

VERDICT_PROMPT = """You are being evaluated on BENCH (DeFi track). Apply your own risk framework.

The case below describes a position and, for each source class, whether that source
answered at the decision time (responded / partial / which provider). Rules of the test:
- Return INSUFFICIENT_DATA when a fact your verdict depends on was not obtainable
  (source not responded, or partial). Guessing in that situation is scored as an error.
- controls_verified = true only if oracle configuration and admin controls (timelock,
  multisig, upgradeability) were actually verified from a source that responded.
- anomaly_basis = true if any anomaly you rely on or dismiss is explained with a stated basis.
- citations: claim -> source id, using ONLY provider ids that responded in this case.
- Do not try to identify the protocol or recall what happened to it later.

CASE:
{case}
"""

PROBE_PROMPT = """Without using any tools: does the following description identify a specific
real-world DeFi incident you know of? If yes, name it; if you are not sure, return null.

{case}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-dir", required=True, help="the agent's repository (cwd for claude)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--max-budget-usd", type=float, default=2.0)
    a = ap.parse_args()

    req = json.load(sys.stdin)
    probe = req.get("mode") == "probe"
    case = json.dumps({k: v for k, v in req.items() if k != "mode"}, indent=2, ensure_ascii=False)
    prompt = (PROBE_PROMPT if probe else VERDICT_PROMPT).format(case=case)

    exe = shutil.which("claude") or shutil.which("claude.cmd")
    if not exe:
        sys.exit("claude CLI not found on PATH")
    cmd = [exe, "-p", prompt, "--output-format", "json",
           "--json-schema", json.dumps(PROBE_SCHEMA if probe else SCHEMA),
           "--disallowedTools", "WebSearch", "WebFetch",
           "--max-turns", str(1 if probe else a.max_turns),
           "--max-budget-usd", str(a.max_budget_usd),
           "--no-session-persistence"]
    if probe:
        cmd += ["--tools", ""]
    if a.model:
        cmd += ["--model", a.model]
    p = subprocess.run(cmd, cwd=a.agent_dir, capture_output=True, text=True,
                       encoding="utf-8", timeout=1800)
    if p.returncode != 0:
        sys.exit(f"claude exited {p.returncode}: {p.stderr[-800:]}")
    out = json.loads(p.stdout)
    result = out.get("structured_output")
    if result is None:
        text = out.get("result", "")
        result = json.loads(text[text.find("{"): text.rfind("}") + 1])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
