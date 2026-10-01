#!/usr/bin/env python3
"""Reconstruct historical DeFi cases at t0_block from chain state (archive RPC).

Each reconstructor reads only what was observable *before* the incident and derives
the fact the label rests on. Output goes to ``data/reconstructed/<id>.json``:
t0_block, the capsules, the derived fact(s), and whether they agree with the draft
facts in ``data/defi_historical_v0.json``. ``--apply`` writes t0_block and capsules
back into the case file and sets ``status`` to ``reconstructed`` — only for cases
where the derived facts agree. A disagreement is reported, never overwritten.

    export RPC_ETHEREUM=https://eth-mainnet.g.alchemy.com/v2/<KEY>
    export RPC_PROVIDER_ETHEREUM=alchemy_archive
    python tools/reconstruct_historical.py H06 H07 H10
    python tools/reconstruct_historical.py H06 --apply

Thresholds are policy and sit at the top of this file; changing one changes labels.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import rpc  # noqa: E402

HIST = "data/defi_historical_v0.json"
OUT = "data/reconstructed"

# --- policy thresholds ----------------------------------------------------------
ORACLE_DEVIATION_MAX = 0.5        # |implied / reference - 1| above this -> controls unsafe
MIN_VAULT_SHARES = 1_000 * 10**18  # ERC-4626 collateral below this supply is inflatable
MIN_VAULT_AGE_BLOCKS = 7_200       # ~1 day on Ethereum
CONCENTRATION_MAX = 0.25           # one collateral's share of a vault's allocations

# --- identifiers (from public post-mortems; each is re-checked on chain) -------
MORPHO_BLUE = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
CHAINLINK_XAU_USD = "0x214eD9Da11D2fbe465a6fc601a91E62EbEc1a0D6"  # verify on data.chain.link
BORROW_TOPIC = "0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43"

H06_ATTACK_TX = "0x256979ae169abb7fbbbbc14188742f4b9debf48b48ad5b5207cadcc99ccb493b"
H07_ATTACK_TX = "0xffbbd492e0605a8bb6d490c3cd879e87ff60862b0684160d08fd5711e7a872d3"
H07_PAIR = "0x6e90c85a495d54c6d7e1f3400fef1f6e59f86bd6"
H07_VAULT_DEPLOY_TX = "0x852eca15a9fd352817346915f7bc8817d46de349bd7a8fc6ee73c7b66ec9ab41"
# Public "Elixir USDC" vault. Checked 2026-10-01: 100% idle at T0 -> NOT the Stream-lending
# channel. Kept for h10_vault(); the H10 case now targets the Arbitrum xUSD market below.
H10_VAULT = "0x0404fD1a77756EB029F06b5CDea88B2B2ddC2fEE"
H10_T0 = "2025-10-27T00:00:00Z"  # before the first public on-chain analyses (28 Oct)
# Morpho Blue on Arbitrum; USDC/xUSD market found via api.morpho.org on 2026-10-01
# (bad debt reported there: ~$136.9M). Borrower = top borrow position in that API.
ARB_MORPHO_BLUE = "0x6c247b1F6182318877311737BaC0844bAa518F5e"
H10_MARKET = "0x9e90aec7d768403dacc9dd0d8320307fda3f980eed4df43e3e52168a1c667709"
H10_BORROWER = "0x2D9C7Df48725B94A9DE6b2F3174fA4337Fd5551c"  # top borrower TODAY; held ~3% at T0
H10_CREATION_BLOCK = 379403243
BORROWER_SHARE_MAX = 0.5          # one address holding more of a market's debt -> breach

H11_ATTACK_TX = "0xd354a15b15cb73d30908f411aee3f795ec86737a4d080e9a818ac4d6d3014129"
MIN_TIMELOCK_SECONDS = 2 * 24 * 3600


def _symbol(chain: str, token: str, block: int) -> str:
    try:
        raw, _ = rpc.call(chain, token, "symbol", block)
        w = rpc.words(raw)
        if len(w) >= 3:  # dynamic string
            n = int(w[1], 16)
            return bytes.fromhex(w[2])[:n].decode(errors="replace")
        return bytes.fromhex(w[0]).rstrip(b"\0").decode(errors="replace")
    except Exception:  # noqa: BLE001 - symbol is cosmetic
        return token[:10]


def h06(chain: str = "ethereum") -> dict:
    """PAXG/USDC: is the market oracle's implied price sane against a gold reference?"""
    rc = rpc.receipt(chain, H06_ATTACK_TX)
    t0 = rc["capsule"]["block"] - 1
    caps = [rc["capsule"]]
    ids = [lg["topics"][1] for lg in rc["receipt"]["logs"]
           if lg["address"].lower() == MORPHO_BLUE.lower() and lg["topics"][0] == BORROW_TOPIC]
    if not ids:
        raise rpc.RPCError("no Morpho Borrow log in the attack tx")
    mid = ids[0]
    raw, c = rpc.call(chain, MORPHO_BLUE, "idToMarketParams", t0, rpc.enc_bytes32(mid)); caps.append(c)
    w = rpc.words(raw)
    loan, coll, oracle = rpc.as_address(w[0]), rpc.as_address(w[1]), rpc.as_address(w[2])
    raw, c = rpc.call(chain, oracle, "price", t0); caps.append(c)
    price = rpc.as_uint(raw)
    raw, c = rpc.call(chain, loan, "decimals", t0); caps.append(c); dl = rpc.as_uint(raw)
    raw, c = rpc.call(chain, coll, "decimals", t0); caps.append(c); dc = rpc.as_uint(raw)
    implied = price * 10**dc / 10**dl / 10**36
    raw, c = rpc.call(chain, CHAINLINK_XAU_USD, "latestRoundData", t0); caps.append(c)
    reference = rpc.as_uint(rpc.words(raw)[1]) / 1e8
    dev = implied / reference - 1 if reference else float("inf")
    return {"t0_block": t0, "capsules": caps,
            "observed": {"market_id": mid, "oracle": oracle, "loan_decimals": dl,
                         "collateral_decimals": dc, "implied_price": implied,
                         "reference_xau_usd": reference, "deviation": dev},
            "derived": {"controls_safe": abs(dev) <= ORACLE_DEVIATION_MAX}}


