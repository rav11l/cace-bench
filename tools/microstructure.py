#!/usr/bin/env python3
"""Exit-cost curves and oracle-manipulation economics, read from archive state.

Two analyses for the DeFi track, both computed from chain state with rpc.py:

A. exit-curves  — cost of exiting $1M / $10M / $50M through the deepest pool, sampled
   every 12 h from T0-14d to T0+7d. Curve pools for H01 (UST), H02 (stETH), H04 (USDC);
   concentrated-liquidity pools for H12 (MAMO) if pool addresses are known or found.

B. manipulation — H12 Moonwell MAMO at T0: what it costs to push MAMO's spot price by a
   factor k through its AMM pools, against how much could be borrowed with the MAMO bought,
   bounded by the market's supply cap (or not, if the cap can be bypassed by donation)
   and by the cash actually available in the other markets.

Every number comes from a view call at a block; the JSON output keeps the blocks and the
capsules, so a reader can re-run any point.

    export RPC_ETHEREUM=...   RPC_BASE=...   (archive)
    python tools/microstructure.py exit-curves --cases H01 H02 H04 --out results/defi/micro
    python tools/microstructure.py exit-curves --cases H12 --mamo-pools 0x..,0x..
    python tools/microstructure.py manipulation --out results/defi/micro
    python tools/microstructure.py manipulation --mamo-pools 0x..,0x..   # if discovery fails

Assumptions are printed with the results and written into the JSON; nothing is hidden.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import rpc  # noqa: E402

SIZES_USD = (1_000_000, 10_000_000, 50_000_000)
STEP_HOURS = 12
WINDOW_BEFORE_D, WINDOW_AFTER_D = 14, 7

# ---------------------------------------------------------------- selectors -------
# keccak-checked; passed to rpc.call as raw hex
SEL = {
    "get_dy": "0x5e0d443f", "balances": "0x4903b0d1", "get_virtual_price": "0xbb7b8b80",
    "latestRoundData": "0xfeaf968c", "decimals": "0x313ce567",
    "slot0": "0x3850c7bd", "liquidity": "0x1a686502", "tickSpacing": "0xd0c93a7c",
    "tickBitmap": "0x5339c296", "ticks": "0xf30dba93", "token0": "0x0dfe1681",
    "token1": "0xd21220a7", "fee": "0xddca3f43",
    "getAllMarkets": "0xb0772d0b", "markets": "0x8e8f294b", "underlying": "0x6f307dc3",
    "getCash": "0x3b1d21a2", "borrowCaps": "0x4a584432", "supplyCaps": "0x02c3bcbb",
    "totalBorrows": "0x47bd3718", "totalSupply": "0x18160ddd",
    "exchangeRateStored": "0x182df0f5", "getUnderlyingPrice": "0xfc57d4df",
    "getPool_u24": "0x1698ee82", "getPool_i24": "0x28af8d0b",
}

# ------------------------------------------------------------------ addresses ------
ETH_USD_FEED = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"      # Chainlink ETH/USD, mainnet
CURVE = {
    "H01": {"chain": "ethereum", "pool": "0xCEAF7747579696A2F0bb206a14210e3c9e6fB269",
            "i": 0, "j": 1, "dec_in": 6, "kind": "ust_3crv", "t0": "2022-05-06T00:00:00Z",
            "label": "UST -> 3CRV (Curve UST-Wormhole metapool)"},
    "H02": {"chain": "ethereum", "pool": "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
            "i": 1, "j": 0, "dec_in": 18, "kind": "steth_eth", "t0": "2022-06-10T00:00:00Z",
            "label": "stETH -> ETH (Curve stETH pool)"},
    "H04": {"chain": "ethereum", "pool": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
            "i": 1, "j": 0, "dec_in": 6, "kind": "usdc_dai", "t0": "2023-03-09T00:00:00Z",
            "label": "USDC -> DAI (Curve 3pool)"},
}
CURVE_3POOL = CURVE["H04"]["pool"]

# H12, Base. Comptroller and oracle were discovered by reconstruct_historical.h12.
MW_COMPTROLLER = "0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
MW_ORACLE = "0xec942be8a8114bfd0396a5052c36027f2ca6a9d0"
MW_MMAMO = "0x2f90bb22eb3979f5ffad31ea6c3f0792ca66da32"
MAMO = "0x7300b37dfdfab110d83290a29dfb31b1740219fe"
H12_T0 = "2026-08-26T00:00:00Z"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_BASE = "0x4200000000000000000000000000000000000006"
# Best-effort pool discovery. VERIFY these factory addresses; if discovery finds nothing,
# pass --mamo-pools explicitly (Basescan: MAMO token page -> DEX trades -> pool addresses).
UNIV3_FACTORY_BASE = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
SLIPSTREAM_FACTORY_BASE = "0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A"
K_FACTORS = (1.5, 2, 3, 5, 8, 10, 20, 40)

Q96 = 2 ** 96
ZERO = "0x" + "0" * 40


# ------------------------------------------------------------------ helpers --------
def call(chain, to, fn, block, args=""):
    return rpc.call(chain, to, SEL.get(fn, fn), block, args)


def try_call(chain, to, fn, block, args=""):
    try:
        return call(chain, to, fn, block, args)
    except rpc.RPCError:
        return None, None


def enc_int(n: int) -> str:
    return f"{n & (2**256 - 1):064x}"


def as_int(word: str) -> int:
    v = int(word, 16)
    return v - 2**256 if v >= 2**255 else v


def block_ts(chain, b) -> int:
    return int(rpc.rpc(chain, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)


def sample_blocks(chain, t0_iso):
    """Blocks every STEP_HOURS from T0-14d to T0+7d. Ends found by binary search, the rest
    interpolated linearly and then stamped with their real timestamps."""
    import datetime as dt
    t0 = int(dt.datetime.fromisoformat(t0_iso.replace("Z", "+00:00")).timestamp())
    t_a, t_b = t0 - WINDOW_BEFORE_D * 86400, t0 + WINDOW_AFTER_D * 86400
    b_a, b_b = rpc.block_at(chain, t_a), rpc.block_at(chain, t_b)
    n = (t_b - t_a) // (STEP_HOURS * 3600)
    out = []
    for i in range(n + 1):
        b = b_a + round((b_b - b_a) * i / n)
        out.append((b, block_ts(chain, b), t0))
    return out


def eth_usd(block) -> float:
    raw, _ = call("ethereum", ETH_USD_FEED, "latestRoundData", block)
    return rpc.as_uint(rpc.words(raw)[1]) / 1e8


# ------------------------------------------------------------- A. Curve exits -----
def curve_exit_point(cfg, block, size_usd):
    ch, pool = cfg["chain"], cfg["pool"]
    if cfg["kind"] == "steth_eth":
        px = eth_usd(block)
        dx_units = size_usd / px                     # stETH at par to ETH
    else:
        px, dx_units = 1.0, float(size_usd)          # stablecoin at par
    dx = int(dx_units * 10 ** cfg["dec_in"])
    raw, cap = try_call(ch, pool, "get_dy", block, enc_int(cfg["i"]) + enc_int(cfg["j"]) + enc_int(dx))
    if not raw:
        return None, cap
    out = rpc.as_uint(raw) / 1e18
    if cfg["kind"] == "ust_3crv":
        vp_raw, _ = call(ch, CURVE_3POOL, "get_virtual_price", block)
        value_out = out * rpc.as_uint(vp_raw) / 1e18
        return 1 - value_out / size_usd, cap
    if cfg["kind"] == "steth_eth":
        return 1 - out / dx_units, cap
    return 1 - out / size_usd, cap


def curve_share(cfg, block):
    ch, pool = cfg["chain"], cfg["pool"]
    b = []
    for k in range(3):
        raw, _ = try_call(ch, pool, "balances", block, enc_int(k))
        if not raw:
            break
        b.append(rpc.as_uint(raw))
    if cfg["kind"] == "steth_eth" and len(b) >= 2:
        return b[1] / (b[0] + b[1])
    if cfg["kind"] == "ust_3crv" and len(b) >= 2:
        vp = rpc.as_uint(call(cfg["chain"], CURVE_3POOL, "get_virtual_price", block)[0]) / 1e18
        ust, tri = b[0] / 1e6, b[1] / 1e18 * vp
        return ust / (ust + tri)
    if cfg["kind"] == "usdc_dai" and len(b) == 3:
        n = [b[0] / 1e18, b[1] / 1e6, b[2] / 1e6]
        return n[1] / sum(n)
    return None


# ------------------------------------------- concentrated-liquidity pool simulation ---
class CLPool:
    """Uniswap-V3-style pool (also Aerodrome Slipstream: same slot0/ticks/tickBitmap prefix).
    Liquidity is read at one block; swaps are simulated range by range, fee included."""

    def __init__(self, chain, addr, block, caps):
        self.chain, self.addr, self.block, self.caps = chain, addr, block, caps
        w = rpc.words(self._c("slot0"))
        self.sqrtp = int(w[0], 16) / Q96
        self.tick = as_int(w[1])
        self.L = rpc.as_uint(self._c("liquidity"))
        self.spacing = as_int(rpc.words(self._c("tickSpacing"))[0])
        self.fee = rpc.as_uint(self._c("fee")) / 1e6
        self.token0 = rpc.as_address(rpc.words(self._c("token0"))[0]).lower()
        self.token1 = rpc.as_address(rpc.words(self._c("token1"))[0]).lower()
        self._bitmap = {}

    def _c(self, fn, args=""):
        raw, c = call(self.chain, self.addr, fn, self.block, args)
        self.caps.append(c)
        return raw

    def _word(self, pos):
        if pos not in self._bitmap:
            self._bitmap[pos] = rpc.as_uint(self._c("tickBitmap", enc_int(pos)))
        return self._bitmap[pos]

    def _net(self, tick):
        return as_int(rpc.words(self._c("ticks", enc_int(tick)))[1])

    def _next_tick(self, tick, up, limit_words=400):
        """Next initialized tick strictly above (up) or at-or-below (down) `tick`."""
        comp = math.floor(tick / self.spacing)
        if up:
            comp += 1
            for _ in range(limit_words):
                pos, bit = comp >> 8, comp % 256
                word = self._word(pos) >> bit
                if word:
                    return (comp + (word & -word).bit_length() - 1) * self.spacing
                comp = (pos + 1) * 256
            return None
        for _ in range(limit_words):
            pos, bit = comp >> 8, comp % 256
            word = self._word(pos) & ((1 << (bit + 1)) - 1)
            if word:
                return (pos * 256 + word.bit_length() - 1) * self.spacing
            comp = pos * 256 - 1
        return None

    @staticmethod
    def _sqrt_at(tick):
        return 1.0001 ** (tick / 2)

    def move_to(self, target_sqrtp):
        """Swap until sqrtP = target. Returns (amount0, amount1): positive = paid into the
        pool (fee included), negative = taken out."""
        s, L, tick = self.sqrtp, self.L, self.tick
        up = target_sqrtp > s
        a0 = a1 = 0.0
        while (s < target_sqrtp) if up else (s > target_sqrtp):
            nt = self._next_tick(tick, up)
            s_next = self._sqrt_at(nt) if nt is not None else target_sqrtp
            s_to = min(s_next, target_sqrtp) if up else max(s_next, target_sqrtp)
            if L > 0:
                if up:   # token1 in, token0 out
                    a1 += L * (s_to - s) / (1 - self.fee)
                    a0 -= L * (1 / s - 1 / s_to)
                else:    # token0 in, token1 out
                    a0 += L * (1 / s_to - 1 / s) / (1 - self.fee)
                    a1 -= L * (s - s_to)
            if nt is None or s_to == target_sqrtp:
                s = s_to
                break
            net = self._net(nt)
            L = L + net if up else L - net
            tick = nt if up else nt - 1
            s = s_to
        return a0, a1

    def sell(self, token, amount_raw):
        """Sell `amount_raw` of `token` into the pool; returns raw amount of the other token."""
        zero_for_one = token.lower() == self.token0
        s, L, tick = self.sqrtp, self.L, self.tick
        left, out = float(amount_raw), 0.0
        for _ in range(10_000):
            if left <= 0:
                break
            nt = self._next_tick(tick, not zero_for_one)
            if nt is None:
                break                                   # ran out of initialized liquidity
            s_lim = self._sqrt_at(nt)
            eff = left * (1 - self.fee)
            if L > 0:
                if zero_for_one:
                    need = L * (1 / s_lim - 1 / s)
                    if eff < need:
                        s_new = 1 / (1 / s + eff / L)
                        out += L * (s - s_new); left = 0; break
                    out += L * (s - s_lim); left -= need / (1 - self.fee)
                else:
                    need = L * (s_lim - s)
                    if eff < need:
                        s_new = s + eff / L
                        out += L * (1 / s - 1 / s_new); left = 0; break
                    out += L * (1 / s - 1 / s_lim); left -= need / (1 - self.fee)
            net = self._net(nt)
            L = L - net if zero_for_one else L + net
            tick = nt - 1 if zero_for_one else nt
            s = s_lim
        return out, left


# --------------------------------------------------------------- Moonwell helpers ----
def mw_price(block, mtoken, dec):
    raw, c = call("base", MW_ORACLE, "getUnderlyingPrice", block, rpc.enc_address(mtoken))
    return rpc.as_uint(raw) / 10 ** (36 - dec), c


def mw_markets(block, caps):
    raw, c = call("base", MW_COMPTROLLER, "getAllMarkets", block); caps.append(c)
    w = rpc.words(raw)
    return [rpc.as_address(x).lower() for x in w[2:2 + int(w[1], 16)]]


def quote_usd(block, token, caps):
    """USD price of a pool's quote token, from Moonwell's own oracle."""
    if token.lower() == USDC_BASE.lower():
        return 1.0
    for m in mw_markets(block, caps):
        raw, _ = try_call("base", m, "underlying", block)
        if raw and rpc.as_address(rpc.words(raw)[0]).lower() == token.lower():
            d = rpc.as_uint(call("base", token, "decimals", block)[0])
            p, c = mw_price(block, m, d); caps.append(c)
            return p
    raise rpc.RPCError(f"no Moonwell market prices quote token {token}")


def discover_mamo_pools(block, caps):
    found = []
    for q in (USDC_BASE, WETH_BASE):
        a, b = sorted([MAMO.lower(), q.lower()])
        for fee in (100, 500, 3000, 10000):
            raw, _ = try_call("base", UNIV3_FACTORY_BASE, "getPool_u24", block,
                              rpc.enc_address(a) + rpc.enc_address(b) + enc_int(fee))
            if raw and rpc.as_address(rpc.words(raw)[0]) != ZERO:
                found.append(rpc.as_address(rpc.words(raw)[0]))
        for ts in (1, 50, 100, 200, 2000):
            raw, _ = try_call("base", SLIPSTREAM_FACTORY_BASE, "getPool_i24", block,
                              rpc.enc_address(a) + rpc.enc_address(b) + enc_int(ts))
            if raw and rpc.as_address(rpc.words(raw)[0]) != ZERO:
                found.append(rpc.as_address(rpc.words(raw)[0]))
    return found


def load_pools(block, pools, caps):
    out = []
    for p in pools:
        try:
            pool = CLPool("base", p, block, caps)
        except rpc.RPCError as e:
            print(f"  skip {p}: {e}")
            continue
        if MAMO.lower() not in (pool.token0, pool.token1) or pool.L == 0:
            continue
        out.append(pool)
    return out


def mamo_spot(pool, quote_px):
    """MAMO price in USD implied by the pool (18-dec MAMO; quote decimals from chain)."""
    qt = pool.token1 if pool.token0 == MAMO.lower() else pool.token0
    qd = rpc.as_uint(call("base", qt, "decimals", pool.block)[0])
    p01 = pool.sqrtp ** 2 * 10 ** (18 - qd) if pool.token0 == MAMO.lower() else \
        (1 / pool.sqrtp ** 2) * 10 ** (18 - qd)
    return p01 * quote_px, qt, qd


# ------------------------------------------------------------------ commands -------
def cmd_exit_curves(a):
    rows, caps_all = [], {}
    for cid in a.cases:
        if cid in CURVE:
            cfg = CURVE[cid]
            print(f"{cid}: {cfg['label']}")
            for b, ts, t0 in sample_blocks(cfg["chain"], cfg["t0"]):
                share = curve_share(cfg, b)
                for size in SIZES_USD:
                    d, cap = curve_exit_point(cfg, b, size)
                    rows.append({"case": cid, "block": b, "ts": ts,
                                 "hours_from_t0": round((ts - t0) / 3600, 1), "size_usd": size,
                                 "exit_discount": None if d is None else round(d, 6),
                                 "risky_share_of_pool": None if share is None else round(share, 4)})
                    if cap:
                        caps_all.setdefault(cid, []).append(cap)
                print(f"  {rows[-1]['hours_from_t0']:+7.1f}h  "
                      + "  ".join(f"${s/1e6:.0f}M:{_fmt(r['exit_discount'])}" for s, r in
                                  zip(SIZES_USD, rows[-3:])))
        elif cid == "H12":
            pools_arg = [p for p in (a.mamo_pools or "").split(",") if p]
            for b, ts, t0 in sample_blocks("base", H12_T0):
                caps = []
                pools = load_pools(b, pools_arg or discover_mamo_pools(b, caps), caps)
                if not pools:
                    print("  no MAMO pool found — pass --mamo-pools"); break
                for size in SIZES_USD:
                    got_usd, unfilled = 0.0, 0
                    # split the sale across pools pro rata to in-range liquidity (simple, stated)
                    Ls = [p.L for p in pools]; tot = sum(Ls)
                    for p, L in zip(pools, Ls):
                        qpx = quote_usd(b, p.token1 if p.token0 == MAMO.lower() else p.token0, caps)
                        spot, qt, qd = mamo_spot(p, qpx)
                        mamo_amt = size * L / tot / spot * 1e18
                        out, left = p.sell(MAMO, mamo_amt)
                        got_usd += out / 10 ** qd * qpx
                        unfilled += left
                    rows.append({"case": "H12", "block": b, "ts": ts,
                                 "hours_from_t0": round((ts - t0) / 3600, 1), "size_usd": size,
                                 "exit_discount": round(1 - got_usd / size, 6),
                                 "unfilled_mamo": unfilled / 1e18 if unfilled else 0})
                caps_all.setdefault("H12", []).extend(caps)
                print(f"  {rows[-1]['hours_from_t0']:+7.1f}h  "
                      + "  ".join(f"${s/1e6:.0f}M:{_fmt(r['exit_discount'])}" for s, r in
                                  zip(SIZES_USD, rows[-3:])))
    rows, caps_all = _keep_other_cases(a.out, "exit_curves", rows, caps_all)
    _write(a.out, "exit_curves", rows, caps_all, {
        "sizes_usd": SIZES_USD, "step_hours": STEP_HOURS,
        "window_days": [-WINDOW_BEFORE_D, WINDOW_AFTER_D],
        "valuation": "stablecoins at par; stETH at par to ETH (Chainlink ETH/USD); 3CRV at "
                     "3pool virtual price; MAMO sold pro rata to in-range liquidity per pool",
        "exit_discount": "1 - value received / value at par (or at pool spot for MAMO)"})


def cmd_manipulation(a):
    caps = []
    t0 = rpc.block_at("base", H12_T0)
    pools_arg = [p for p in (a.mamo_pools or "").split(",") if p]
    pools = load_pools(t0, pools_arg or discover_mamo_pools(t0, caps), caps)
    if not pools:
        sys.exit("no MAMO pool found at T0 — pass --mamo-pools 0x..,0x..")
    # market parameters at T0
    raw, c = call("base", MW_COMPTROLLER, "markets", t0, rpc.enc_address(MW_MMAMO)); caps.append(c)
    cf = rpc.as_uint(rpc.words(raw)[1]) / 1e18
    raw, c = call("base", MW_COMPTROLLER, "supplyCaps", t0, rpc.enc_address(MW_MMAMO)); caps.append(c)
    supply_cap = rpc.as_uint(raw) / 1e18
    raw, c = call("base", MW_MMAMO, "totalSupply", t0); caps.append(c); m_supply = rpc.as_uint(raw)
    raw, c = call("base", MW_MMAMO, "exchangeRateStored", t0); caps.append(c); xr = rpc.as_uint(raw)
    supplied_mamo = m_supply * xr / 1e18 / 1e18
    p0, c = mw_price(t0, MW_MMAMO, 18); caps.append(c)
    # what other markets could actually lend at T0
    capacity, per_market = 0.0, []
    for m in mw_markets(t0, caps):
        if m == MW_MMAMO.lower():
            continue
        u_raw, _ = try_call("base", m, "underlying", t0)
        und = rpc.as_address(rpc.words(u_raw)[0]) if u_raw else WETH_BASE
        d = rpc.as_uint(call("base", und, "decimals", t0)[0]) if u_raw else 18
        cash = rpc.as_uint(call("base", m, "getCash", t0)[0]) / 10 ** d
        bcap = rpc.as_uint(call("base", MW_COMPTROLLER, "borrowCaps", t0, rpc.enc_address(m))[0]) / 10 ** d
        tb = rpc.as_uint(call("base", m, "totalBorrows", t0)[0]) / 10 ** d
        room = cash if bcap == 0 else max(0.0, min(cash, bcap - tb))
        px, _ = mw_price(t0, m, d)
        capacity += room * px
        per_market.append({"mtoken": m, "room_usd": round(room * px)})
    # cost of pushing all pools to k x spot (arbitrage keeps them aligned)
    results = []
    for k in K_FACTORS:
        cost_usd, mamo_got = 0.0, 0.0
        for p in pools:
            qpx = quote_usd(t0, p.token1 if p.token0 == MAMO.lower() else p.token0, caps)
            _, qt, qd = mamo_spot(p, qpx)
            target = p.sqrtp * math.sqrt(k) if p.token0 == MAMO.lower() else p.sqrtp / math.sqrt(k)
            a0, a1 = p.move_to(target)
            q_in, m_out = (a1, -a0) if p.token0 == MAMO.lower() else (a0, -a1)
            cost_usd += q_in / 10 ** qd * qpx
            mamo_got += m_out / 1e18
        room_under_cap = max(0.0, supply_cap - supplied_mamo) if supply_cap else mamo_got
        capped = min(mamo_got, room_under_cap)
        power_capped = cf * capped * k * p0
        power_uncapped = cf * mamo_got * k * p0
        results.append({
            "k": k, "spot_after_usd": round(k * p0, 6), "quote_spent_usd": round(cost_usd),
            "mamo_bought": round(mamo_got),
            "borrow_power_capped_usd": round(power_capped),
            "borrow_power_uncapped_usd": round(power_uncapped),
            "borrowable_capped_usd": round(min(power_capped, capacity)),
            "borrowable_uncapped_usd": round(min(power_uncapped, capacity)),
            "net_capped_usd": round(min(power_capped, capacity) - cost_usd),
            "net_uncapped_usd": round(min(power_uncapped, capacity) - cost_usd)})
        r = results[-1]
        print(f"  k={k:>4}: spend ${r['quote_spent_usd']:>12,}  buys {r['mamo_bought']:>13,} MAMO  "
              f"borrowable cap/no-cap ${r['borrowable_capped_usd']:>11,} / ${r['borrowable_uncapped_usd']:>11,}  "
              f"net ${r['net_capped_usd']:>12,} / ${r['net_uncapped_usd']:>12,}")
    out = {"t0_block": t0, "params_at_t0": {
        "collateral_factor": cf, "supply_cap_mamo": supply_cap, "mamo_already_supplied": round(supplied_mamo),
        "oracle_price_usd": p0, "pools": [p.addr for p in pools],
        "pool_fees": [p.fee for p in pools], "lendable_capacity_usd": round(capacity),
        "per_market_room": per_market},
        "results": results,
        "assumptions": [
            "pools are pushed to the same price (arbitrage), liquidity read at T0, fees included",
            "borrow power = CF x MAMO bought x manipulated price; 'capped' respects the supply "
            "cap minus MAMO already supplied, 'uncapped' assumes the cap is bypassed (e.g. by "
            "donating to the mToken, as the post-mortem's direct transfers suggest)",
            "borrowable is bounded by cash and borrow caps of the other markets at T0",
            "net ignores the residual value of the MAMO left as collateral and unwind of the pump",
            "the oracle is assumed to read the pools' spot price (post-mortem: no TWAP guard)"]}
    _write(a.out, "manipulation_h12", results, {"H12": caps}, out)


def _fmt(d):
    return "  n/a " if d is None else f"{d*100:6.2f}%"


def _keep_other_cases(out_dir, name, rows, caps):
    """Merge into an existing result file: rows and capsules of the cases computed in this
    run replace their old ones; other cases already in the file are kept, so running one
    case does not drop the rest."""
    path = os.path.join(out_dir, f"{name}.json")
    if not os.path.exists(path):
        return rows, caps
    old = json.load(open(path, encoding="utf-8"))
    done = {r["case"] for r in rows}
    kept = [r for r in old.get("rows", []) if r.get("case") not in done]
    merged_caps = {k: v for k, v in (old.get("capsules") or {}).items() if k not in done}
    merged_caps.update(caps)
    if kept:
        print(f"kept {len(kept)} rows of {sorted({r['case'] for r in kept})} already in {path}")
    merged = sorted(kept + rows, key=lambda r: (r["case"], r.get("hours_from_t0", 0), r.get("size_usd", 0)))
    return merged, merged_caps


def _write(out_dir, name, rows, caps, meta):
    os.makedirs(out_dir, exist_ok=True)
    if rows:
        with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
            fields = list(dict.fromkeys(k for r in rows for k in r))   # union, first-seen order
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)
    with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "meta": meta, "rows": rows, "capsules": caps}, f, indent=1, default=str)
    print(f"wrote {out_dir}/{name}.csv and .json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("exit-curves")
    e.add_argument("--cases", nargs="+", default=["H01", "H02", "H04"],
                   choices=["H01", "H02", "H04", "H12"])
    e.add_argument("--mamo-pools")
    e.add_argument("--out", default="results/defi/micro")
    m = sp.add_parser("manipulation")
    m.add_argument("--mamo-pools")
    m.add_argument("--out", default="results/defi/micro")
    a = ap.parse_args()
    {"exit-curves": cmd_exit_curves, "manipulation": cmd_manipulation}[a.cmd](a)


if __name__ == "__main__":
    main()
