"""Record one daily, detailed snapshot of the AXL market data (DefiLlama Markets API).

Run by GitHub Actions once a day (.github/workflows/record_axl_market_history.yml).
The API only holds the last 24 hours, so every indicator shown on the "AXL Markets" tab is stored
here once a day; the tab then draws the "over time" charts from these files.

Two long-format CSV files are written (columns: date, category, name, metric, value):

  data/axl_market_history.csv         aggregated indicators
      category = overall | segment | venue | venue_segment | exchange | quote | depth
  data/axl_market_latest.json         latest raw API payload (dashboard fallback)
  data/axl_market_detail_history.csv  one row per market and indicator
      category = market   (name = "<Exchange> | <SYMBOL> | <segment>")

Re-running on the same day REPLACES that day's rows, so the job is safe to run twice.

Usage:
    python scripts/record_axl_market_snapshot.py
    python scripts/record_axl_market_snapshot.py --date 2026-11-20 --out x.csv --out-markets y.csv
"""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

try:  # impersonates a real browser; avoids HTTP 403 from bot protection
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

API_URL = "https://defillama.com/api/public/markets/axelar"
TICKER = "AXL"

# A snapshot belongs to the UTC day it closes: a run that GitHub delays a little past midnight is still
# stored under the day that just ended.
DAY_OFFSET_HOURS = 2

STABLE_QUOTES = {"usdt", "usdc", "usd", "usdh"}
MAJOR_CEX = ["Binance", "Coinbase", "OKX", "Bybit", "Upbit", "Kraken"]
DEFAULT_BANDS = [0.001, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025, 0.05, 0.1, 0.25]
SEG_LABELS = {"linear_perp": "Perp", "inverse_perp": "Perp (inverse)", "spot": "Spot"}
COLUMNS = ["date", "category", "name", "metric", "value"]
DEPTH_CAP = 1_000_000  # some exchanges (e.g. BingX) report exactly $1,000,000 as a capped placeholder


# --------------------------------------------------------------------------------------------
# helpers (same definitions as the dashboard)
# --------------------------------------------------------------------------------------------
def wavg(values, weights):
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan


def clean_depth(lst):
    """Replace capped placeholder cells ($1,000,000) and everything after them with the last real value
    (a lower bound of the true liquidity instead of an inflated number)."""
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


def band_label(b):
    return f"±{b * 100:.2f}%"


NUM_COLS = ["price", "best_bid", "best_ask", "volume_24h", "volume_prev_24h", "price_change_24h", "oi_usd",
            "oi_prev_usd", "funding_rate_8h", "max_leverage", "taker_fee", "maker_fee", "mark_price",
            "index_price", "nvol_reported", "nvol_normalized", "nvol_active_liquidity"]


def flatten(payload):
    rows = []
    for venue in ["cex", "dex"]:
        for seg, markets in (payload.get(venue) or {}).items():
            for m in markets or []:
                nv = m.get("nvol") or {}
                rows.append({
                    "venue": venue.upper(), "segment": SEG_LABELS.get(seg, seg),
                    "exchange": m.get("display_name"), "symbol": str(m.get("symbol") or "").upper(),
                    "quote": (m.get("quote") or "").lower(),
                    "price": m.get("price"), "best_bid": m.get("best_bid"), "best_ask": m.get("best_ask"),
                    "volume_24h": m.get("volume_24h"), "volume_prev_24h": m.get("volume_prev_24h"),
                    "price_change_24h": m.get("price_change_24h"), "oi_usd": m.get("oi_usd"),
                    "oi_prev_usd": m.get("oi_prev_usd"), "funding_rate_8h": m.get("funding_rate_8h"),
                    "max_leverage": m.get("max_leverage"), "taker_fee": m.get("taker_fee"),
                    "maker_fee": m.get("maker_fee"), "mark_price": m.get("mark_price"),
                    "index_price": m.get("index_price"),
                    "nvol_reported": nv.get("reported"), "nvol_normalized": nv.get("normalized"),
                    "nvol_active_liquidity": nv.get("active_liquidity"),
                    "depth_bid": m.get("depth_bid_usd"), "depth_ask": m.get("depth_ask_usd"),
                })
    cols = ["venue", "segment", "exchange", "symbol", "quote"] + NUM_COLS + ["depth_bid", "depth_ask"]
    df = pd.DataFrame(rows, columns=cols)
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["market"] = df["exchange"].astype(str) + " | " + df["symbol"] + " | " + df["segment"]
    mid = (df["best_bid"] + df["best_ask"]) / 2
    valid = (df["best_bid"] > 0) & (df["best_ask"] >= df["best_bid"])   # ignore empty or crossed books
    df["spread_pct"] = ((df["best_ask"] - df["best_bid"]) / mid * 100).where(valid)
    return df


