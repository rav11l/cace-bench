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
# H12 Moonwell (Base): a borrow by "Moonwell Exploiter 1" (Basescan label), block 50516532.
H12_EXPLOIT_TX = "0xafb6f0fa257b115a5c813bf787b4c1535e63888b1d0dbeb1f3788f557f51798f"
H12_T0 = "2026-08-26T00:00:00Z"
MIN_COLLATERAL_FDV_USD = 50_000_000   # collateral whose whole supply is worth less is "thin"
# H13 Edel (Ethereum): tx reported as the exploit (cryptotimes, 2026-07-01) — verify.
H13_EXPLOIT_TX = "0xe2320086b2815d21b0927839bd0e306466c29a68d38d5361e99dd21ec5472612"
H13_T0 = "2026-06-30T00:00:00Z"
# H05 CRV: LlamaLend factory (verify on docs.curve.finance) and Egorov's public address.
LLAMALEND_FACTORY = "0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0"
CRV = "0xD533a949740bb3306d119CC777fa900bA034cd52"
EGOROV = "0x7a16fF8270133F063aAb6C9977183D9e72835428"
H05_T0 = "2024-06-10T00:00:00Z"
# H08 USDe: Aave V3 oracle on Ethereum and the Chainlink USDT/USD aggregator proxy.
AAVE_ORACLE = "0x54586bE62E3c3580375aE3723C145253060Ca0C2"
USDE = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"
H08_T0 = "2025-10-10T00:00:00Z"
# H09 xUSD: the oracle of the Arbitrum USDC/xUSD market (same market as H10).
H09_ORACLE = "0x1837efFC34Bb5a96EFdA00d53560799bE3a4226E"
H09_T0 = "2025-10-27T00:00:00Z"
# H01/H02/H04: exit depth through the deepest Curve pool at T0, for a fixed position size.
EXIT_SIZE_USD = 1_000_000
MAX_EXIT_DISCOUNT = 0.03          # losing more than 3% to exit at that size fails the gate
CURVE_3POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"      # DAI/USDC/USDT
CURVE_STETH = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"      # ETH/stETH
CURVE_UST_WH = "0xCEAF7747579696A2F0bb206a14210e3c9e6fB269"     # UST(Wormhole)/3CRV
H01_T0, H02_T0, H04_T0 = "2022-05-06T00:00:00Z", "2022-06-10T00:00:00Z", "2023-03-09T00:00:00Z"
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
                                                        "User-Agent": "bench-rpc/0.5"})
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


def _try(chain, to, fn, block, args=""):
    try:
        return rpc.call(chain, to, fn, block, args)
    except rpc.RPCError:
        return None, None


def h12(chain: str = "base") -> dict:
    """Moonwell MAMO: was a thin, spot-priced token accepted as collateral at T0?
    Comptroller and oracle are discovered from the exploit tx; amounts read at T0."""
    rc = rpc.receipt(chain, H12_EXPLOIT_TX)
    b_exploit = rc["capsule"]["block"]
    t0 = rpc.block_at(chain, H12_T0)
    caps = [rc["capsule"]]
    comp = None
    for lg in rc["receipt"]["logs"]:
        raw, c = _try(chain, lg["address"], "comptroller", t0)
        if raw and len(raw) >= 66:
            comp = rpc.as_address(rpc.words(raw)[0]); caps.append(c); break
    if not comp:
        raise rpc.RPCError("no mToken with comptroller() among the exploit tx logs")
    raw, c = rpc.call(chain, comp, "oracle", t0); caps.append(c)
    oracle = rpc.as_address(rpc.words(raw)[0])
    raw, c = rpc.call(chain, comp, "getAllMarkets", t0); caps.append(c)
    w = rpc.words(raw)
    markets = [rpc.as_address(x) for x in w[2:2 + int(w[1], 16)]]
    target = None
    for m in markets:
        if "MAMO" in _symbol(chain, m, t0).upper():
            target = m; break
    if not target:
        raise rpc.RPCError(f"no MAMO market listed at block {t0}")
    raw, c = rpc.call(chain, comp, "markets", t0, rpc.enc_address(target)); caps.append(c)
    mw = rpc.words(raw)
    listed, cf = rpc.as_uint(mw[0]) == 1, rpc.as_uint(mw[1]) / 1e18
    raw, c = rpc.call(chain, target, "underlying", t0); caps.append(c)
    mamo = rpc.as_address(rpc.words(raw)[0])
    raw, c = rpc.call(chain, mamo, "decimals", t0); caps.append(c); dec = rpc.as_uint(raw)
    raw, c = rpc.call(chain, mamo, "totalSupply", t0); caps.append(c); supply = rpc.as_uint(raw) / 10**dec
    raw, c = rpc.call(chain, oracle, "getUnderlyingPrice", t0, rpc.enc_address(target)); caps.append(c)
    p0 = rpc.as_uint(raw) / 10**(36 - dec)
    raw, _ = rpc.call(chain, oracle, "getUnderlyingPrice", b_exploit - 1, rpc.enc_address(target))
    p_pre = rpc.as_uint(raw) / 10**(36 - dec)
    fdv = supply * p0
    return {"t0_block": t0, "capsules": caps,
            "observed": {"comptroller": comp, "oracle": oracle, "mMAMO": target, "MAMO": mamo,
                         "listed": listed, "collateral_factor": cf, "price_t0": p0,
                         "fdv_t0_usd": round(fdv), "post_t0_evidence":
                         {"price_block_before_exploit_borrow": p_pre,
                          "price_ratio": round(p_pre / p0, 2) if p0 else None}},
            "derived": {"gate_fail": listed and cf > 0 and fdv < MIN_COLLATERAL_FDV_USD}}


