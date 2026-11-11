"""Record one daily snapshot of the market indicators of AXL and its competitors.

Run by GitHub Actions once a day (see .github/workflows/record_market_history.yml).
Each run fetches the markets API for every token, computes the indicators and
UPSERTS one row per (date, ticker) into a CSV file, so re-running on the same day simply
overwrites that day's row.

The indicator logic below is copied unchanged from the comparison tab (axl_competitors.py),
so the history and the live comparison always use the same definitions.

Usage:
    python scripts/record_market_snapshot.py                         # -> data/market_history.csv
    python scripts/record_market_snapshot.py --out other.csv --date 2026-11-10
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

try:  # impersonates a real browser; avoids HTTP 403 from the API's bot protection
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

# A snapshot belongs to the UTC day it closes. Taking the time 2 hours back means a run that GitHub
# delays a little past midnight is still stored under the day that just ended.
DAY_OFFSET_HOURS = 2
ID_COLS = ["date", "captured_at_utc", "ticker", "name", "tags", "last_updated"]
EXTRA_COLS = ["api_total_volume", "api_total_oi"]

BASE_URL = "https://defillama.com/api/public/markets/"

TOKENS = [
    ("AXL", "Axelar", "axelar"),
    ("HYPER", "Hyperlane", "Hyperlane"),
    ("LINK", "Chainlink", "Chainlink"),
    ("CELR", "Celer Network", "celer-network"),
    ("DBR", "deBridge", "deBridge"),
    ("SYN", "Synapse", "synapse-2"),
    ("ACX", "Across Protocol", "Across-Protocol"),
    ("STG", "Stargate Finance", "Stargate-finance"),
    ("ZRO", "LayerZero", "LayerZero"),
    ("W", "Wormhole", "wormhole"),
]

STABLE_QUOTES = {"usdt", "usdc", "usd", "usdh"}

MAJOR_CEX = ["Binance", "Coinbase", "OKX", "Bybit", "Upbit", "Kraken"]

DEFAULT_BANDS = [0.001, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025, 0.05, 0.1, 0.25]

METRICS = {
    "volume_24h": ("24h Volume (USD)", "usd", True),
    "volume_change_pct": ("Volume change vs prev 24h (%)", "pct", None),
    "perp_volume": ("Perp volume (USD)", "usd", True),
    "spot_volume": ("Spot volume (USD)", "usd", True),
    "perp_share_pct": ("Perp share of volume (%)", "pct", None),
    "dex_share_pct": ("DEX share of volume (%)", "pct", None),
    "oi_usd": ("Open interest (USD)", "usd", True),
    "oi_change_pct": ("OI change vs prev (%)", "pct", None),
    "oi_to_perp_volume": ("OI / perp volume", "ratio", None),
    "funding_8h_pct": ("Funding rate, OI-weighted (8h, %)", "pct", None),
    "funding_annualized_pct": ("Funding annualised (%)", "pct", None),
    "max_leverage": ("Max leverage (x)", "num", True),
    "price": ("Price (USD, median)", "num", None),
    "price_change_pct": ("Price change 24h (vol-weighted, %)", "pct", None),
    "price_dispersion_pct": ("Cross-exchange price dispersion (%)", "pct", False),
    "avg_spread_pct": ("Avg bid/ask spread (vol-weighted, %)", "pct", False),
    "depth_1pct": ("Depth ±1% (USD)", "usd", True),
    "depth_2pct": ("Depth ±2% (USD)", "usd", True),
    "depth_5pct": ("Depth ±5% (USD)", "usd", True),
    "depth_to_volume": ("Depth ±2% / 24h volume", "ratio", True),
    "avg_taker_fee_pct": ("Avg base taker fee (vol-weighted, %)", "pct", False),
    "exchanges": ("Exchanges", "num", True),
    "markets": ("Markets", "num", True),
    "perp_exchanges": ("Exchanges with perps", "num", True),
    "spot_exchanges": ("Exchanges with spot", "num", True),
    "dex_markets": ("DEX markets", "num", True),
    "major_cex": (f"Major CEX listings (of {len(MAJOR_CEX)})", "num", True),
    "top_exchange_share_pct": ("Top exchange share of volume (%)", "pct", False),
}

def wavg(values, weights):
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan

DEPTH_CAP = 1_000_000  # some exchanges (e.g. BingX) report exactly $1,000,000 as a capped placeholder

def clean_depth(lst):
    """Replace capped placeholder cells ($1,000,000) and everything after them with the last real value.

    The result is a lower bound of the true liquidity instead of an inflated number."""
    if not isinstance(lst, list):
        return lst
    out, last, capped = [], None, False
    for x in lst:
        if capped or (x is not None and abs(float(x) - DEPTH_CAP) < 1e-6):
            capped = True
            out.append(last)
        else:
            out.append(x)
            if x is not None:
                last = x
    return out

def depth_at(lst, idx):
    if isinstance(lst, list) and idx < len(lst) and lst[idx] is not None:
        return float(lst[idx])
    return 0.0

def band_index(bands, target):
    return int(np.argmin([abs(b - target) for b in bands]))

MARKET_COLS = ["venue", "segment", "exchange", "symbol", "quote", "price", "best_bid", "best_ask", "volume_24h",
               "volume_prev_24h", "price_change_24h", "oi_usd", "oi_prev_usd", "funding_rate_8h", "max_leverage",
               "taker_fee", "nvol_reported", "nvol_normalized", "depth_bid", "depth_ask"]

NUM_COLS = ["price", "best_bid", "best_ask", "volume_24h", "volume_prev_24h", "price_change_24h", "oi_usd",
            "oi_prev_usd", "funding_rate_8h", "max_leverage", "taker_fee", "nvol_reported", "nvol_normalized"]

def flatten(payload):
    rows = []
    for venue in ["cex", "dex"]:
        for seg, markets in (payload.get(venue) or {}).items():
            for m in markets or []:
                nv = m.get("nvol") or {}
                rows.append({
                    "venue": venue.upper(), "segment": seg, "exchange": m.get("display_name"),
                    "symbol": m.get("symbol"), "quote": (m.get("quote") or "").lower(),
                    "price": m.get("price"), "best_bid": m.get("best_bid"), "best_ask": m.get("best_ask"),
                    "volume_24h": m.get("volume_24h"), "volume_prev_24h": m.get("volume_prev_24h"),
                    "price_change_24h": m.get("price_change_24h"), "oi_usd": m.get("oi_usd"),
                    "oi_prev_usd": m.get("oi_prev_usd"), "funding_rate_8h": m.get("funding_rate_8h"),
                    "max_leverage": m.get("max_leverage"), "taker_fee": m.get("taker_fee"),
                    "nvol_reported": nv.get("reported"), "nvol_normalized": nv.get("normalized"),
                    "depth_bid": m.get("depth_bid_usd"), "depth_ask": m.get("depth_ask_usd"),
                })
    df = pd.DataFrame(rows, columns=MARKET_COLS)
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def summarize(ticker, name, payload):
    """Return (metrics dict, depth curve dict, exchange-volume dict) for one token."""
    mk = flatten(payload)
    bands = payload.get("depth_bands") or DEFAULT_BANDS
    perp = mk["segment"].isin(["linear_perp", "inverse_perp"])
    spot = mk["segment"] == "spot"

    total_vol = mk["volume_24h"].sum()
    perp_vol = mk.loc[perp, "volume_24h"].sum()
    spot_vol = mk.loc[spot, "volume_24h"].sum()
    dex_vol = mk.loc[mk["venue"] == "DEX", "volume_24h"].sum()

    both = mk[mk["volume_24h"].notna() & mk["volume_prev_24h"].notna()]
    prev_sum = both["volume_prev_24h"].sum()
    vol_change = (both["volume_24h"].sum() / prev_sum - 1) * 100 if prev_sum > 0 else np.nan

    pk = mk[perp]
    oi = pk["oi_usd"].sum(min_count=1)
    oi_both = pk[pk["oi_usd"].notna() & pk["oi_prev_usd"].notna()]
    oi_prev = oi_both["oi_prev_usd"].sum()
    oi_change = (oi_both["oi_usd"].sum() / oi_prev - 1) * 100 if oi_prev > 0 else np.nan

    funding_8h = wavg(pk["funding_rate_8h"], pk["oi_usd"]) * 100
    usd = mk[mk["quote"].isin(STABLE_QUOTES) & (mk["price"] > 0) & (mk["volume_24h"] > 0)]
    price_med = usd["price"].median() if len(usd) else np.nan
    dispersion = wavg((usd["price"] / price_med - 1).abs() * 100, usd["volume_24h"]) if len(usd) else np.nan

    mid = (mk["best_bid"] + mk["best_ask"]) / 2
    valid = (mk["best_bid"] > 0) & (mk["best_ask"] >= mk["best_bid"])   # ignore empty or crossed books
    spread_pct = ((mk["best_ask"] - mk["best_bid"]) / mid * 100).where(valid)

    # aggregated order-book depth (sum over all markets, USD-denominated)
    bid_tot = np.zeros(len(bands))
    ask_tot = np.zeros(len(bands))
    for b, a in zip(mk["depth_bid"], mk["depth_ask"]):
        b, a = clean_depth(b), clean_depth(a)
        for i in range(len(bands)):
            bid_tot[i] += depth_at(b, i)
            ask_tot[i] += depth_at(a, i)
    depth = bid_tot + ask_tot
    d1, d2, d5 = (depth[band_index(bands, t)] for t in (0.01, 0.02, 0.05))

    ex_vol = mk.groupby("exchange")["volume_24h"].sum()
    ex_vol = ex_vol[ex_vol > 0]
    top_share = ex_vol.max() / ex_vol.sum() * 100 if len(ex_vol) and ex_vol.sum() > 0 else np.nan
    names = set(mk["exchange"].dropna())

    metrics = {
        "ticker": ticker, "name": name, "tags": ", ".join(payload.get("tags") or []),
        "volume_24h": total_vol, "volume_change_pct": vol_change,
        "perp_volume": perp_vol, "spot_volume": spot_vol,
        "perp_share_pct": perp_vol / total_vol * 100 if total_vol > 0 else np.nan,
        "dex_share_pct": dex_vol / total_vol * 100 if total_vol > 0 else np.nan,
        "oi_usd": oi, "oi_change_pct": oi_change,
        "oi_to_perp_volume": oi / perp_vol if perp_vol > 0 and pd.notna(oi) else np.nan,
        "funding_8h_pct": funding_8h, "funding_annualized_pct": funding_8h * 3 * 365,
        "max_leverage": pk["max_leverage"].max() if len(pk) else np.nan,
        "price": price_med, "price_change_pct": wavg(mk["price_change_24h"], mk["volume_24h"]) * 100,
        "price_dispersion_pct": dispersion, "avg_spread_pct": wavg(spread_pct, mk["volume_24h"]),
        "depth_1pct": d1, "depth_2pct": d2, "depth_5pct": d5,
        "depth_to_volume": d2 / total_vol if total_vol > 0 else np.nan,
        "avg_taker_fee_pct": wavg(mk["taker_fee"], mk["volume_24h"]) * 100,
        "last_updated": payload.get("last_updated"),
        "api_total_volume": payload.get("total_volume_24h"), "api_total_oi": payload.get("total_oi_usd"),
        "exchanges": len(names), "markets": len(mk),
        "perp_exchanges": mk.loc[perp, "exchange"].nunique(), "spot_exchanges": mk.loc[spot, "exchange"].nunique(),
        "dex_markets": int((mk["venue"] == "DEX").sum()),
        "major_cex": sum(1 for x in MAJOR_CEX if x in names),
        "top_exchange_share_pct": top_share,
    }
    curve = {"bands": list(bands), "depth": depth.tolist()}
    return metrics, curve, ex_vol.to_dict()

def fetch_json(slug):
    url = BASE_URL + slug
    attempts = []
    if cffi_requests is not None:
        attempts.append(lambda: cffi_requests.get(url, impersonate="chrome",
                                                  headers={"Referer": "https://defillama.com/"}, timeout=60))
    attempts.append(lambda: requests.get(url, timeout=60, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json", "Referer": "https://defillama.com/"}))
    errors = []
    for attempt in attempts:
        try:
            r = attempt()
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            errors.append(str(e))
    return None, " | ".join(errors)

def fetch_with_retry(slug, attempts=3):
    err = None
    for i in range(attempts):
        payload, err = fetch_json(slug)
        if payload is not None:
            return payload, None
        time.sleep(5 * (i + 1))
    return None, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/market_history.csv")
    ap.add_argument("--date", default=None, help="override the snapshot date (YYYY-MM-DD)")
    args = ap.parse_args()

    captured = datetime.now(timezone.utc)
    day = args.date or (captured - timedelta(hours=DAY_OFFSET_HOURS)).date().isoformat()
    columns = ID_COLS + list(METRICS.keys()) + EXTRA_COLS

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(lambda t: fetch_with_retry(t[2]), TOKENS))

    rows, failed = [], {}
    for (ticker, name, _slug), (payload, err) in zip(TOKENS, results):
        if payload is None:
            failed[ticker] = err
            continue
        try:
            m, _curve, _ex_vol = summarize(ticker, name, payload)
        except Exception as e:
            failed[ticker] = f"processing error: {e}"
            continue
        m["date"] = day
        m["captured_at_utc"] = captured.strftime("%Y-%m-%dT%H:%M:%SZ")
        absent = [c for c in columns if c not in m]
        if absent:
            failed[ticker] = f"missing computed fields: {absent}"
            continue
        rows.append({c: m[c] for c in columns})

    for t, e in failed.items():
        print(f"::warning::{t} was not recorded: {str(e)[:200]}")
    if not rows:
        print("No token could be recorded; nothing written.")
        sys.exit(1)

    new = pd.DataFrame(rows, columns=columns)
    if os.path.exists(args.out) and os.path.getsize(args.out) > 0:
        old = pd.read_csv(args.out, dtype={"date": str})
        merged = pd.concat([old, new], ignore_index=True)
    else:
        merged = new
    merged = merged.reindex(columns=columns)
    merged = merged.drop_duplicates(subset=["date", "ticker"], keep="last")
    order = {t[0]: i for i, t in enumerate(TOKENS)}
    merged = merged.assign(_o=merged["ticker"].map(order)).sort_values(["date", "_o"]).drop(columns="_o")

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f"Recorded {len(rows)}/{len(TOKENS)} tokens for {day}. File now has {len(merged)} rows "
          f"({merged['date'].nunique()} days).")


if __name__ == "__main__":
    main()
