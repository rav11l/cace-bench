"""rpc.py — point-in-time on-chain reads for the CACE-Bench DeFi track.

Standard library only, like the rest of the benchmark. Every read returns
(result, capsule): the capsule is what goes into ``Narrative.cited`` evidence and
into the historical case file, so any fact can be re-fetched at the same block.

Configuration (environment variables, never committed):

    RPC_ETHEREUM=https://eth-mainnet.g.alchemy.com/v2/<KEY>
    RPC_BASE=...           RPC_ARBITRUM=...        RPC_MONAD=...
    RPC_PROVIDER_ETHEREUM=alchemy_archive   # id from configs/defi_sources.json

Historical reads need an ARCHIVE node. A non-archive node answers recent blocks
and errors on old ones; that error is reported as ``partial`` so
``ground_truth_defi`` escalates instead of the agent guessing.

    python rpc.py ethereum block-at 2025-11-02T00:00:00Z
    python rpc.py ethereum call 0x<safe> getThreshold --block 23712345
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

# 4-byte selectors for the view calls the rules need. All entries below were checked
# against keccak-256 of the signature; verify any new one with `cast sig "<fn>"`
# (stdlib has no keccak-256).
SELECTORS = {
    "getThreshold": "0xe75235b8",   # Safe
    "getOwners": "0xa0e67e2b",      # Safe
    "getMinDelay": "0xf27a0c92",    # OpenZeppelin TimelockController
    "decimals": "0x313ce567",       # ERC-20
    "totalSupply": "0x18160ddd",    # ERC-20 / ERC-4626 shares
    "totalAssets": "0x01e1d114",    # ERC-4626
    "price": "0xa035b1fe",          # Morpho IOracle.price()
    "symbol": "0x95d89b41",         # ERC-20
    "asset": "0x38d52e0f",          # ERC-4626
    "collateral": "0xd8dfeb45",     # ResupplyPair
    "latestRoundData": "0xfeaf968c",  # Chainlink aggregator
    "idToMarketParams": "0x2c3c9157",  # Morpho Blue (bytes32)
    "market": "0x5c60e39a",          # Morpho Blue (bytes32)
    "position": "0x93c52062",        # Morpho Blue (bytes32,address)
    "withdrawQueueLength": "0x33f91ebb",  # MetaMorpho v1
    "withdrawQueue": "0x62518ddf",        # MetaMorpho v1 (uint256)
}

ARCHIVE_ERRORS = ("missing trie node", "header not found", "state not available",
                  "pruned", "archive", "block not found")


class RPCError(Exception):
    pass


def _endpoint(chain: str) -> tuple[str, str]:
    url = os.environ.get(f"RPC_{chain.upper()}")
    if not url:
        raise RPCError(f"RPC_{chain.upper()} is not set")
    return url, os.environ.get(f"RPC_PROVIDER_{chain.upper()}", "unregistered_rpc")


def rpc(chain: str, method: str, params: list, timeout: float = 20.0):
    url, _ = _endpoint(chain)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError) as e:
        raise RPCError(f"transport: {e}") from e
    if "error" in out:
        raise RPCError(out["error"].get("message", str(out["error"])))
    return out["result"]


def block_at(chain: str, when: str | int) -> int:
    """Last block with timestamp <= ``when`` (ISO-8601 or unix seconds). Binary search."""
    ts = when if isinstance(when, int) else int(
        _dt.datetime.fromisoformat(when.replace("Z", "+00:00")).timestamp())

    def t(n: int) -> int:
        return int(rpc(chain, "eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)

    lo, hi = 0, int(rpc(chain, "eth_blockNumber", []), 16)
    if t(hi) <= ts:
        return hi
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if t(mid) <= ts:
            lo = mid
        else:
            hi = mid - 1
    return lo


def call(chain: str, to: str, fn: str, block: int | str = "latest", args_hex: str = ""):
    """eth_call at a block. Returns (raw_hex, capsule)."""
    _, provider = _endpoint(chain)
    data = SELECTORS.get(fn, fn) + args_hex
    tag = hex(block) if isinstance(block, int) else block
    raw = rpc(chain, "eth_call", [{"to": to, "data": data}, tag])
    capsule = {
        "kind": "rpc", "chain": chain, "block": block, "contract": to, "fn": fn,
        "calldata": data, "provider": provider,
        "result_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "retrieved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    return raw, capsule


def source_state(chain: str, probes: list[tuple[str, str]], block: int | str) -> dict:
    """Run the probes a source class needs and report it the way the benchmark models
    sources: {responded, provider, partial, attempts, capsules}. Archive gaps -> partial."""
    try:
        _, provider = _endpoint(chain)
    except RPCError:
        return {"responded": False, "provider": None, "partial": False, "attempts": []}
    caps, partial = [], False
    for to, fn in probes:
        try:
            caps.append(call(chain, to, fn, block)[1])
        except RPCError as e:
            if any(s in str(e).lower() for s in ARCHIVE_ERRORS):
                partial = True
                continue
            return {"responded": False, "provider": None, "partial": False,
                    "attempts": [provider], "error": str(e)}
    return {"responded": True, "provider": provider, "partial": partial,
            "attempts": [provider], "capsules": caps}


def as_uint(raw: str) -> int:
    return int(raw, 16) if raw and raw != "0x" else 0


def words(raw: str) -> list[str]:
    """Split ABI-encoded return data into 32-byte words (hex, no 0x)."""
    h = raw[2:] if raw.startswith("0x") else raw
    return [h[i:i + 64] for i in range(0, len(h), 64)]


def as_address(word: str) -> str:
    return "0x" + word[-40:]


def enc_uint(n: int) -> str:
    return f"{n:064x}"


def enc_bytes32(h: str) -> str:
    return (h[2:] if h.startswith("0x") else h).rjust(64, "0")


def enc_address(a: str) -> str:
    return a.lower().replace("0x", "").rjust(64, "0")


def receipt(chain: str, tx: str) -> dict:
    """Transaction receipt with a capsule. Block number is the anchor for t0_block."""
    _, provider = _endpoint(chain)
    r = rpc(chain, "eth_getTransactionReceipt", [tx])
    if r is None:
        raise RPCError(f"receipt not found: {tx}")
    cap = {"kind": "rpc", "chain": chain, "fn": "eth_getTransactionReceipt", "tx": tx,
           "block": int(r["blockNumber"], 16), "provider": provider,
           "result_sha256": hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest(),
           "retrieved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    return {"receipt": r, "capsule": cap}


if __name__ == "__main__":
    chain, cmd, *rest = sys.argv[1:] or ["", ""]
    if cmd == "block-at":
        print(block_at(chain, rest[0]))
    elif cmd == "call":
        blk = int(rest[rest.index("--block") + 1]) if "--block" in rest else "latest"
        raw, cap = call(chain, rest[0], rest[1], blk)
        print(as_uint(raw) if len(raw) <= 66 else raw)
        print(json.dumps(cap, indent=2))
    else:
        print(__doc__)