def h13(chain: str = "ethereum") -> dict:
    """Edel: collateral valued through a wrapper exchange rate. Finds the ERC-4626-style
    wrapper among the exploit tx logs and reads its supply and rate at T0."""
    rc = rpc.receipt(chain, H13_EXPLOIT_TX)
    b = rc["capsule"]["block"]
    t0 = rpc.block_at(chain, H13_T0)
    caps = [rc["capsule"]]
    found = []
    for a in sorted({lg["address"].lower() for lg in rc["receipt"]["logs"]}):
        raw, c = _try(chain, a, "convertToAssets", t0, rpc.enc_uint(10**18))
        if not raw or len(raw) < 66:
            continue
        sym = _symbol(chain, a, t0)
        r0 = rpc.as_uint(raw)
        sraw, sc = _try(chain, a, "totalSupply", t0)
        raw_b, _ = _try(chain, a, "convertToAssets", b, rpc.enc_uint(10**18))
        caps += [c] + ([sc] if sc else [])
        found.append({"address": a, "symbol": sym, "rate_t0": r0 / 1e18,
                      "total_supply_t0": rpc.as_uint(sraw) if sraw else None,
                      "post_t0_evidence": {"rate_after_exploit_tx":
                                           rpc.as_uint(raw_b) / 1e18 if raw_b else None}})
    if not found:
        raise rpc.RPCError("no ERC-4626-style wrapper among the exploit tx logs — check the tx hash")
    g = [f for f in found if "GOOG" in f["symbol"].upper()] or found
    w = g[0]
    thin = w["total_supply_t0"] is not None and w["total_supply_t0"] < MIN_VAULT_SHARES
    return {"t0_block": t0, "capsules": caps, "observed": {"wrappers": found},
            "derived": {"gate_fail": thin}}


def h05(chain: str = "ethereum") -> dict:
    """CRV: one borrower's share of debt in LlamaLend CRV-collateral markets at T0."""
    t0 = rpc.block_at(chain, H05_T0)
    caps = []
    raw, c = rpc.call(chain, LLAMALEND_FACTORY, "market_count", t0); caps.append(c)
    rows = []
    for i in range(rpc.as_uint(raw)):
        raw, c = rpc.call(chain, LLAMALEND_FACTORY, "collateral_tokens", t0, rpc.enc_uint(i))
        if rpc.as_address(rpc.words(raw)[0]).lower() != CRV.lower():
            continue
        caps.append(c)
        raw, c = rpc.call(chain, LLAMALEND_FACTORY, "controllers", t0, rpc.enc_uint(i)); caps.append(c)
        ctl = rpc.as_address(rpc.words(raw)[0])
        raw, c = rpc.call(chain, ctl, "total_debt", t0); caps.append(c); tot = rpc.as_uint(raw)
        raw, c = rpc.call(chain, ctl, "debt", t0, rpc.enc_address(EGOROV)); caps.append(c); mine = rpc.as_uint(raw)
        rows.append({"controller": ctl, "total_debt": tot / 1e18, "borrower_debt": mine / 1e18,
                     "borrower_share": round(mine / tot, 4) if tot else None})
    if not rows:
        raise rpc.RPCError("no CRV-collateral LlamaLend market found — check LLAMALEND_FACTORY")
    top = max((r["borrower_share"] or 0) for r in rows)
    return {"t0_block": t0, "capsules": caps, "observed": {"borrower": EGOROV, "markets": rows},
            "derived": {"concentration_breach": top > BORROWER_SHARE_MAX}}