def h07(chain: str = "ethereum") -> dict:
    """Resupply: ERC-4626 collateral with negligible supply and a fresh deployment."""
    rc = rpc.receipt(chain, H07_ATTACK_TX)
    t0 = rc["capsule"]["block"] - 1
    caps = [rc["capsule"]]
    raw, c = rpc.call(chain, H07_PAIR, "collateral", t0); caps.append(c)
    vault = rpc.as_address(rpc.words(raw)[0])
    raw, c = rpc.call(chain, vault, "totalSupply", t0); caps.append(c); supply = rpc.as_uint(raw)
    raw, c = rpc.call(chain, vault, "totalAssets", t0); caps.append(c); assets = rpc.as_uint(raw)
    dep = rpc.receipt(chain, H07_VAULT_DEPLOY_TX); caps.append(dep["capsule"])
    age = t0 - dep["capsule"]["block"]
    gate = supply < MIN_VAULT_SHARES or age < MIN_VAULT_AGE_BLOCKS
    return {"t0_block": t0, "capsules": caps,
            "observed": {"vault": vault, "total_supply": supply, "total_assets": assets,
                         "age_blocks": age},
            "derived": {"gate_fail": gate}}


def h10(chain: str = "arbitrum") -> dict:
    """Arbitrum USDC/xUSD market: one borrower's share of total debt at T0."""
    t0 = rpc.block_at(chain, H10_T0)
    caps = []
    raw, c = rpc.call(chain, ARB_MORPHO_BLUE, "market", t0, rpc.enc_bytes32(H10_MARKET)); caps.append(c)
    m = rpc.words(raw)
    tsa, tss, tba, tbs = (rpc.as_uint(m[i]) for i in range(4))
    if tbs == 0:
        raise rpc.RPCError(f"market had no borrows at block {t0}")
    # Candidate addresses = everyone who ever held a position in this market (Morpho API,
    # includes closed positions). Only the ADDRESS SET comes from today's API; every
    # amount below is read on chain AT T0, so no present-day state leaks into the label.
    borrowers, api_cap = morpho_api_position_holders(H10_MARKET, 42161)
    caps.append(api_cap)
    logs = []
    rows = []
    for b in borrowers:
        raw, c = rpc.call(chain, ARB_MORPHO_BLUE, "position", t0,
                          rpc.enc_bytes32(H10_MARKET) + rpc.enc_address(b))
        bs = rpc.as_uint(rpc.words(raw)[1])
        if bs:
            caps.append(c)
            rows.append((bs / tbs, b))
    rows.sort(reverse=True)
    top_share = rows[0][0] if rows else 0.0
    return {"t0_block": t0, "capsules": caps,
            "observed": {"market": H10_MARKET,
                         "total_supply_usdc": tsa / 1e6, "total_borrow_usdc": tba / 1e6,
                         "utilization": round(tba / tsa, 4) if tsa else None,
                         "candidate_addresses": len(borrowers), "borrowers_at_t0": len(rows),
                         "top_borrowers": [{"address": b, "share": round(sh, 6),
                                            "debt_usdc": round(sh * tba / 1e6, 2)} for sh, b in rows[:5]]},
            "derived": {"concentration_breach": top_share > BORROWER_SHARE_MAX}}


