#!/usr/bin/env python3
"""snapshot_p01.py — facts at t0 for the prospective case P01, read on chain with capsules.

P01: an RLUSD depositor in a curated Morpho Vault V2 on Ethereum. Everything behind the
verdict is read at one block (t0_block) through rpc.py, so each fact carries a capsule.
The Morpho API supplies candidate ADDRESSES only (the borrowers of each market); every
amount is read on chain at t0_block.

The verdict written here is the track's own ground-truth rule applied to these facts
(a rules baseline, no language model). It is what the prospective split tests first:
whether the rule label, fixed before the outcome, predicts the outcome.

    python tools/snapshot_p01.py                       # writes to ~/bench-private
    python tools/snapshot_p01.py --out D:/somewhere    # or elsewhere, never into the repo

then
    python prereg.py commit --id P01 --chain ethereum --t0 <date printed> --t0-block <N> \
        --horizon 90 --model rules-baseline-v0.5 --model-cutoff n/a \
        --verdict ~/bench-private/P01_verdict.json --facts ~/bench-private/P01_facts.json \
        --private-dir ~/bench-private
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc  # noqa: E402
from defi_track import ground_truth_defi  # noqa: E402
from bench import SourceState  # noqa: E402
from reconstruct_historical import (  # noqa: E402
    MORPHO_BLUE, CONCENTRATION_MAX, BORROWER_SHARE_MAX, ORACLE_DEVIATION_MAX,
    MIN_TIMELOCK_SECONDS, EXIT_SIZE_USD, morpho_api_position_holders)

CHAIN = "ethereum"
VAULT = "0x6dC58a0FdfC8D694e571DC59B9A52EEEa780E6bf"     # Morpho Vault V2 "Sentora RLUSD Main"
CONFIRMATIONS = 12
MIN_ALLOC_FOR_BORROWER_SCAN = 1_000_000   # USD; markets below this are reported, not scanned

# Chainlink USD references for the oracle sanity check (description() is read and kept).
REFERENCE_FEEDS = {
    "BTC": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",   # BTC / USD
    "ETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",   # ETH / USD
}
REFERENCE_FOR_SYMBOL = {"kBTC": "BTC", "cbBTC": "BTC", "WBTC": "BTC",
                        "weETH": "ETH", "wstETH": "ETH", "WETH": "ETH"}

# Vault V2 functions that raise risk for a depositor; each must sit behind a timelock of at
# least MIN_TIMELOCK_SECONDS for controls to count as safe: adding an adapter, raising a cap,
# raising the force-deallocation penalty, and the two gates checked on exit (withdraw/redeem
# require canSendShares(owner) and canReceiveAssets(receiver)).
# decreaseTimelock is not listed: VaultV2.submit() applies the timelock of the selector being
# decreased, so its own slot is unused. Other setters are read and reported, not scored.
RISK_SELECTORS = {
    "addAdapter(address)": "0x60d54d41",
    "increaseAbsoluteCap(bytes,uint256)": "0xf6f98fd5",
    "increaseRelativeCap(bytes,uint256)": "0x2438525b",
    "setForceDeallocatePenalty(address,uint256)": "0x3e9d2ac7",
    "setReceiveAssetsGate(address)": "0x04dbf0ce",
    "setSendSharesGate(address)": "0xc21ad028",
}
INFO_SELECTORS = {
    "setIsAllocator(address,bool)": "0xb192a84a",
    "setAdapterRegistry(address)": "0x5b34b823",
    "setReceiveSharesGate(address)": "0x2cb19f98",
    "setSendAssetsGate(address)": "0x871c979c",
}

# Selectors checked against keccak-256 of the signature.
rpc.SELECTORS.update({
    "curator": "0xe66f53b7", "owner": "0x8da5cb5b",
    "adaptersLength": "0x5aa22bc8", "adapters": "0x4ef501ac",
    "liquidityAdapter": "0xad468d11", "timelock": "0xe78ab14e", "abdicated": "0xe470b8bc",
    "marketIdsLength": "0xace48b45", "marketIds": "0x779a9683",
    "balanceOf": "0x70a08231",
})


def _try(to, fn, block, args=""):
    try:
        return rpc.call(CHAIN, to, fn, block, args)
    except rpc.RPCError:
        return None, None


def _string(raw: str) -> str:
    try:
        w = rpc.words(raw)
        n = rpc.as_uint(w[1])
        return bytes.fromhex("".join(w[2:])[: 2 * n]).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def snapshot(t0: int, caps: list) -> dict:
    def rd(to, fn, args=""):
        raw, c = rpc.call(CHAIN, to, fn, t0, args)
        caps.append(c)
        return raw

    asset = rpc.as_address(rpc.words(rd(VAULT, "asset"))[0])
    adec = rpc.as_uint(rd(asset, "decimals"))
    unit = 10 ** adec
    total_assets = rpc.as_uint(rd(VAULT, "totalAssets")) / unit
    idle = rpc.as_uint(rd(asset, "balanceOf", rpc.enc_address(VAULT))) / unit
    owner = rpc.as_address(rpc.words(rd(VAULT, "owner"))[0])
    curator = rpc.as_address(rpc.words(rd(VAULT, "curator"))[0])

    # admin: is owner / curator a Safe, and with what threshold
    admins = {}
    for role, a in (("owner", owner), ("curator", curator)):
        raw, c = _try(a, "getThreshold", t0)
        if c:
            caps.append(c)
        admins[role] = {"address": a, "safe_threshold": rpc.as_uint(raw) if raw and raw != "0x" else None}

    timelocks, timelocks_info = {}, {}
    for sig, sel in RISK_SELECTORS.items():
        arg = sel[2:].ljust(64, "0")                       # bytes4 is left-aligned
        timelocks[sig] = rpc.as_uint(rd(VAULT, "timelock", arg))
    for sig, sel in INFO_SELECTORS.items():
        timelocks_info[sig] = rpc.as_uint(rd(VAULT, "timelock", sel[2:].ljust(64, "0")))

    # allocation, enumerated on chain: vault -> adapters -> market ids -> Morpho positions
    markets = []
    n_ad = rpc.as_uint(rd(VAULT, "adaptersLength"))
    for i in range(n_ad):
        ad = rpc.as_address(rpc.words(rd(VAULT, "adapters", rpc.enc_uint(i)))[0])
        raw, c = _try(ad, "marketIdsLength", t0)
        if not c:
            markets.append({"adapter": ad, "error": "not a Morpho market adapter (no marketIdsLength)"})
            continue
        caps.append(c)
        for j in range(rpc.as_uint(raw)):
            mid = "0x" + rpc.words(rd(ad, "marketIds", rpc.enc_uint(j)))[0]
            p = rpc.words(rd(MORPHO_BLUE, "idToMarketParams", rpc.enc_bytes32(mid)))
            coll, oracle, lltv = rpc.as_address(p[1]), rpc.as_address(p[2]), rpc.as_uint(p[4]) / 1e18
            m = rpc.words(rd(MORPHO_BLUE, "market", rpc.enc_bytes32(mid)))
            tsa, tss, tba, tbs = (rpc.as_uint(m[k]) for k in range(4))
            pos = rpc.words(rd(MORPHO_BLUE, "position", rpc.enc_bytes32(mid) + rpc.enc_address(ad)))
            sup_shares = rpc.as_uint(pos[0])
            supplied = (sup_shares * tsa // tss if tss else 0) / unit
            sym = _string(rd(coll, "symbol")) if coll != "0x" + "0" * 40 else ""
            cdec = rpc.as_uint(rd(coll, "decimals")) if sym else 18
            raw, c = _try(oracle, "price", t0)
            implied = None
            if c:
                caps.append(c)
                implied = rpc.as_uint(raw) / 1e36 * 10 ** cdec / unit
            markets.append({"adapter": ad, "market_id": mid, "collateral": coll, "symbol": sym,
                            "oracle": oracle, "lltv": lltv,
                            "vault_supplied": round(supplied, 2),
                            "market_supply": round(tsa / unit, 2), "market_borrow": round(tba / unit, 2),
                            "market_liquidity": round((tsa - tba) / unit, 2),
                            "utilization": round(tba / tsa, 4) if tsa else None,
                            "borrow_shares_total": tbs,
                            "oracle_implied_usd": implied})

    # oracle sanity against a USD reference (loan asset assumed at $1; RLUSD)
    refs = {}
    for k, feed in REFERENCE_FEEDS.items():
        d = _string(rd(feed, "description"))
        dec = rpc.as_uint(rd(feed, "decimals"))
        ans = rpc.as_uint(rpc.words(rd(feed, "latestRoundData"))[1]) / 10 ** dec
        refs[k] = {"feed": feed, "description": d, "usd": ans}
    for mk in markets:
        r = REFERENCE_FOR_SYMBOL.get(mk.get("symbol", ""))
        if r and mk.get("oracle_implied_usd"):
            mk["reference_usd"] = refs[r]["usd"]
            mk["oracle_vs_reference"] = round(mk["oracle_implied_usd"] / refs[r]["usd"], 4)

    # borrower concentration: candidate addresses from the API, amounts on chain
    for mk in markets:
        if mk.get("vault_supplied", 0) < MIN_ALLOC_FOR_BORROWER_SCAN or not mk.get("borrow_shares_total"):
            continue
        cands, api_cap = morpho_api_position_holders(mk["market_id"], 1)
        caps.append(api_cap)
        rows = []
        for b in cands:
            raw, c = rpc.call(CHAIN, MORPHO_BLUE, "position", t0,
                              rpc.enc_bytes32(mk["market_id"]) + rpc.enc_address(b))
            bs = rpc.as_uint(rpc.words(raw)[1])
            if bs:
                caps.append(c)
                rows.append((bs / mk["borrow_shares_total"], b))
        rows.sort(reverse=True)
        mk["borrowers_at_t0"] = len(rows)
        mk["top_borrowers"] = [{"address": b, "share": round(s, 4)} for s, b in rows[:3]]

    deployed = sum(m.get("vault_supplied", 0) for m in markets)
    by_coll: dict = {}
    for m in markets:
        if m.get("vault_supplied"):
            by_coll[m["symbol"] or m["collateral"]] = by_coll.get(m["symbol"] or m["collateral"], 0) + m["vault_supplied"]
    alloc = sorted(((v / deployed, k) for k, v in by_coll.items()), reverse=True) if deployed else []
    withdrawable = idle + sum(min(m.get("vault_supplied", 0), max(m.get("market_liquidity", 0), 0))
                              for m in markets)
    return {"vault": VAULT, "asset": asset, "total_assets": round(total_assets, 2),
            "idle": round(idle, 2), "withdrawable_now": round(withdrawable, 2),
            "admins": admins, "timelocks_s": timelocks, "timelocks_info_s": timelocks_info, "references": refs,
            "allocation_by_collateral": [{"collateral": k, "share_of_deployed": round(s, 4)} for s, k in alloc],
            "markets": markets}


def derive(obs: dict) -> dict:
    alloc = obs["allocation_by_collateral"]
    top_alloc = alloc[0]["share_of_deployed"] if alloc else 0.0
    top_borrower = max((b["share"] for m in obs["markets"] for b in m.get("top_borrowers", [])[:1]),
                       default=0.0)
    oracle_off = [m["symbol"] for m in obs["markets"] if m.get("oracle_vs_reference") is not None
                  and abs(m["oracle_vs_reference"] - 1) > ORACLE_DEVIATION_MAX and m.get("vault_supplied")]
    exit_fail = obs["withdrawable_now"] < EXIT_SIZE_USD
    min_tl = min(obs["timelocks_s"].values()) if obs["timelocks_s"] else 0
    return {
        "concentration_breach": top_alloc > CONCENTRATION_MAX or top_borrower > BORROWER_SHARE_MAX,
        "concentration_detail": {"top_collateral_share": top_alloc, "max": CONCENTRATION_MAX,
                                 "top_borrower_share": top_borrower, "borrower_max": BORROWER_SHARE_MAX},
        "gate_fail": bool(oracle_off) or exit_fail,
        "gate_detail": {"oracle_off_reference": oracle_off, "exit_size_usd": EXIT_SIZE_USD,
                        "withdrawable_now": obs["withdrawable_now"],
                        "backing": "not assessed on chain (custodial wrappers need issuer evidence)"},
        "controls_safe": min_tl >= MIN_TIMELOCK_SECONDS,
        "controls_detail": {"min_risk_timelock_s": min_tl, "min_required_s": MIN_TIMELOCK_SECONDS},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.expanduser("~/bench-private"))
    ap.add_argument("--block", type=int, help="t0 block (default: latest minus %d)" % CONFIRMATIONS)
    a = ap.parse_args()
    if os.path.abspath(a.out).startswith(os.path.abspath(ROOT)):
        sys.exit("--out must be outside the repository (the record is private until reveal)")
    os.makedirs(a.out, exist_ok=True)
    t0 = a.block or int(rpc.rpc(CHAIN, "eth_blockNumber", []), 16) - CONFIRMATIONS
    ts = int(rpc.rpc(CHAIN, "eth_getBlockByNumber", [hex(t0), False])["timestamp"], 16)
    t0_iso = _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat()
    caps: list = []
    obs = snapshot(t0, caps)
    der = derive(obs)
    ok = SourceState(True, "alchemy_archive", False, ["alchemy_archive"])
    srcs = {"onchain_state": ok, "contract_meta": ok, "market_depth": ok,
            "offchain_meta": SourceState(False, None, False, [])}
    outcome, decidable = ground_truth_defi(der["gate_fail"], der["concentration_breach"],
                                           der["controls_safe"], srcs)
    verdict = {"verdict": {"FLAG": "NO-GO", "CLEAR": "GO", "ESCALATE": "INSUFFICIENT_DATA"}.get(
                   str(outcome).split(".")[-1].upper(), str(outcome)),
               "agent": "rules-baseline (defi_track.ground_truth_defi, no language model)",
               "basis": der, "controls_verified": der["controls_safe"], "anomaly_basis": False,
               "citations": {"state": "alchemy_archive", "depth": "alchemy_archive",
                             "controls": "alchemy_archive"}}
    facts = {"case": "P01", "chain": CHAIN, "t0_block": t0, "t0_timestamp": t0_iso,
             "observed": obs, "derived": der, "capsules": caps}
    json.dump(facts, open(os.path.join(a.out, "P01_facts.json"), "w", encoding="utf-8"), indent=1, default=str)
    json.dump(verdict, open(os.path.join(a.out, "P01_verdict.json"), "w", encoding="utf-8"), indent=1, default=str)
    print(f"t0_block={t0}  t0={t0_iso}  capsules={len(caps)}")
    print(f"total_assets={obs['total_assets']:,.0f}  idle={obs['idle']:,.0f}  withdrawable={obs['withdrawable_now']:,.0f}")
    for x in obs["allocation_by_collateral"]:
        print(f"  {x['collateral']:>22}: {x['share_of_deployed']:.1%} of deployed")
    for m in obs["markets"]:
        if m.get("vault_supplied"):
            tb = m.get("top_borrowers", [{}])[0] if m.get("top_borrowers") else {}
            print(f"  {m['symbol']:>22}: supplied {m['vault_supplied']:>14,.0f}  util {m['utilization']}  "
                  f"oracle/ref {m.get('oracle_vs_reference')}  top borrower {tb.get('share')}")
    print(f"timelocks (scored): {obs['timelocks_s']}")
    print(f"timelocks (reported): {obs['timelocks_info_s']}")
    print(f"admins: {obs['admins']}")
    print(f"derived: concentration={der['concentration_breach']} gate_fail={der['gate_fail']} "
          f"controls_safe={der['controls_safe']}  ->  VERDICT {verdict['verdict']}")
    print(f"wrote {a.out}/P01_facts.json and P01_verdict.json  (do NOT commit these)")
    print(f"next: python prereg.py commit --id P01 --chain ethereum --t0 {t0_iso[:10]} --t0-block {t0} "
          f"--horizon 90 --model rules-baseline-v0.5 --model-cutoff n/a "
          f"--verdict {a.out}/P01_verdict.json --facts {a.out}/P01_facts.json --private-dir {a.out}")


if __name__ == "__main__":
    main()