def h08(chain: str = "ethereum") -> dict:
    """USDe on Aave: is the collateral priced off the USDT feed (a peg control) at T0?"""
    t0 = rpc.block_at(chain, H08_T0)
    caps = []
    raw, c = rpc.call(chain, AAVE_ORACLE, "getSourceOfAsset", t0, rpc.enc_address(USDE)); caps.append(c)
    src = rpc.as_address(rpc.words(raw)[0])
    # The label rests on this reading, so it gets its own capsule, with the decoded text.
    raw, c = rpc.call(chain, src, "description", t0)
    w = rpc.words(raw)
    desc = bytes.fromhex("".join(w[2:]))[:int(w[1], 16)].decode(errors="replace")
    c["decoded"] = desc
    caps.append(c)
    raw, c = rpc.call(chain, AAVE_ORACLE, "getAssetPrice", t0, rpc.enc_address(USDE)); caps.append(c)
    price = rpc.as_uint(raw) / 1e8
    pegged = "USDT" in desc.upper()
    return {"t0_block": t0, "capsules": caps,
            "observed": {"source": src, "source_description": desc, "usde_price_usd": price},
            "derived": {"controls_safe": pegged}}


def h09(chain: str = "arbitrum") -> dict:
    """xUSD: does the market oracle price xUSD from any feed or vault, or is it a constant?"""
    t0 = rpc.block_at(chain, H09_T0)
    caps, cfg = [], {}
    for fn in ("BASE_FEED_1", "BASE_FEED_2", "QUOTE_FEED_1", "QUOTE_FEED_2", "BASE_VAULT", "QUOTE_VAULT"):
        raw, c = rpc.call(chain, H09_ORACLE, fn, t0); caps.append(c)
        cfg[fn] = rpc.as_address(rpc.words(raw)[0])
    zero = "0x" + "0" * 40
    raw, c = rpc.call(chain, H09_ORACLE, "price", t0); caps.append(c)
    oracle_price = rpc.as_uint(raw)
    feeds = [cfg[k] for k in ("BASE_FEED_1", "BASE_FEED_2") if cfg[k] != zero]
    feed_info = []
    constant = not feeds and cfg["BASE_VAULT"] == zero
    if feeds:
        # A feed that never moved over the 30 days before T0 and reports exactly 1.0 is a
        # constant in disguise. Both readings are pre-T0, so this is observable at T0.
        t_prev = rpc.block_at(chain, "2025-09-27T00:00:00Z")
        all_flat = True
        for f in feeds:
            desc = _symbol_like(chain, f, "description", t0)
            raw, c = rpc.call(chain, f, "decimals", t0); caps.append(c); dec = rpc.as_uint(raw)
            raw, c = rpc.call(chain, f, "latestRoundData", t0); caps.append(c); w0 = rpc.words(raw)
            pr, cp = _try(chain, f, "latestRoundData", t_prev)
            w1 = rpc.words(pr) if pr else None
            a0 = rpc.as_uint(w0[1]) / 10**dec
            a1 = rpc.as_uint(w1[1]) / 10**dec if w1 else None
            flat = a1 is not None and a0 == a1 == 1.0 and w0[0] == w1[0]
            all_flat &= flat
            if cp:
                caps.append(cp)
            post, _ = _try(chain, f, "latestRoundData", rpc.block_at(chain, "2025-11-06T00:00:00Z"))
            feed_info.append({"feed": f, "description": desc, "answer_t0": a0,
                              "answer_30d_before": a1, "round_id_unchanged": bool(w1) and w0[0] == w1[0],
                              "updated_at_t0": rpc.as_uint(w0[3]),
                              "post_t0_evidence": {"answer_2025_11_06":
                                                   rpc.as_uint(rpc.words(post)[1]) / 10**dec if post else None}})
        constant = all_flat
    return {"t0_block": t0, "capsules": caps,
            "observed": {"oracle": H09_ORACLE, "config": cfg, "price_raw": str(oracle_price),
                         "feeds": feed_info, "xusd_priced_by_constant": constant},
            "derived": {"controls_safe": not constant}}