MORPHO_API = "https://api.morpho.org/graphql"


def morpho_api_position_holders(market_id: str, chain_id: int) -> tuple[list[str], dict]:
    q = ('query($skip:Int){ marketPositions(first: 1000, skip: $skip, where: '
         '{ marketUniqueKey_in: ["%s"], chainId_in: [%d] }) { items { user { address } } '
         'pageInfo { countTotal } } }') % (market_id, chain_id)
    addrs, skip, pages = set(), 0, []
    while True:
        body = json.dumps({"query": q, "variables": {"skip": skip}}).encode()
        req = urllib.request.Request(MORPHO_API, body, {"Content-Type": "application/json",
                                                        "User-Agent": "cace-bench-rpc/0.5"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
        pages.append(hashlib.sha256(raw).hexdigest())
        data = json.loads(raw)
        if "errors" in data:
            raise rpc.RPCError(f"morpho api: {data['errors'][0].get('message')}")
        mp = data["data"]["marketPositions"]
        addrs |= {i["user"]["address"].lower() for i in mp["items"]}
        skip += 1000
        if skip >= mp["pageInfo"]["countTotal"] or not mp["items"]:
            break
    cap = {"kind": "api", "provider": "morpho_api", "url": MORPHO_API, "query": q,
           "pages_sha256": pages, "addresses": len(addrs),
           "retrieved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
           "note": "address set only; all amounts read on chain at t0_block"}
    return sorted(addrs), cap


def h11(chain: str = "ethereum") -> dict:
    """Term Finance: the timelock (Zodiac Delay txCooldown) as it stood one block before
    execution. Found by probing every contract that emitted a log in the attack tx."""
    rc = rpc.receipt(chain, H11_ATTACK_TX)
    t0 = rc["capsule"]["block"] - 1
    caps = [rc["capsule"]]
    seen, delays = set(), []
    for lg in rc["receipt"]["logs"]:
        a = lg["address"].lower()
        if a in seen:
            continue
        seen.add(a)
        try:
            raw, c = rpc.call(chain, a, "txCooldown", t0)
        except rpc.RPCError:
            continue
        if raw and raw != "0x" and len(raw) >= 66:
            caps.append(c)
            delays.append((a, rpc.as_uint(raw)))
    if not delays:
        raise rpc.RPCError("no contract in the attack tx exposes txCooldown()")
    shortest = min(d for _, d in delays)
    return {"t0_block": t0, "capsules": caps,
            "observed": {"delay_modules": [{"address": a, "txCooldown_s": d} for a, d in delays]},
            "derived": {"controls_safe": shortest >= MIN_TIMELOCK_SECONDS}}


def h10_vault(chain: str = "ethereum") -> dict:
    """Elixir vault: share of allocations by collateral token at T0."""
    t0 = rpc.block_at(chain, H10_T0)
    caps = []
    raw, c = rpc.call(chain, H10_VAULT, "withdrawQueueLength", t0); caps.append(c)
    n = rpc.as_uint(raw)
    by_coll: dict = {}
    for i in range(n):
        raw, c = rpc.call(chain, H10_VAULT, "withdrawQueue", t0, rpc.enc_uint(i)); caps.append(c)
        mid = "0x" + rpc.words(raw)[0]
        raw, c = rpc.call(chain, MORPHO_BLUE, "idToMarketParams", t0, rpc.enc_bytes32(mid)); caps.append(c)
        coll = rpc.as_address(rpc.words(raw)[1])
        raw, c = rpc.call(chain, MORPHO_BLUE, "position", t0,
                          rpc.enc_bytes32(mid) + rpc.enc_address(H10_VAULT)); caps.append(c)
        shares = rpc.as_uint(rpc.words(raw)[0])
        raw, c = rpc.call(chain, MORPHO_BLUE, "market", t0, rpc.enc_bytes32(mid)); caps.append(c)
        m = rpc.words(raw)
        tsa, tss = rpc.as_uint(m[0]), rpc.as_uint(m[1])
        assets = shares * tsa // tss if tss else 0
        by_coll[coll] = by_coll.get(coll, 0) + assets
    zero = "0x" + "0" * 40
    idle = by_coll.pop(zero, 0)  # MetaMorpho idle market: not a collateral exposure
    deployed = sum(by_coll.values())
    if deployed == 0:
        raise rpc.RPCError(f"vault {H10_VAULT} had no deployed allocations at block {t0} "
                           f"(idle only) — wrong vault for this case; find the lending vault")
    shares = sorted(((a / deployed, coll) for coll, a in by_coll.items()), reverse=True)
    top_share, top_coll = shares[0]
    return {"t0_block": t0, "capsules": caps,
            "observed": {"vault": H10_VAULT, "markets": n,
                         "idle_share_of_total": round(idle / (idle + deployed), 4),
                         "allocation": [{"collateral": col, "symbol": _symbol(chain, col, t0)
                                         , "share_of_deployed": round(s, 4)}
                                        for s, col in shares]},
            "derived": {"concentration_breach": top_share > CONCENTRATION_MAX}}


RECON = {"H06": h06, "H07": h07, "H10": h10, "H11": h11}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="+", choices=sorted(RECON))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    doc = json.load(open(HIST, encoding="utf-8"))
    cases = {c["id"]: c for c in doc["cases"]}
    os.makedirs(OUT, exist_ok=True)
    changed = False
    for cid in a.ids:
        try:
            r = RECON[cid]()
        except rpc.RPCError as e:
            print(f"{cid}: RPC error — {e}")
            continue
        draft = cases[cid]["facts"]
        agree = {k: draft.get(k) == v for k, v in r["derived"].items()}
        r["agrees_with_draft"] = agree
        json.dump(r, open(os.path.join(OUT, f"{cid}.json"), "w", encoding="utf-8"), indent=2)
        flag = "OK" if all(agree.values()) else "DISAGREES — review before labelling"
        print(f"{cid}: t0_block={r['t0_block']}  derived={r['derived']}  -> {flag}")
        print(f"     observed={json.dumps(r['observed'], default=str)[:400]}")
        if a.apply and all(agree.values()):
            cases[cid]["t0_block"] = r["t0_block"]
            cases[cid]["status"] = "reconstructed"
            cases[cid].setdefault("sources", {}).setdefault("onchain_state", {})["capsules"] = r["capsules"]
            changed = True
    if changed:
        json.dump(doc, open(HIST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"updated {HIST}")


if __name__ == "__main__":
    main()
