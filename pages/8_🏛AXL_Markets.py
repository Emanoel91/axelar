import io
import json
import os
import time
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title ------------------------------------------------------------------------------------------------------------
st.title("🏛️ AXL Market Structure (CEX & DEX)")
st.info("⏳ Market data is fetched from the DefiLlama Markets API and may take a few moments to load.")

# ==================================================
# Configuration
# ==================================================
API_URL = "https://defillama.com/api/public/markets/axelar"
STABLE_QUOTES = {"usdt", "usdc", "usd", "usdh"}      # quotes that are ~USD (used for price comparison)
SEG_LABELS = {"linear_perp": "Perp", "inverse_perp": "Perp (inverse)", "spot": "Spot"}
SEG_COLORS = {"Perp": "#00B8F4", "Perp (inverse)": "#7B61FF", "Spot": "#FF8A00"}
VENUE_COLORS = {"CEX": "#00B8F4", "DEX": "#FF8A00"}

st.markdown(
    """
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #00B8F4;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 15px;
        color: #888;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# Fetch Data
# ==================================================
LATEST_URL = "https://raw.githubusercontent.com/Emanoel91/axelar/main/data/axl_market_latest.json"
LATEST_LOCAL = "data/axl_market_latest.json"
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://defillama.com/",
}


@st.cache_data(ttl=300)
def load_raw():
    """Live API first (browser-like request); if DefiLlama refuses the server, use the latest recorded snapshot.

    Returns (payload, note) where note is None for live data."""
    errors = []
    for attempt in range(2):
        try:
            try:
                from curl_cffi import requests as cr
                r = cr.get(API_URL, headers=_BROWSER_HEADERS, timeout=30, impersonate="chrome")
            except ImportError:
                r = requests.get(API_URL, headers=_BROWSER_HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json(), None
            errors.append(f"HTTP {r.status_code}")
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
        time.sleep(1.5)

    snap = None
    try:
        r = requests.get(LATEST_URL, timeout=30)
        if r.status_code == 200:
            snap = r.json()
    except Exception:
        pass
    if snap is None and os.path.exists(LATEST_LOCAL):
        with open(LATEST_LOCAL, encoding="utf-8") as f:
            snap = json.load(f)
    if snap is None:
        raise RuntimeError("live API failed (" + "; ".join(errors) + ") and no recorded snapshot is available yet")
    return snap, ("⚠️ DefiLlama refused the live request (" + "; ".join(errors) +
                  "). Showing the latest recorded snapshot instead — last updated: "
                  + str(snap.get("last_updated", "unknown")) + ".")


try:
    raw, data_note = load_raw()
except Exception as e:
    st.error(f"❌ Error fetching market data: {e}")
    st.stop()
if data_note:
    st.warning(data_note)

BANDS = raw.get("depth_bands", [])


# ==================================================
# Helpers
# ==================================================
def depth_at(lst, idx):
    """Safe getter for a depth list (values may be None)."""
    if isinstance(lst, list) and idx < len(lst) and lst[idx] is not None:
        return float(lst[idx])
    return np.nan


DEPTH_CAP = 1_000_000  # some exchanges (e.g. BingX) report exactly $1,000,000 as a capped placeholder


def clean_depth(lst):
    """Replace capped placeholder cells ($1,000,000) and everything after them with the last real value,
    so depth is a lower bound of the real liquidity instead of an inflated number."""
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


def fmt_usd(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    if abs(x) >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.1f}K"
    return f"${x:,.2f}"


def pct_delta(now, prev):
    if prev in (None, 0) or now is None:
        return None
    return (now - prev) / prev * 100


def flatten_markets(raw_json):
    rows = []
    for venue in ["cex", "dex"]:
        for seg, markets in raw_json.get(venue, {}).items():
            for m in markets:
                row = {k: v for k, v in m.items()
                       if k not in ("nvol", "freshness", "depth_ask_usd", "depth_bid_usd")}
                row["venue"] = venue.upper()
                row["segment"] = SEG_LABELS.get(seg, seg)
                for k, v in (m.get("nvol") or {}).items():
                    row[f"nvol_{k}"] = v
                for k, v in (m.get("freshness") or {}).items():
                    row[f"fresh_{k}"] = v
                row["depth_ask_usd"] = m.get("depth_ask_usd")
                row["depth_bid_usd"] = m.get("depth_bid_usd")
                rows.append(row)
    return pd.DataFrame(rows)


dfm = flatten_markets(raw)

num_cols = [
    "price", "best_bid", "best_ask", "index_price", "mark_price", "volume_24h", "volume_prev_24h",
    "volume_change_24h", "price_change_24h", "oi", "oi_usd", "oi_prev_usd", "oi_change_24h",
    "funding_rate_8h", "funding_period_h", "max_leverage", "maker_fee", "taker_fee",
    "min_order_cost", "contract_size", "nvol_reported", "nvol_normalized", "nvol_active_liquidity",
    "nvol_coverage", "nvol_daily_vol", "nvol_band"
]
for c in num_cols:
    if c in dfm.columns:
        dfm[c] = pd.to_numeric(dfm[c], errors="coerce")

dfm["market_label"] = dfm["display_name"] + " | " + dfm["symbol"].str.upper() + " | " + dfm["segment"]
mid = (dfm["best_bid"] + dfm["best_ask"]) / 2
dfm["spread_pct"] = np.where(mid > 0, (dfm["best_ask"] - dfm["best_bid"]) / mid * 100, np.nan)
dfm["funding_annualized_pct"] = dfm["funding_rate_8h"] * 3 * 365 * 100
dfm["oi_to_volume"] = np.where(dfm["volume_24h"] > 0, dfm["oi_usd"] / dfm["volume_24h"], np.nan)

# ==================================================
# Header KPIs
# ==================================================
last_updated = raw.get("last_updated", "-")
tags = ", ".join(raw.get("tags", [])) or "-"
seg = raw.get("segments", {})
perp_seg = seg.get("linear_perp", {})
spot_seg = seg.get("spot", {})

total_vol = raw.get("total_volume_24h")
prev_total_vol = sum((s.get("volume_prev_24h") or 0) for s in seg.values())
total_oi = raw.get("total_oi_usd")
prev_total_oi = sum((s.get("oi_prev_usd") or 0) for s in seg.values())

st.markdown(f"### 💎 {raw.get('name', 'Axelar')} ({str(raw.get('symbol', 'axl')).upper()}) — Market KPIs")
st.caption(f"Tags: {tags}  |  Dataset last updated: {last_updated}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 Total Volume (24h)", fmt_usd(total_vol), None if pct_delta(total_vol, prev_total_vol) is None
          else f"{pct_delta(total_vol, prev_total_vol):.1f}%")
c2.metric("🧾 Total Open Interest", fmt_usd(total_oi), None if pct_delta(total_oi, prev_total_oi) is None
          else f"{pct_delta(total_oi, prev_total_oi):.1f}%")
c3.metric("🏦 Exchanges", f"{raw.get('exchange_count', 0)}")
c4.metric("🔗 Markets", f"{raw.get('market_count', 0)}")

st.write(" ")
c5, c6, c7, c8 = st.columns(4)
c5.metric("⚡ Perp Volume (24h)", fmt_usd(perp_seg.get("volume_24h")))
c6.metric("💱 Spot Volume (24h)", fmt_usd(spot_seg.get("volume_24h")))
perp_fund = perp_seg.get("funding_rate_8h")
c7.metric("💸 Avg Funding (8h)", "-" if perp_fund is None else f"{perp_fund * 100:.4f}%")
c8.metric("📉 Perp Price Change 24h", "-" if perp_seg.get("price_change_24h") is None
          else f"{perp_seg['price_change_24h'] * 100:.2f}%")

st.write(" ")

# ==================================================
# Daily history (recorded once a day by scripts/record_axl_market_snapshot.py)
# ==================================================
HISTORY_URL = "https://raw.githubusercontent.com/Emanoel91/axelar/main/data/axl_market_history.csv"
HISTORY_LOCAL = "data/axl_market_history.csv"      # used when the GitHub URL cannot be read (e.g. private repo)
DETAIL_URL = "https://raw.githubusercontent.com/Emanoel91/axelar/main/data/axl_market_detail_history.csv"
DETAIL_LOCAL = "data/axl_market_detail_history.csv"
HIST_COLS = ["date", "category", "name", "metric", "value"]

BLUE, ORANGE, PURPLE, GREEN, RED, GREY = "#00B8F4", "#FF8A00", "#7B61FF", "#2CA02C", "#D62728", "#8A8A8A"


def _read_history(url, local):
    text = None
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            text = res.text
    except Exception:
        pass
    if text is None and os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            text = f.read()
    if not text:
        return pd.DataFrame(columns=HIST_COLS)
    h = pd.read_csv(io.StringIO(text), dtype={"category": str, "name": str, "metric": str},
                    keep_default_na=False, na_values=[""])
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["value"] = pd.to_numeric(h["value"], errors="coerce")
    h = h.dropna(subset=["date", "value", "name"])
    return h.drop_duplicates(subset=["date", "category", "name", "metric"], keep="last")


@st.cache_data(ttl=600)
def load_history():
    return _read_history(HISTORY_URL, HISTORY_LOCAL)


@st.cache_data(ttl=600)
def load_detail_history():
    return _read_history(DETAIL_URL, DETAIL_LOCAL)


hist_all = load_history()
n_days_total = hist_all["date"].nunique() if not hist_all.empty else 0

st.markdown("### 📈 Market History (recorded daily)")
RANGES = {"30 days": 30, "90 days": 90, "180 days": 180, "1 year": 365, "All": None}
hr1, hr2 = st.columns([2, 3])
range_choice = hr1.radio("Over-time range", list(RANGES), index=len(RANGES) - 1, horizontal=True)
if RANGES[range_choice] and not hist_all.empty:
    hist_cut = hist_all[hist_all["date"] >= hist_all["date"].max() - pd.Timedelta(days=RANGES[range_choice])]
else:
    hist_cut = hist_all
n_hist_days = hist_cut["date"].nunique() if not hist_cut.empty else 0
hr2.caption(
    f"Days recorded: {n_days_total}"
    + (f"  |  from {hist_cut['date'].min():%Y-%m-%d} to {hist_cut['date'].max():%Y-%m-%d}" if n_hist_days else "")
    + ". The API only keeps the last 24 hours, so the 'over time' charts in each tab below are built from one "
      "snapshot per day, starting from the first recorded day.")
if n_hist_days < 2:
    st.info("📅 The over-time charts need at least 2 recorded days. They appear automatically after the "
            "second daily snapshot.")

HP = (hist_cut.pivot_table(index="date", columns=["category", "name", "metric"], values="value", aggfunc="last")
      .sort_index() if n_hist_days else pd.DataFrame())
_chart_no = [0]


def ser(cat, name, metric):
    """Daily series (date index) of one recorded indicator."""
    key = (cat, name, metric)
    if len(HP.columns) and key in HP.columns:
        return HP[key].dropna()
    return pd.Series(dtype=float)


def names_for(cat, metric):
    return [c[1] for c in HP.columns if c[0] == cat and c[2] == metric] if len(HP.columns) else []


def _show(fig, unit, height, zero_line=False):
    fig.update_layout(template="plotly_white", height=height, hovermode="x unified", xaxis_title="",
                      legend=dict(orientation="h", y=-0.2), margin=dict(t=60))
    if unit == "usd":
        fig.update_yaxes(tickprefix="$", tickformat=".3~s", hoverformat=",.0f")
    elif unit == "pct":
        fig.update_yaxes(ticksuffix="%", hoverformat=",.4f")
    else:
        fig.update_yaxes(hoverformat=",.4f")
    if zero_line:
        fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    _chart_no[0] += 1
    st.plotly_chart(fig, use_container_width=True, key=f"ot_{_chart_no[0]}")


def ot_header(text):
    """Section title above a row of over-time charts (hidden until there is history to draw)."""
    if n_hist_days >= 2:
        st.markdown(f"#### {text}")


def _waiting(title):
    # With fewer than 2 recorded days the notice at the top of the page already explains it.
    if n_hist_days >= 2:
        st.caption(f"📅 {title}: no recorded values in the selected range.")


def ts_chart(title, specs, kind="line", unit="usd", height=400, zero_line=False, stack=False):
    """specs = [(label, category, name, metric, color or None), ...]; kind = line | area | bar | signed_bar."""
    if n_hist_days < 2:
        _waiting(title)
        return
    fig = go.Figure()
    n = 0
    for label, cat, name, metric, color in specs:
        s_ = ser(cat, name, metric)
        if s_.empty:
            continue
        n += 1
        if kind == "signed_bar":
            fig.add_trace(go.Bar(x=s_.index, y=s_.values, name=label,
                                 marker_color=[GREEN if v >= 0 else RED for v in s_.values]))
        elif kind == "bar":
            fig.add_trace(go.Bar(x=s_.index, y=s_.values, name=label, marker_color=color))
        elif kind == "area":
            fig.add_trace(go.Scatter(x=s_.index, y=s_.values, name=label, mode="lines",
                                     line=dict(color=color, width=1.5),
                                     **({"stackgroup": "one"} if stack else {"fill": "tozeroy"})))
        else:
            fig.add_trace(go.Scatter(x=s_.index, y=s_.values, name=label, mode="lines+markers",
                                     line=dict(color=color, width=2), marker=dict(size=5)))
    if n == 0:
        _waiting(title)
        return
    fig.update_layout(title=title, barmode="stack" if (kind == "bar" and stack) else "group",
                      showlegend=n > 1)
    _show(fig, unit, height, zero_line)


def group_chart(title, cat, metric, kind="area", unit="usd", top_n=8, height=420, color_map=None, zero_line=False):
    """One series per name of a category. kind = area (stacked) | share (100 % stacked) | line | bar (stacked).

    Only the top_n names (by latest value) are drawn; for area / share / bar the rest is grouped as 'Others'."""
    if n_hist_days < 2:
        _waiting(title)
        return
    names = names_for(cat, metric)
    if not names:
        _waiting(title)
        return
    wide = pd.DataFrame({n: ser(cat, n, metric) for n in names}).sort_index()
    latest = wide.ffill().iloc[-1].sort_values(ascending=False)
    keep = list(latest.index[:top_n])
    if kind == "line":
        fig = go.Figure()
        for n in keep:
            fig.add_trace(go.Scatter(x=wide.index, y=wide[n], name=n, mode="lines+markers",
                                     line=dict(width=2, color=(color_map or {}).get(n)), marker=dict(size=4),
                                     connectgaps=False))
        fig.update_layout(title=title)
        _show(fig, unit, height, zero_line)
        return
    data = wide[keep].fillna(0.0)
    if len(names) > top_n:
        data["Others"] = wide.drop(columns=keep).fillna(0.0).sum(axis=1)
    order = list(data.columns)
    long_df = data.reset_index().melt(id_vars="date", var_name="name", value_name="value")
    if kind == "bar":
        fig = px.bar(long_df, x="date", y="value", color="name", category_orders={"name": order},
                     color_discrete_map=color_map, title=title)
        fig.update_layout(barmode="stack")
    else:
        fig = px.area(long_df, x="date", y="value", color="name", category_orders={"name": order},
                      color_discrete_map=color_map, title=title, **({"groupnorm": "percent"} if kind == "share" else {}))
    fig.update_layout(legend_title_text="")
    _show(fig, "pct" if kind == "share" else unit, height)


# ==================================================
# Inner Tabs
# ==================================================
tab_overview, tab_price, tab_perp, tab_liq, tab_quality, tab_raw = st.tabs([
    "🌐 Overview", "💰 Prices & Spreads", "⚡ Perpetuals", "🌊 Liquidity Depth", "🧪 Fees & Data Quality", "🗂️ Raw Data"
])

# --------------------------------------------------
# TAB 1 — Overview
# --------------------------------------------------
with tab_overview:
    st.subheader("Perp vs Spot (segments)")
    seg_rows = []
    for k, v in seg.items():
        seg_rows.append({
            "Segment": SEG_LABELS.get(k, k),
            "Exchanges": v.get("exchange_count"),
            "Markets": v.get("market_count"),
            "Volume 24h": v.get("volume_24h"),
            "Volume prev 24h": v.get("volume_prev_24h"),
            "OI (USD)": v.get("oi_usd"),
            "OI prev (USD)": v.get("oi_prev_usd"),
            "Avg price": v.get("price"),
            "Price change 24h %": None if v.get("price_change_24h") is None else v["price_change_24h"] * 100,
            "Avg funding 8h %": None if v.get("funding_rate_8h") is None else v["funding_rate_8h"] * 100,
            "Leverage min": v.get("leverage_min"),
            "Leverage max": v.get("leverage_max"),
        })
    df_seg = pd.DataFrame(seg_rows)
    st.dataframe(df_seg, use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        d = df_seg.melt(id_vars="Segment", value_vars=["Volume 24h", "Volume prev 24h"],
                        var_name="Period", value_name="USD")
        fig = px.bar(d, x="Segment", y="USD", color="Period", barmode="group",
                     title="Volume: Today vs Previous 24h", template="plotly_white", height=420,
                     color_discrete_sequence=["#00B8F4", "#B0B0B0"])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = df_seg.dropna(subset=["OI (USD)"]).melt(id_vars="Segment", value_vars=["OI (USD)", "OI prev (USD)"],
                                                    var_name="Period", value_name="USD")
        fig = px.bar(d, x="Segment", y="USD", color="Period", barmode="group",
                     title="Open Interest: Now vs Previous", template="plotly_white", height=420,
                     color_discrete_sequence=["#00B8F4", "#B0B0B0"])
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Volume & Open Interest by Segment")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Daily 24h Volume by Segment",
                 [(l, "segment", l, "volume_24h", SEG_COLORS[l]) for l in SEG_LABELS.values()],
                 kind="bar", stack=True)
    with oc2:
        ts_chart("Open Interest by Segment",
                 [(l, "segment", l, "oi_usd", SEG_COLORS[l]) for l in SEG_LABELS.values()],
                 kind="area", stack=True)
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Perp & DEX Share of Volume (%)",
                 [("Perp share", "overall", "AXL", "perp_share_pct", BLUE),
                  ("DEX share", "overall", "AXL", "dex_share_pct", ORANGE)], unit="pct")
    with oc2:
        ts_chart("Markets per Segment",
                 [(l, "segment", l, "markets", SEG_COLORS[l]) for l in SEG_LABELS.values()], unit="num")

    st.subheader("CEX vs DEX (totals)")
    tot_rows = []
    for venue, segs in raw.get("totals", {}).items():
        for k, v in segs.items():
            tot_rows.append({
                "Venue": venue.upper(),
                "Segment": SEG_LABELS.get(k, k),
                "Pairs": v.get("pair_count"),
                "OI (USD)": v.get("total_oi_usd") or 0,
                "Volume 24h": v.get("total_volume_24h") or 0,
            })
    df_tot = pd.DataFrame(tot_rows)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(df_tot, x="Venue", y="Volume 24h", color="Segment", barmode="stack",
                     title="24h Volume by Venue & Segment", template="plotly_white", height=420,
                     color_discrete_map=SEG_COLORS)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = px.bar(df_tot[df_tot["OI (USD)"] > 0], x="Venue", y="OI (USD)", color="Segment", barmode="stack",
                     title="Open Interest by Venue & Segment", template="plotly_white", height=420,
                     color_discrete_map=SEG_COLORS)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_tot, use_container_width=True, hide_index=True)

    ot_header("📈 Over time — CEX vs DEX")
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("24h Volume by Venue & Segment", "venue_segment", "volume_24h", kind="area", top_n=6)
    with oc2:
        group_chart("Open Interest by Venue & Segment", "venue_segment", "oi_usd", kind="area", top_n=6)
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("Share of 24h Volume: CEX vs DEX", "venue", "volume_24h", kind="share", color_map=VENUE_COLORS)
    with oc2:
        group_chart("Markets by Venue", "venue", "markets", kind="line", unit="num", color_map=VENUE_COLORS)

    st.subheader("Volume & Open Interest by Exchange")
    vol_ex = dfm.groupby(["display_name", "segment"], as_index=False)["volume_24h"].sum()
    order = (vol_ex.groupby("display_name")["volume_24h"].sum().sort_values(ascending=False).index.tolist())
    fig = px.bar(vol_ex, x="display_name", y="volume_24h", color="segment", barmode="stack",
                 category_orders={"display_name": order}, title="24h Volume by Exchange",
                 labels={"display_name": "Exchange", "volume_24h": "Volume (USD)", "segment": "Segment"},
                 template="plotly_white", height=500, color_discrete_map=SEG_COLORS)
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        oi_ex = dfm.groupby("display_name", as_index=False)["oi_usd"].sum()
        oi_ex = oi_ex[oi_ex["oi_usd"] > 0].sort_values("oi_usd", ascending=False)
        fig = px.bar(oi_ex, x="display_name", y="oi_usd", title="Open Interest by Exchange",
                     labels={"display_name": "Exchange", "oi_usd": "OI (USD)"},
                     template="plotly_white", height=450, color_discrete_sequence=["#00B8F4"])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        share = vol_ex.groupby("display_name", as_index=False)["volume_24h"].sum().sort_values(
            "volume_24h", ascending=False)
        top = share.head(8).copy()
        other = share["volume_24h"].iloc[8:].sum()
        if other > 0:
            top = pd.concat([top, pd.DataFrame([{"display_name": "Others", "volume_24h": other}])])
        fig = px.pie(top, names="display_name", values="volume_24h", hole=0.45,
                     title="Exchange Share of 24h Volume", template="plotly_white", height=450)
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Exchanges")
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("Exchange Share of 24h Volume (top 8)", "exchange", "volume_24h", kind="share")
    with oc2:
        group_chart("24h Volume by Exchange (top 8)", "exchange", "volume_24h", kind="area")
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("Open Interest by Exchange (top 8)", "exchange", "oi_usd", kind="area")
    with oc2:
        ts_chart("Exchanges & Markets (coverage)",
                 [("Exchanges", "overall", "AXL", "exchanges", BLUE),
                  ("Markets", "overall", "AXL", "markets", ORANGE),
                  ("Active markets (volume > 0)", "overall", "AXL", "active_markets", GREEN),
                  ("Major CEX listings (of 6)", "overall", "AXL", "major_cex", PURPLE)], unit="num")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Volume Concentration: Top Exchange & Top 3 (% of volume)",
                 [("Top exchange", "overall", "AXL", "top_exchange_share_pct", BLUE),
                  ("Top 3 exchanges", "overall", "AXL", "top3_exchange_share_pct", ORANGE)], unit="pct")
    with oc2:
        ts_chart("Exchange HHI (0–10,000; higher = more concentrated)",
                 [("HHI", "overall", "AXL", "exchange_hhi", PURPLE)], unit="num")

    st.subheader("Volume by Quote Currency")
    q = dfm.groupby("quote", as_index=False)["volume_24h"].sum()
    q = q[q["volume_24h"] > 0].sort_values("volume_24h", ascending=False)
    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.pie(q, names="quote", values="volume_24h", hole=0.45, title="24h Volume by Quote Asset",
                     template="plotly_white", height=450)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        q_bar = q.sort_values("volume_24h", ascending=True)   # largest bar at the top
        fig = px.bar(q_bar, x="volume_24h", y="quote", orientation="h",
                     title="24h Volume by Quote Asset (USD)",
                     labels={"volume_24h": "Volume (USD)", "quote": "Quote asset"},
                     template="plotly_white", height=450, color_discrete_sequence=["#00B8F4"])
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Volume by Quote Asset")
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("24h Volume by Quote Asset (top 6)", "quote", "volume_24h", kind="area", top_n=6)
    with oc2:
        group_chart("Share of 24h Volume by Quote Asset (top 6)", "quote", "volume_24h", kind="share", top_n=6)

    st.subheader("24h Changes (markets with volume ≥ $10K)")
    chg = dfm[dfm["volume_24h"] >= 10_000].copy()
    chg["volume_change_pct"] = chg["volume_change_24h"] * 100
    chg["price_change_pct"] = chg["price_change_24h"] * 100
    chg["oi_change_pct"] = chg["oi_change_24h"] * 100
    chg = chg.sort_values("volume_24h", ascending=False)

    col_a, col_b = st.columns(2)
    with col_a:
        d = chg.dropna(subset=["volume_change_pct"])
        fig = go.Figure(go.Bar(
            x=d["market_label"], y=d["volume_change_pct"],
            marker_color=["green" if v >= 0 else "red" for v in d["volume_change_pct"]]))
        fig.update_layout(title="Volume Change vs Previous 24h (%)", template="plotly_white",
                          height=520, xaxis_title="Market", yaxis_title="Change (%)")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = chg.dropna(subset=["price_change_pct"])
        fig = go.Figure(go.Bar(
            x=d["market_label"], y=d["price_change_pct"],
            marker_color=["green" if v >= 0 else "red" for v in d["price_change_pct"]]))
        fig.update_layout(title="Price Change 24h by Market (%)", template="plotly_white",
                          height=520, xaxis_title="Market", yaxis_title="Change (%)")
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Daily Changes")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Total Volume Change vs Previous 24h (%)",
                 [("Volume change", "overall", "AXL", "volume_change_pct", None)],
                 kind="signed_bar", unit="pct", zero_line=True)
    with oc2:
        ts_chart("Price Change 24h, volume-weighted (%)",
                 [("Price change", "overall", "AXL", "price_change_pct", None)],
                 kind="signed_bar", unit="pct", zero_line=True)

# --------------------------------------------------
# TAB 2 — Prices & Spreads
# --------------------------------------------------
with tab_price:
    st.subheader("Cross-Market Price Comparison (USD-pegged quotes only)")
    st.caption("Markets quoted in KRW, TRY, EUR, IDR or BTC are excluded because their prices are not in USD terms.")

    dfp = dfm[dfm["quote"].isin(STABLE_QUOTES) & dfm["price"].notna() & (dfm["volume_24h"].fillna(0) > 0)].copy()
    ref_price = dfp["price"].median()
    vwap = np.average(dfp["price"], weights=dfp["volume_24h"]) if len(dfp) else np.nan
    dfp["deviation_pct"] = (dfp["price"] / ref_price - 1) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📍 Median Price", f"${ref_price:.5f}")
    c2.metric("⚖️ Volume-Weighted Price", f"${vwap:.5f}")
    c3.metric("🔻 Lowest", f"${dfp['price'].min():.5f}")
    c4.metric("🔺 Highest", f"${dfp['price'].max():.5f}")
    st.write(" ")
    st.metric("↔️ Max Cross-Market Spread", f"{(dfp['price'].max() - dfp['price'].min()) / ref_price * 100:.2f}%")

    d = dfp.sort_values("deviation_pct")
    fig = go.Figure(go.Bar(
        x=d["market_label"], y=d["deviation_pct"],
        marker_color=["green" if v >= 0 else "red" for v in d["deviation_pct"]]))
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(title="Price Deviation from Median (%)", template="plotly_white", height=550,
                      xaxis_title="Market", yaxis_title="Deviation (%)")
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Price & Cross-Market Dispersion")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("AXL Price Over Time (USD-quoted markets)",
                 [("Median", "overall", "AXL", "price_median", BLUE),
                  ("Volume-weighted", "overall", "AXL", "price_vwap", ORANGE),
                  ("Lowest", "overall", "AXL", "price_min", RED),
                  ("Highest", "overall", "AXL", "price_max", GREEN)], unit="num")
    with oc2:
        ts_chart("Price Dispersion & Max Cross-Market Spread (%)",
                 [("Volume-weighted dispersion", "overall", "AXL", "price_dispersion_pct", BLUE),
                  ("Max spread (highest vs lowest)", "overall", "AXL", "max_cross_market_spread_pct", ORANGE)],
                 unit="pct")

    st.subheader("Mark / Index Premium (perpetuals)")
    dfx = dfm[(dfm["segment"] == "Perp") & dfm["mark_price"].notna() & dfm["index_price"].notna()].copy()
    dfx["premium_pct"] = (dfx["mark_price"] / dfx["index_price"] - 1) * 100
    if len(dfx):
        dfx = dfx.sort_values("premium_pct")
        fig = go.Figure(go.Bar(
            x=dfx["market_label"], y=dfx["premium_pct"],
            marker_color=["green" if v >= 0 else "red" for v in dfx["premium_pct"]]))
        fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
        fig.update_layout(title="Mark Price vs Index Price (%)", template="plotly_white", height=500,
                          xaxis_title="Market", yaxis_title="Premium (%)")
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Mark / Index Premium")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Mark vs Index Premium, OI-weighted (%)",
                 [("Premium", "overall", "AXL", "mark_index_premium_pct", BLUE)], unit="pct", zero_line=True)
    with oc2:
        ts_chart("Average Price by Segment (API)",
                 [(l, "segment", l, "avg_price", SEG_COLORS[l]) for l in SEG_LABELS.values()], unit="num")

    st.subheader("Bid/Ask Spread")
    dfs = dfm[dfm["spread_pct"].notna() & dfm["quote"].isin(STABLE_QUOTES) & (dfm["volume_24h"].fillna(0) > 0)]
    dfs = dfs.sort_values("spread_pct")
    fig = px.bar(dfs, x="market_label", y="spread_pct", color="segment",
                 title="Best Bid/Ask Spread (%)", labels={"market_label": "Market", "spread_pct": "Spread (%)"},
                 template="plotly_white", height=500, color_discrete_map=SEG_COLORS)
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Bid/Ask Spread")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Bid/Ask Spread (USD-quoted markets, %)",
                 [("Volume-weighted", "overall", "AXL", "avg_spread_pct", BLUE),
                  ("Median", "overall", "AXL", "median_spread_pct", ORANGE)], unit="pct")
    with oc2:
        group_chart("Spread by Exchange (top 8 by volume, %)", "exchange", "avg_spread_pct", kind="line", unit="pct")

    st.subheader("Price Table")
    st.dataframe(
        dfp[["market_label", "venue", "price", "best_bid", "best_ask", "spread_pct",
             "deviation_pct", "price_change_24h", "volume_24h"]]
        .rename(columns={"market_label": "Market"})
        .sort_values("volume_24h", ascending=False).round(6),
        use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 3 — Perpetuals
# --------------------------------------------------
with tab_perp:
    dfq = dfm[dfm["segment"].isin(["Perp", "Perp (inverse)"])].copy()

    st.subheader("Funding Rates")
    dff = dfq.dropna(subset=["funding_rate_8h"]).sort_values("funding_rate_8h")
    fig = go.Figure(go.Bar(
        x=dff["market_label"], y=dff["funding_rate_8h"] * 100,
        marker_color=["green" if v >= 0 else "red" for v in dff["funding_rate_8h"]]))
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(title="Funding Rate (8h-normalised, %)", template="plotly_white", height=520,
                      xaxis_title="Market", yaxis_title="Funding (%)")
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        d = dff[dff["funding_rate_8h"].abs() < 0.005]  # hide extreme outliers in the annualised view
        fig = px.bar(d, x="market_label", y="funding_annualized_pct",
                     title="Annualised Funding (%) — outliers hidden",
                     labels={"market_label": "Market", "funding_annualized_pct": "Annualised (%)"},
                     template="plotly_white", height=450, color_discrete_sequence=["#00B8F4"])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = dfq.dropna(subset=["funding_period_h"])
        fig = px.histogram(d, x="funding_period_h", title="Funding Period Distribution (hours)",
                           template="plotly_white", height=450, color_discrete_sequence=["#FF8A00"])
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Funding")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Funding Rate (8h-normalised, %)",
                 [("OI-weighted", "overall", "AXL", "funding_8h_pct", BLUE),
                  ("Lowest market (OI ≥ $10K)", "overall", "AXL", "funding_min_pct", RED),
                  ("Highest market (OI ≥ $10K)", "overall", "AXL", "funding_max_pct", GREEN)],
                 unit="pct", zero_line=True)
    with oc2:
        ts_chart("Annualised Funding, OI-weighted (%)",
                 [("Annualised", "overall", "AXL", "funding_annualized_pct", PURPLE)], unit="pct", zero_line=True)
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("Funding Rate by Exchange (top 8 by volume, 8h %)", "exchange", "funding_8h_pct",
                    kind="line", unit="pct", zero_line=True)
    with oc2:
        ts_chart("Share of Open Interest with Positive Funding (%)",
                 [("Positive-funding OI share", "overall", "AXL", "funding_positive_oi_share_pct", ORANGE)],
                 unit="pct")

    st.subheader("Open Interest")
    col_a, col_b = st.columns(2)
    with col_a:
        d = dfq[dfq["oi_usd"] > 0].sort_values("oi_usd", ascending=False)
        fig = px.bar(d, x="market_label", y="oi_usd", color="venue", title="Open Interest by Market (USD)",
                     labels={"market_label": "Market", "oi_usd": "OI (USD)"}, template="plotly_white",
                     height=500, color_discrete_map=VENUE_COLORS)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = dfq.dropna(subset=["oi_change_24h"]).copy()
        d = d[d["oi_prev_usd"] >= 10_000]
        d["oi_change_pct"] = d["oi_change_24h"] * 100
        fig = go.Figure(go.Bar(
            x=d["market_label"], y=d["oi_change_pct"],
            marker_color=["green" if v >= 0 else "red" for v in d["oi_change_pct"]]))
        fig.update_layout(title="OI Change 24h (%) — markets with prev OI ≥ $10K", template="plotly_white",
                          height=500, xaxis_title="Market", yaxis_title="Change (%)")
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Open Interest")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Total Open Interest",
                 [("Open interest", "overall", "AXL", "oi_usd", BLUE),
                  ("Previous-period OI", "overall", "AXL", "oi_prev_usd", GREY)], kind="line")
    with oc2:
        ts_chart("Open Interest Change vs Previous (%)",
                 [("OI change", "overall", "AXL", "oi_change_pct", None)],
                 kind="signed_bar", unit="pct", zero_line=True)
    oc1, oc2 = st.columns(2)
    with oc1:
        group_chart("Open Interest by Venue", "venue", "oi_usd", kind="area", color_map=VENUE_COLORS)
    with oc2:
        ts_chart("Open Interest / Perp Volume",
                 [("OI ÷ perp volume", "overall", "AXL", "oi_to_perp_volume", PURPLE)], unit="num")

    st.subheader("Volume vs Open Interest")
    d = dfq[(dfq["oi_usd"] > 0) & (dfq["volume_24h"] > 0)]
    fig = px.scatter(d, x="volume_24h", y="oi_usd", size="oi_usd", color="venue", hover_name="market_label",
                     log_x=True, log_y=True, title="24h Volume vs OI (log scale)",
                     labels={"volume_24h": "Volume 24h (USD)", "oi_usd": "OI (USD)"},
                     template="plotly_white", height=550, color_discrete_map=VENUE_COLORS)
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Perp Volume & Leverage")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Daily Perp Volume (24h)",
                 [("Perp volume", "overall", "AXL", "perp_volume", BLUE)], kind="bar")
    with oc2:
        ts_chart("Max Leverage Offered (x)",
                 [("Highest", "overall", "AXL", "max_leverage", ORANGE),
                  ("Perp (API) max", "segment", "Perp", "leverage_max", BLUE),
                  ("Perp (API) min", "segment", "Perp", "leverage_min", GREY)], unit="num")

    st.subheader("Leverage & Contract Specs")
    st.dataframe(
        dfq[["market_label", "venue", "contract_type", "contract_size", "max_leverage", "funding_period_h",
             "funding_rate_8h", "funding_annualized_pct", "oi_usd", "oi_to_volume", "min_order_cost"]]
        .rename(columns={"market_label": "Market"}).sort_values("oi_usd", ascending=False).round(6),
        use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 4 — Liquidity Depth
# --------------------------------------------------
with tab_liq:
    st.subheader("Aggregate Order-Book Depth (all USD-quoted markets)")
    st.caption("Depth values are cumulative USD liquidity within a given % distance from the mid price.")

    dfd = dfm[dfm["quote"].isin(STABLE_QUOTES)].copy()
    dfd["depth_bid_usd"] = dfd["depth_bid_usd"].apply(clean_depth)   # same cleaning as the recorded history
    dfd["depth_ask_usd"] = dfd["depth_ask_usd"].apply(clean_depth)
    agg_bid = [np.nansum([depth_at(x, i) for x in dfd["depth_bid_usd"]]) for i in range(len(BANDS))]
    agg_ask = [np.nansum([depth_at(x, i) for x in dfd["depth_ask_usd"]]) for i in range(len(BANDS))]
    band_lbl = [f"±{b * 100:.2f}%" for b in BANDS]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=band_lbl, y=agg_bid, mode="lines+markers", name="Bids", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=band_lbl, y=agg_ask, mode="lines+markers", name="Asks", line=dict(color="red")))
    fig.update_layout(title="Cumulative Depth by Distance from Mid Price", template="plotly_white", height=500,
                      xaxis_title="Distance from mid", yaxis_title="Depth (USD)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Aggregate Depth")
    _i2 = int(np.argmin([abs(b - 0.02) for b in BANDS])) if BANDS else None
    _lbl2 = band_lbl[_i2] if _i2 is not None else ""
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Total Depth within ±1%, ±2%, ±5% (bid + ask)",
                 [("±1%", "overall", "AXL", "depth_1pct", GREEN),
                  ("±2%", "overall", "AXL", "depth_2pct", BLUE),
                  ("±5%", "overall", "AXL", "depth_5pct", ORANGE)], kind="line")
    with oc2:
        ts_chart(f"Bid vs Ask Depth within {_lbl2}",
                 [("Bids", "depth", _lbl2, "bid", GREEN), ("Asks", "depth", _lbl2, "ask", RED)], kind="line")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Depth Imbalance at ±2% ((bid − ask) / total, %)",
                 [("Imbalance", "overall", "AXL", "depth_imbalance_2pct_pct", PURPLE)],
                 kind="signed_bar", unit="pct", zero_line=True)
    with oc2:
        ts_chart("Depth (±2%) ÷ 24h Volume",
                 [("Depth ÷ volume", "overall", "AXL", "depth_to_volume", BLUE)], unit="num")
    if n_hist_days >= 2 and names_for("depth", "total"):
        _wide = pd.DataFrame({n: ser("depth", n, "total") for n in names_for("depth", "total")}).sort_index()
        _wide = _wide[sorted(_wide.columns, key=lambda t: float(t.replace("±", "").replace("%", "")))]
        _fig = go.Figure(go.Heatmap(z=_wide.T.values, x=_wide.index, y=list(_wide.columns),
                                    colorscale="Blues", colorbar_title="USD"))
        _fig.update_layout(title="Total Depth by Distance from Mid Price, Over Time", yaxis_title="Distance from mid")
        _show(_fig, "num", 420)

    st.subheader("Depth by Exchange at a Chosen Band")
    band_idx = st.select_slider(
        "Select depth band", options=list(range(len(BANDS))), value=min(4, len(BANDS) - 1),
        format_func=lambda i: f"±{BANDS[i] * 100:.2f}%")
    dfd["bid_depth"] = [depth_at(x, band_idx) for x in dfd["depth_bid_usd"]]
    dfd["ask_depth"] = [depth_at(x, band_idx) for x in dfd["depth_ask_usd"]]
    ex_depth = dfd.groupby(["display_name", "segment"], as_index=False)[["bid_depth", "ask_depth"]].sum()
    ex_depth = ex_depth[(ex_depth["bid_depth"] > 0) | (ex_depth["ask_depth"] > 0)]
    ex_depth["total"] = ex_depth["bid_depth"] + ex_depth["ask_depth"]
    ex_order = ex_depth.groupby("display_name")["total"].sum().sort_values(ascending=False).index.tolist()
    ex_long = ex_depth.melt(id_vars=["display_name", "segment"], value_vars=["bid_depth", "ask_depth"],
                            var_name="Side", value_name="Depth")
    ex_long["Side"] = ex_long["Side"].map({"bid_depth": "Bid", "ask_depth": "Ask"})
    fig = px.bar(ex_long, x="display_name", y="Depth", color="Side", barmode="group", facet_row="segment",
                 category_orders={"display_name": ex_order},
                 title=f"Depth within ±{BANDS[band_idx] * 100:.2f}% by Exchange",
                 labels={"display_name": "Exchange", "Depth": "Depth (USD)"},
                 template="plotly_white", height=700,
                 color_discrete_map={"Bid": "green", "Ask": "red"})
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Depth at the Chosen Band & by Exchange")
    _bl = band_lbl[band_idx]
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart(f"Bid vs Ask Depth within {_bl} (band selected above)",
                 [("Bids", "depth", _bl, "bid", GREEN), ("Asks", "depth", _bl, "ask", RED)], kind="line")
    with oc2:
        group_chart("Depth within ±2% by Exchange (top 8)", "exchange", "depth_2pct", kind="area")

    st.subheader("Single Market Order Book")
    depth_markets = dfm[dfm["depth_bid_usd"].notna() & dfm["depth_ask_usd"].notna()]["market_label"].tolist()
    sel = st.selectbox("Select market", depth_markets, index=0)
    row = dfm[dfm["market_label"] == sel].iloc[0]
    bids = [depth_at(row["depth_bid_usd"], i) for i in range(len(BANDS))]
    asks = [depth_at(row["depth_ask_usd"], i) for i in range(len(BANDS))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=band_lbl, y=bids, mode="lines+markers", name="Bids", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=band_lbl, y=asks, mode="lines+markers", name="Asks", line=dict(color="red")))
    fig.update_layout(title=f"Cumulative Depth — {sel}", template="plotly_white", height=450,
                      xaxis_title="Distance from mid", yaxis_title="Depth (USD)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Active Liquidity (normalised-volume model)")
    dfa = dfm.dropna(subset=["nvol_active_liquidity"]).sort_values("nvol_active_liquidity", ascending=False)
    dfa = dfa[dfa["nvol_active_liquidity"] > 0].head(25)
    fig = px.bar(dfa, x="market_label", y="nvol_active_liquidity", color="segment",
                 title="Top Markets by Active Liquidity (USD)",
                 labels={"market_label": "Market", "nvol_active_liquidity": "Active liquidity (USD)"},
                 template="plotly_white", height=500, color_discrete_map=SEG_COLORS)
    st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Active Liquidity")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Total Active Liquidity (normalised-volume model)",
                 [("Active liquidity", "overall", "AXL", "active_liquidity_usd", BLUE)], kind="area")
    with oc2:
        ts_chart("Normalised Volume Ratio (% of reported)",
                 [("Normalised ÷ reported", "overall", "AXL", "nvol_normalized_ratio_pct", ORANGE)], unit="pct")

# --------------------------------------------------
# TAB 5 — Fees & Data Quality
# --------------------------------------------------
with tab_quality:
    st.subheader("Trading Fees")
    dff2 = dfm.copy()
    dff2["maker_fee_pct"] = dff2["maker_fee"] * 100
    dff2["taker_fee_pct"] = dff2["taker_fee"] * 100
    fee = dff2.groupby(["display_name", "segment"], as_index=False)[["maker_fee_pct", "taker_fee_pct"]].mean()

    col_a, col_b = st.columns(2)
    with col_a:
        d = fee.dropna(subset=["taker_fee_pct"]).sort_values("taker_fee_pct")
        fig = px.bar(d, x="display_name", y="taker_fee_pct", color="segment", barmode="group",
                     title="Taker Fee (%)", labels={"display_name": "Exchange", "taker_fee_pct": "Fee (%)"},
                     template="plotly_white", height=450, color_discrete_map=SEG_COLORS)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = fee.dropna(subset=["maker_fee_pct"]).sort_values("maker_fee_pct")
        fig = px.bar(d, x="display_name", y="maker_fee_pct", color="segment", barmode="group",
                     title="Maker Fee (%)", labels={"display_name": "Exchange", "maker_fee_pct": "Fee (%)"},
                     template="plotly_white", height=450, color_discrete_map=SEG_COLORS)
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Trading Fees")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Average Fees, volume-weighted (%)",
                 [("Taker", "overall", "AXL", "avg_taker_fee_pct", BLUE),
                  ("Maker", "overall", "AXL", "avg_maker_fee_pct", ORANGE)], unit="pct")
    with oc2:
        group_chart("Taker Fee by Exchange (top 8 by volume, %)", "exchange", "taker_fee_pct", kind="line",
                    unit="pct")

    st.subheader("Reported vs Normalised Volume")
    st.caption("Normalised volume adjusts reported volume by what the order-book liquidity can plausibly support. "
               "A large gap can indicate inflated or low-quality volume.")
    dfn = dfm.dropna(subset=["nvol_reported", "nvol_normalized"]).copy()
    dfn = dfn[dfn["nvol_reported"] > 0].sort_values("nvol_reported", ascending=False)
    dfn["normalized_ratio"] = dfn["nvol_normalized"] / dfn["nvol_reported"]

    top_n = dfn.head(20)
    d = top_n.melt(id_vars="market_label", value_vars=["nvol_reported", "nvol_normalized"],
                   var_name="Metric", value_name="USD")
    d["Metric"] = d["Metric"].map({"nvol_reported": "Reported", "nvol_normalized": "Normalised"})
    fig = px.bar(d, x="market_label", y="USD", color="Metric", barmode="group",
                 title="Top 20 Markets: Reported vs Normalised Volume",
                 labels={"market_label": "Market"}, template="plotly_white", height=550,
                 color_discrete_map={"Reported": "#B0B0B0", "Normalised": "#00B8F4"})
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Total Reported Volume", fmt_usd(dfn["nvol_reported"].sum()))
        st.metric("Total Normalised Volume", fmt_usd(dfn["nvol_normalized"].sum()))
    with col_b:
        status = dfm["nvol_status"].fillna("n/a").value_counts().reset_index()
        status.columns = ["status", "count"]
        fig = px.pie(status, names="status", values="count", hole=0.45,
                     title="Normalised-Volume Coverage Status", template="plotly_white", height=380)
        st.plotly_chart(fig, use_container_width=True)

    ot_header("📈 Over time — Reported vs Normalised Volume")
    oc1, oc2 = st.columns(2)
    with oc1:
        ts_chart("Reported vs Normalised Volume (USD)",
                 [("Reported", "overall", "AXL", "nvol_reported", GREY),
                  ("Normalised", "overall", "AXL", "nvol_normalized", BLUE)], kind="line")
    with oc2:
        ts_chart("API Totals vs Sum of Markets (volume, USD)",
                 [("Sum of markets", "overall", "AXL", "volume_24h", BLUE),
                  ("API total_volume_24h", "overall", "AXL", "api_total_volume", ORANGE)], kind="line")

    st.subheader("Data Freshness")
    now_utc = pd.Timestamp.now(tz="UTC")
    fr = dfm[["market_label", "fresh_volume", "fresh_depth", "fresh_funding", "fresh_oi"]].copy()
    for c in ["fresh_volume", "fresh_depth", "fresh_funding", "fresh_oi"]:
        fr[c] = pd.to_datetime(fr[c], utc=True, errors="coerce")
        fr[c.replace("fresh_", "age_h_")] = ((now_utc - fr[c]).dt.total_seconds() / 3600).round(1)
    st.dataframe(fr.rename(columns={"market_label": "Market"}), use_container_width=True, hide_index=True)
    st.caption("Ages are measured against the current time; depth snapshots are typically a few hours older "
               "than volume / funding / OI.")

# --------------------------------------------------
# TAB 6 — Raw Data
# --------------------------------------------------
with tab_raw:
    st.subheader("Market Explorer")
    f1, f2, f3 = st.columns(3)
    venues = f1.multiselect("Venue", sorted(dfm["venue"].unique()), default=sorted(dfm["venue"].unique()))
    segs = f2.multiselect("Segment", sorted(dfm["segment"].unique()), default=sorted(dfm["segment"].unique()))
    exs = f3.multiselect("Exchange", sorted(dfm["display_name"].unique()), default=[])

    view = dfm[dfm["venue"].isin(venues) & dfm["segment"].isin(segs)]
    if exs:
        view = view[view["display_name"].isin(exs)]

    show_cols = [
        "display_name", "venue", "segment", "symbol", "pair_id", "quote", "price", "price_change_24h",
        "volume_24h", "volume_change_24h", "oi_usd", "oi_change_24h", "funding_rate_8h", "funding_period_h",
        "max_leverage", "maker_fee", "taker_fee", "best_bid", "best_ask", "spread_pct", "mark_price",
        "index_price", "min_order_cost", "nvol_reported", "nvol_normalized", "nvol_status", "pair_url"
    ]
    show_cols = [c for c in show_cols if c in view.columns]
    st.dataframe(view[show_cols].sort_values("volume_24h", ascending=False),
                 use_container_width=True, hide_index=True)

    csv = view.drop(columns=["depth_ask_usd", "depth_bid_usd"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, file_name="axl_markets.csv", mime="text/csv")

    with st.expander("Show raw API JSON"):
        st.json(raw, expanded=False)

with tab_raw:
    st.subheader("📈 Single Market Over Time")
    detail = load_detail_history()
    if not hist_all.empty:
        _cut = hist_cut["date"].min() if n_hist_days else None
        if _cut is not None:
            detail = detail[detail["date"] >= _cut]
    if n_hist_days < 2 or detail.empty:
        st.caption("Per-market history appears after at least 2 recorded days.")
    else:
        _vol_last = (detail[detail["metric"] == "volume_24h"].sort_values("date")
                     .groupby("name")["value"].last().sort_values(ascending=False))
        m1, m2 = st.columns(2)
        market_pick = m1.selectbox("Market (sorted by latest volume)", list(_vol_last.index), key="ot_market")
        METRIC_OPTS = {"volume_24h": "24h volume (USD)", "oi_usd": "Open interest (USD)",
                       "funding_8h_pct": "Funding 8h (%)", "price": "Price", "spread_pct": "Bid/ask spread (%)"}
        metric_pick = m2.selectbox("Indicator", list(METRIC_OPTS), format_func=METRIC_OPTS.get, key="ot_metric")
        d = detail[(detail["name"] == market_pick) & (detail["metric"] == metric_pick)].sort_values("date")
        if d.empty:
            st.caption("This market has no recorded values for the selected indicator.")
        else:
            if metric_pick == "volume_24h":
                fig = go.Figure(go.Bar(x=d["date"], y=d["value"], marker_color=BLUE))
            elif metric_pick == "funding_8h_pct":
                fig = go.Figure(go.Bar(x=d["date"], y=d["value"],
                                       marker_color=[GREEN if v >= 0 else RED for v in d["value"]]))
            else:
                fig = go.Figure(go.Scatter(x=d["date"], y=d["value"], mode="lines+markers",
                                           line=dict(color=BLUE, width=2)))
            fig.update_layout(title=f"{market_pick} — {METRIC_OPTS[metric_pick]}", showlegend=False)
            _show(fig, "usd" if metric_pick in ("volume_24h", "oi_usd") else
                  ("pct" if metric_pick.endswith("pct") else "num"), 420,
                  zero_line=metric_pick == "funding_8h_pct")

    if not hist_all.empty:
        st.download_button("⬇️ Download aggregated history (CSV)", hist_all.to_csv(index=False).encode("utf-8"),
                           file_name="axl_market_history.csv", mime="text/csv")

st.caption("Source: DefiLlama Markets API — https://defillama.com/api/public/markets/axelar")