def _symbol_like(chain, to, fn, block) -> str:
    try:
        raw, _ = rpc.call(chain, to, fn, block)
        w = rpc.words(raw)
        n = int(w[1], 16)
        return bytes.fromhex("".join(w[2:]))[:n].decode(errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _curve_exit(chain, pool, i, j, dx, block, caps):
    """Amount of coin j received for dx of coin i, plus pool balances, at a block."""
    raw, c = rpc.call(chain, pool, "get_dy", block, rpc.enc_uint(i) + rpc.enc_uint(j) + rpc.enc_uint(dx))
    caps.append(c)
    out = rpc.as_uint(raw)
    bals = []
    for k in range(4):
        r, c = _try(chain, pool, "balances", block, rpc.enc_uint(k))
        if not r:
            r, c = _try(chain, pool, "balances_i128", block, rpc.enc_uint(k))
        if not r:
            break
        caps.append(c)
        bals.append(rpc.as_uint(r))
    return out, bals


def _coin_meta(chain, pool, k, block, caps):
    raw, c = rpc.call(chain, pool, "coins", block, rpc.enc_uint(k)); caps.append(c)
    a = rpc.as_address(rpc.words(raw)[0])
    if a.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
        return a, "ETH", 18
    raw, c = rpc.call(chain, a, "decimals", block); caps.append(c)
    return a, _symbol(chain, a, block), rpc.as_uint(raw)


def h04(chain: str = "ethereum") -> dict:
    """USDC before SVB: exit depth for $1M USDC -> DAI through the Curve 3pool at T0."""
    t0 = rpc.block_at(chain, H04_T0); caps = []
    _, s_in, d_in = _coin_meta(chain, CURVE_3POOL, 1, t0, caps)
    _, s_out, d_out = _coin_meta(chain, CURVE_3POOL, 0, t0, caps)
    out, bals = _curve_exit(chain, CURVE_3POOL, 1, 0, EXIT_SIZE_USD * 10**d_in, t0, caps)
    disc = 1 - (out / 10**d_out) / EXIT_SIZE_USD
    norm = [bals[0] / 1e18, bals[1] / 1e6, bals[2] / 1e6] if len(bals) == 3 else []
    return {"t0_block": t0, "capsules": caps,
            "observed": {"pool": CURVE_3POOL, "exit": f"{EXIT_SIZE_USD:,} {s_in} -> {s_out}",
                         "exit_discount": round(disc, 5),
                         "pool_shares": [round(x / sum(norm), 4) for x in norm] if norm else None},
            "derived": {"gate_fail": disc > MAX_EXIT_DISCOUNT}}


def h02(chain: str = "ethereum") -> dict:
    """stETH, June 2022: exit depth stETH -> ETH through Curve at T0, and pool imbalance."""
    t0 = rpc.block_at(chain, H02_T0); caps = []
    _, s_in, d_in = _coin_meta(chain, CURVE_STETH, 1, t0, caps)
    # size in stETH: $1M at ~1,800 USD/ETH (June 2022) ≈ 550 stETH; recorded, not hidden
    size = 550
    out, bals = _curve_exit(chain, CURVE_STETH, 1, 0, size * 10**d_in, t0, caps)
    disc = 1 - (out / 1e18) / size
    share_steth = bals[1] / (bals[0] + bals[1]) if len(bals) >= 2 else None
    return {"t0_block": t0, "capsules": caps,
            "observed": {"pool": CURVE_STETH, "exit": f"{size} {s_in} -> ETH (≈ ${EXIT_SIZE_USD:,})",
                         "exit_discount": round(disc, 5),
                         "steth_share_of_pool": round(share_steth, 4) if share_steth else None},
            "derived": {"gate_fail": disc > MAX_EXIT_DISCOUNT}}


def h01(chain: str = "ethereum") -> dict:
    """UST, May 2022: exit depth and imbalance of the Curve UST/3CRV metapool at T0.
    Evidence only: the label rests on reflexive backing on Terra, not observable here."""
    t0 = rpc.block_at(chain, H01_T0); caps = []
    _, s_in, d_in = _coin_meta(chain, CURVE_UST_WH, 0, t0, caps)
    if "UST" not in s_in.upper():
        raise rpc.RPCError(f"coin 0 of {CURVE_UST_WH} is {s_in}, expected UST — check the pool address")
    out, bals = _curve_exit(chain, CURVE_UST_WH, 0, 1, EXIT_SIZE_USD * 10**d_in, t0, caps)
    raw, c = rpc.call(chain, CURVE_3POOL, "get_virtual_price", t0); caps.append(c)
    vp = rpc.as_uint(raw) / 1e18
    disc = 1 - (out / 1e18 * vp) / EXIT_SIZE_USD
    share_ust = (bals[0] / 10**d_in) / (bals[0] / 10**d_in + bals[1] / 1e18 * vp) if len(bals) >= 2 else None
    return {"t0_block": t0, "capsules": caps, "status_override": "evidence attached",
            "observed": {"pool": CURVE_UST_WH, "exit": f"{EXIT_SIZE_USD:,} {s_in} -> 3CRV",
                         "exit_discount": round(disc, 5),
                         "ust_share_of_pool": round(share_ust, 4) if share_ust else None,
                         "note": "label (reflexive backing) is not observable on Ethereum; exit depth is shown as evidence only"},
            "derived": {}}


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


RECON = {"H01": h01, "H02": h02, "H04": h04, "H05": h05, "H06": h06, "H07": h07, "H08": h08, "H09": h09, "H10": h10,
         "H11": h11, "H12": h12, "H13": h13}


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
            cases[cid]["status"] = r.get("status_override", "reconstructed")
            cases[cid].setdefault("sources", {}).setdefault("onchain_state", {})["capsules"] = r["capsules"]
            changed = True
    if changed:
        json.dump(doc, open(HIST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"updated {HIST}")


if __name__ == "__main__":
    main()