# --------------------------------------------------------------------------------------------
# indicator computation
# --------------------------------------------------------------------------------------------
class Rows:
    """Collects (category, name, metric, value) and drops missing / non-finite numbers."""

    def __init__(self):
        self.items = []

    def add(self, category, name, metric, value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        if math.isnan(v) or math.isinf(v):
            return
        self.items.append((category, str(name), metric, float(f"{v:.10g}")))


def compute(payload):
    """Return (aggregate rows, per-market rows) for one API payload."""
    mk = flatten(payload)
    bands = payload.get("depth_bands") or DEFAULT_BANDS
    agg, det = Rows(), Rows()

    perp = mk["segment"].isin(["Perp", "Perp (inverse)"])
    spot = mk["segment"] == "Spot"
    vol = mk["volume_24h"]
    total_vol = vol.sum()
    perp_vol, spot_vol = vol[perp].sum(), vol[spot].sum()
    cex_vol, dex_vol = vol[mk["venue"] == "CEX"].sum(), vol[mk["venue"] == "DEX"].sum()

    both = mk[mk["volume_24h"].notna() & mk["volume_prev_24h"].notna()]
    prev_sum = both["volume_prev_24h"].sum()
    vol_change = (both["volume_24h"].sum() / prev_sum - 1) * 100 if prev_sum > 0 else np.nan

    pk = mk[perp]
    oi = pk["oi_usd"].sum(min_count=1)
    oi_both = pk[pk["oi_usd"].notna() & pk["oi_prev_usd"].notna()]
    oi_prev = oi_both["oi_prev_usd"].sum()
    oi_change = (oi_both["oi_usd"].sum() / oi_prev - 1) * 100 if oi_prev > 0 else np.nan

    # ---- funding
    funding_8h = wavg(pk["funding_rate_8h"], pk["oi_usd"]) * 100
    fk = pk[pk["funding_rate_8h"].notna() & (pk["oi_usd"] >= 10_000)]
    f_oi = fk["oi_usd"].sum()
    pos_share = fk.loc[fk["funding_rate_8h"] > 0, "oi_usd"].sum() / f_oi * 100 if f_oi > 0 else np.nan
    api_perp_fund = ((payload.get("segments") or {}).get("linear_perp") or {}).get("funding_rate_8h")

    # ---- prices (USD-pegged quotes only, like the Prices & Spreads tab)
    usd = mk[mk["quote"].isin(STABLE_QUOTES) & mk["price"].notna() & (mk["volume_24h"].fillna(0) > 0)]
    price_med = usd["price"].median() if len(usd) else np.nan
    price_vwap = wavg(usd["price"], usd["volume_24h"]) if len(usd) else np.nan
    dispersion = wavg((usd["price"] / price_med - 1).abs() * 100, usd["volume_24h"]) if len(usd) else np.nan
    max_spread = (usd["price"].max() - usd["price"].min()) / price_med * 100 if len(usd) and price_med > 0 else np.nan
    usd_sp = usd[usd["spread_pct"].notna()]

    mi = pk[(pk["mark_price"] > 0) & (pk["index_price"] > 0)]
    premium = wavg((mi["mark_price"] / mi["index_price"] - 1) * 100, mi["oi_usd"].fillna(0)) if len(mi) else np.nan

    # ---- exchange concentration
    ex_vol = mk.groupby("exchange")["volume_24h"].sum()
    ex_vol = ex_vol[ex_vol > 0].sort_values(ascending=False)
    ex_tot = ex_vol.sum()
    top1 = ex_vol.iloc[0] / ex_tot * 100 if len(ex_vol) and ex_tot > 0 else np.nan
    top3 = ex_vol.iloc[:3].sum() / ex_tot * 100 if len(ex_vol) and ex_tot > 0 else np.nan
    hhi = float(((ex_vol / ex_tot) ** 2).sum() * 10000) if len(ex_vol) and ex_tot > 0 else np.nan
    names = set(mk["exchange"].dropna())

    # ---- normalised volume
    nv = mk[mk["nvol_reported"].notna() & mk["nvol_normalized"].notna() & (mk["nvol_reported"] > 0)]
    nv_rep, nv_norm = nv["nvol_reported"].sum(), nv["nvol_normalized"].sum()

    # ---- depth (USD-quoted markets only, placeholder cells cleaned — same as the Liquidity Depth tab)
    du = mk[mk["quote"].isin(STABLE_QUOTES)]
    bid_tot, ask_tot = np.zeros(len(bands)), np.zeros(len(bands))
    ex_d2 = {}
    i2 = int(np.argmin([abs(b - 0.02) for b in bands]))
    for _, r in du.iterrows():
        b, a = clean_depth(r["depth_bid"]), clean_depth(r["depth_ask"])
        for i in range(len(bands)):
            bid_tot[i] += depth_at(b, i)
            ask_tot[i] += depth_at(a, i)
        ex_d2[r["exchange"]] = ex_d2.get(r["exchange"], 0.0) + depth_at(b, i2) + depth_at(a, i2)
    depth = bid_tot + ask_tot
    d1, d2, d5 = (depth[int(np.argmin([abs(b - t) for b in bands]))] for t in (0.01, 0.02, 0.05))
    imbalance = (bid_tot[i2] - ask_tot[i2]) / depth[i2] * 100 if depth[i2] > 0 else np.nan

    # ================= overall =================
    o = {
        "volume_24h": total_vol, "volume_prev_24h": prev_sum, "volume_change_pct": vol_change,
        "api_total_volume": payload.get("total_volume_24h"), "api_total_oi": payload.get("total_oi_usd"),
        "perp_volume": perp_vol, "spot_volume": spot_vol, "cex_volume": cex_vol, "dex_volume": dex_vol,
        "perp_share_pct": perp_vol / total_vol * 100 if total_vol > 0 else np.nan,
        "dex_share_pct": dex_vol / total_vol * 100 if total_vol > 0 else np.nan,
        "oi_usd": oi, "oi_prev_usd": oi_prev, "oi_change_pct": oi_change,
        "oi_to_perp_volume": oi / perp_vol if perp_vol > 0 and pd.notna(oi) else np.nan,
        "funding_8h_pct": funding_8h, "funding_annualized_pct": funding_8h * 3 * 365,
        "funding_api_8h_pct": None if api_perp_fund is None else api_perp_fund * 100,
        "funding_min_pct": fk["funding_rate_8h"].min() * 100 if len(fk) else np.nan,
        "funding_max_pct": fk["funding_rate_8h"].max() * 100 if len(fk) else np.nan,
        "funding_positive_oi_share_pct": pos_share,
        "max_leverage": pk["max_leverage"].max() if len(pk) else np.nan,
        "price_median": price_med, "price_vwap": price_vwap,
        "price_min": usd["price"].min() if len(usd) else np.nan,
        "price_max": usd["price"].max() if len(usd) else np.nan,
        "price_dispersion_pct": dispersion, "max_cross_market_spread_pct": max_spread,
        "price_change_pct": wavg(mk["price_change_24h"], mk["volume_24h"]) * 100,
        "avg_spread_pct": wavg(usd_sp["spread_pct"], usd_sp["volume_24h"]) if len(usd_sp) else np.nan,
        "median_spread_pct": usd_sp["spread_pct"].median() if len(usd_sp) else np.nan,
        "mark_index_premium_pct": premium,
        "avg_taker_fee_pct": wavg(mk["taker_fee"], mk["volume_24h"]) * 100,
        "avg_maker_fee_pct": wavg(mk["maker_fee"], mk["volume_24h"]) * 100,
        "exchanges": len(names), "markets": len(mk), "active_markets": int((vol > 0).sum()),
        "perp_exchanges": mk.loc[perp, "exchange"].nunique(), "spot_exchanges": mk.loc[spot, "exchange"].nunique(),
        "cex_exchanges": mk.loc[mk["venue"] == "CEX", "exchange"].nunique(),
        "dex_markets": int((mk["venue"] == "DEX").sum()),
        "major_cex": sum(1 for x in MAJOR_CEX if x in names),
        "top_exchange_share_pct": top1, "top3_exchange_share_pct": top3, "exchange_hhi": hhi,
        "nvol_reported": nv_rep, "nvol_normalized": nv_norm,
        "nvol_normalized_ratio_pct": nv_norm / nv_rep * 100 if nv_rep > 0 else np.nan,
        "active_liquidity_usd": mk.loc[mk["nvol_active_liquidity"] > 0, "nvol_active_liquidity"].sum(),
        "depth_1pct": d1, "depth_2pct": d2, "depth_5pct": d5,
        "depth_to_volume": d2 / total_vol if total_vol > 0 else np.nan,
        "depth_imbalance_2pct_pct": imbalance,
    }
    for k, v in o.items():
        agg.add("overall", TICKER, k, v)

    # ================= segments (API values, as in the tab's segment table) =================
    for key, s in (payload.get("segments") or {}).items():
        lbl = SEG_LABELS.get(key, key)
        for metric, field, mult in [
            ("volume_24h", "volume_24h", 1), ("volume_prev_24h", "volume_prev_24h", 1),
            ("oi_usd", "oi_usd", 1), ("oi_prev_usd", "oi_prev_usd", 1),
            ("exchanges", "exchange_count", 1), ("markets", "market_count", 1), ("avg_price", "price", 1),
            ("price_change_pct", "price_change_24h", 100), ("funding_8h_pct", "funding_rate_8h", 100),
            ("leverage_min", "leverage_min", 1), ("leverage_max", "leverage_max", 1)]:
            v = s.get(field)
            agg.add("segment", lbl, metric, None if v is None else v * mult)

    # ================= venue / venue x segment =================
    for venue, g in mk.groupby("venue"):
        agg.add("venue", venue, "volume_24h", g["volume_24h"].sum())
        agg.add("venue", venue, "oi_usd", g["oi_usd"].sum(min_count=1))
        agg.add("venue", venue, "markets", len(g))
        agg.add("venue", venue, "exchanges", g["exchange"].nunique())
    for (venue, seg), g in mk.groupby(["venue", "segment"]):
        agg.add("venue_segment", f"{venue} {seg}", "volume_24h", g["volume_24h"].sum())
        agg.add("venue_segment", f"{venue} {seg}", "oi_usd", g["oi_usd"].sum(min_count=1))

    # ================= exchanges =================
    for ex, g in mk.groupby("exchange"):
        gp = g[g["segment"].isin(["Perp", "Perp (inverse)"])]
        gs = g[g["quote"].isin(STABLE_QUOTES) & g["spread_pct"].notna() & (g["volume_24h"].fillna(0) > 0)]
        agg.add("exchange", ex, "volume_24h", g["volume_24h"].sum())
        agg.add("exchange", ex, "oi_usd", g["oi_usd"].sum(min_count=1))
        agg.add("exchange", ex, "markets", len(g))
        agg.add("exchange", ex, "funding_8h_pct", wavg(gp["funding_rate_8h"], gp["oi_usd"]) * 100)
        agg.add("exchange", ex, "taker_fee_pct", wavg(g["taker_fee"], g["volume_24h"]) * 100)
        agg.add("exchange", ex, "avg_spread_pct", wavg(gs["spread_pct"], gs["volume_24h"]) if len(gs) else np.nan)
        if ex in ex_d2:
            agg.add("exchange", ex, "depth_2pct", ex_d2[ex])

    # ================= quote assets =================
    for q, g in mk.groupby("quote"):
        agg.add("quote", q or "n/a", "volume_24h", g["volume_24h"].sum())
        agg.add("quote", q or "n/a", "markets", len(g))

    # ================= depth curve =================
    for i, b in enumerate(bands):
        agg.add("depth", band_label(b), "bid", bid_tot[i])
        agg.add("depth", band_label(b), "ask", ask_tot[i])
        agg.add("depth", band_label(b), "total", depth[i])

    # ================= per market =================
    for name, g in mk.groupby("market"):
        gp = g[g["segment"].isin(["Perp", "Perp (inverse)"])]
        det.add("market", name, "volume_24h", g["volume_24h"].sum(min_count=1))
        det.add("market", name, "oi_usd", g["oi_usd"].sum(min_count=1))
        det.add("market", name, "funding_8h_pct",
                (wavg(gp["funding_rate_8h"], gp["oi_usd"].fillna(0) + 1e-9) if len(gp) else np.nan) * 100)
        det.add("market", name, "price", g["price"].mean())
        det.add("market", name, "spread_pct", g["spread_pct"].mean())

    return agg.items, det.items


# --------------------------------------------------------------------------------------------
# fetching / writing
# --------------------------------------------------------------------------------------------
def fetch_json():
    attempts = []
    if cffi_requests is not None:
        attempts.append(lambda: cffi_requests.get(API_URL, impersonate="chrome",
                                                  headers={"Referer": "https://defillama.com/"}, timeout=60))
    attempts.append(lambda: requests.get(API_URL, timeout=60, headers={
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


def fetch_with_retry(tries=3):
    err = None
    for i in range(tries):
        payload, err = fetch_json()
        if payload is not None:
            return payload, None
        time.sleep(5 * (i + 1))
    return None, err


def write_day(path, day, items):
    """Replace every row of `day` in the CSV at `path` with `items`."""
    new = pd.DataFrame([(day, c, n, m, v) for c, n, m, v in items], columns=COLUMNS)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        old = pd.read_csv(path, dtype={"date": str, "name": str, "category": str, "metric": str},
                          keep_default_na=False, na_values=[""])
        old = old[old["date"] != day]
        merged = pd.concat([old, new], ignore_index=True)
    else:
        merged = new
    merged = merged.sort_values(["date", "category", "name", "metric"], kind="stable")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    merged.to_csv(path, index=False)
    return len(new), merged["date"].nunique()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/axl_market_history.csv")
    ap.add_argument("--out-markets", default="data/axl_market_detail_history.csv")
    ap.add_argument("--out-json", default="data/axl_market_latest.json",
                    help="latest raw API payload; the dashboard shows it if the live API refuses the request")
    ap.add_argument("--date", default=None, help="override the snapshot date (YYYY-MM-DD)")
    args = ap.parse_args()

    captured = datetime.now(timezone.utc)
    day = args.date or (captured - timedelta(hours=DAY_OFFSET_HOURS)).date().isoformat()

    payload, err = fetch_with_retry()
    if payload is None:
        print(f"::error::Could not fetch {API_URL}: {str(err)[:300]}")
        sys.exit(1)
    try:
        agg, det = compute(payload)
    except Exception as e:
        print(f"::error::Processing error: {e}")
        sys.exit(1)
    if not agg:
        print("::error::No indicator could be computed; nothing written.")
        sys.exit(1)

    folder = os.path.dirname(args.out_json)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    n1, d1 = write_day(args.out, day, agg)
    n2, d2 = write_day(args.out_markets, day, det)
    print(f"Recorded {n1} aggregate rows ({d1} days in file) and {n2} per-market rows ({d2} days) for {day}.")


if __name__ == "__main__":
    main()
