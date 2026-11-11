"""Record one daily snapshot of Axelar's TVL and AXL's FDV.

Run by GitHub Actions once a day (see .github/workflows/record_tvl_history.yml).
It stores, in a single "long" CSV file (data/axelar_tvl_history.csv):

    category      name        value
    total_tvl     Total       Total Axelar TVL (USD)
    fdv           AXL FDV     AXL price x total supply (USD)
    axl_price     AXL         AXL price (USD)
    axl_supply    AXL         AXL total supply
    asset_type    ITS / non-ITS     TVL per asset type (USD)
    chain         <chain>     TVL per chain (USD)

The calculations are the same ones the TVL tab uses on the live data, so history and live numbers agree.
Re-running on the same day overwrites that day's rows (nothing is duplicated).

Usage:
    python scripts/record_tvl_snapshot.py
    python scripts/record_tvl_snapshot.py --out other.csv --date 2026-11-10
"""
import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

try:  # impersonates a real browser; helps if the API answers plain python requests with HTTP 403
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

TVL_URL = "https://api.axelarscan.io/api/getTVL"
PRICE_URL = "https://api.axelarscan.io/api/getTokensPrice?symbol=AXL"
SUPPLY_URL = "https://api.axelarscan.io/api/getTotalSupply"

# A snapshot belongs to the UTC day it closes: a run that GitHub delays slightly past midnight
# is still stored under the day that just ended.
DAY_OFFSET_HOURS = 2
COLUMNS = ["date", "captured_at_utc", "category", "name", "value"]


def get_json(url, attempts=3):
    last_err = None
    for i in range(attempts):
        tries = []
        if cffi_requests is not None:
            tries.append(lambda: cffi_requests.get(url, impersonate="chrome", timeout=60))
        tries.append(lambda: requests.get(url, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"}))
        for attempt in tries:
            try:
                r = attempt()
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
        time.sleep(5 * (i + 1))
    raise last_err


def tvl_rows(payload):
    """Same parsing and formulas as the TVL tab. Returns (total, asset_type Series, chain Series)."""
    rows = []
    for asset in payload["data"]:
        price = asset.get("price", None)
        tvl_data = asset.get("tvl", {}) or {}
        for chain, details in tvl_data.items():
            rows.append({
                "Asset ID": asset.get("asset", ""),
                "Asset Type": asset.get("assetType", ""),
                "Chain": chain,
                "Total TVL": details.get("total", None),
                "Price (USD)": price,
                "Total Asset Value (USD)": asset.get("value", None),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("getTVL returned no chain rows")
    for col in ["Total TVL", "Price (USD)", "Total Asset Value (USD)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    unique_assets = df.drop_duplicates(subset=["Asset ID"]).copy()
    total = float(unique_assets["Total Asset Value (USD)"].sum())

    unique_assets["label"] = unique_assets["Asset Type"].apply(lambda x: "ITS" if str(x).lower() == "its" else "non-ITS")
    by_type = unique_assets.groupby("label")["Total Asset Value (USD)"].sum()

    df["TVL (USD)"] = (df["Total TVL"] * df["Price (USD)"]).round(0)
    by_chain = df.groupby("Chain")["TVL (USD)"].sum()
    return total, by_type, by_chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/axelar_tvl_history.csv")
    ap.add_argument("--date", default=None, help="override the snapshot date (YYYY-MM-DD)")
    args = ap.parse_args()

    captured = datetime.now(timezone.utc)
    day = args.date or (captured - timedelta(hours=DAY_OFFSET_HOURS)).date().isoformat()
    stamp = captured.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, problems = [], []

    def add(category, name, value):
        rows.append({"date": day, "captured_at_utc": stamp, "category": category, "name": name, "value": float(value)})

    # --- TVL: total, per asset type, per chain
    try:
        total, by_type, by_chain = tvl_rows(get_json(TVL_URL))
        if not total > 0:
            raise ValueError(f"total TVL is {total}")
        add("total_tvl", "Total", total)
        for name, v in by_type.items():
            add("asset_type", name, v)
        for name, v in by_chain.items():
            if pd.notna(v):
                add("chain", name, v)
    except Exception as e:
        problems.append(f"TVL not recorded: {e}")

    # --- AXL price, supply and FDV
    try:
        price = float(get_json(PRICE_URL)["AXL"]["price"])
        supply = float(get_json(SUPPLY_URL))
        add("axl_price", "AXL", price)
        add("axl_supply", "AXL", supply)
        add("fdv", "AXL FDV", price * supply)
    except Exception as e:
        problems.append(f"FDV not recorded: {e}")

    for p in problems:
        print(f"::warning::{p[:250]}")
    if not rows:
        print("Nothing could be recorded; no file written.")
        sys.exit(1)

    new = pd.DataFrame(rows, columns=COLUMNS)
    if os.path.exists(args.out) and os.path.getsize(args.out) > 0:
        old = pd.read_csv(args.out, dtype={"date": str})
        merged = pd.concat([old, new], ignore_index=True)
    else:
        merged = new
    merged = merged.reindex(columns=COLUMNS)
    # a partial run (for example only FDV) must not delete rows of other categories, so only exact duplicates go
    merged = merged.drop_duplicates(subset=["date", "category", "name"], keep="last")
    merged = merged.sort_values(["date", "category", "name"])

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f"Recorded {len(rows)} rows for {day}. File now has {len(merged)} rows ({merged['date'].nunique()} days).")


if __name__ == "__main__":
    main()
