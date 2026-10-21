import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from curl_cffi import requests as cffi_requests
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

# ------ SIDEBAR ------------------------------------------------

st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px; # -- MOVE LEFT
        text-align: left;  
    }
    .sidebar-footer img {
        width: 16px;
        height: 16px;
        vertical-align: middle;
        border-radius: 50%;
        margin-right: 5px;
    }
    .sidebar-footer a {
        color: gray;
        text-decoration: none;
    }
    </style>

    <div class="sidebar-footer">
        <div>
            <a href="https://x.com/axelar" target="_blank">
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo">
                Powered by Axelar
            </a>
        </div>
        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/2060406047391559681/sA9zPNKM_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
# ==================================================
# Fetch Data
# ==================================================
@st.cache_data(ttl=300)
def load_raw():
    response = requests.get(API_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.json()


try:
    raw = load_raw()
except Exception as e:
    st.error(f"❌ Error fetching market data: {e}")
    st.stop()

BANDS = raw.get("depth_bands", [])


# ==================================================
# Helpers
# ==================================================
def depth_at(lst, idx):
    """Safe getter for a depth list (values may be None)."""
    if isinstance(lst, list) and idx < len(lst) and lst[idx] is not None:
        return float(lst[idx])
    return np.nan


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

    st.subheader("Bid/Ask Spread")
    dfs = dfm[dfm["spread_pct"].notna() & dfm["quote"].isin(STABLE_QUOTES) & (dfm["volume_24h"].fillna(0) > 0)]
    dfs = dfs.sort_values("spread_pct")
    fig = px.bar(dfs, x="market_label", y="spread_pct", color="segment",
                 title="Best Bid/Ask Spread (%)", labels={"market_label": "Market", "spread_pct": "Spread (%)"},
                 template="plotly_white", height=500, color_discrete_map=SEG_COLORS)
    st.plotly_chart(fig, use_container_width=True)

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

    st.subheader("Volume vs Open Interest")
    d = dfq[(dfq["oi_usd"] > 0) & (dfq["volume_24h"] > 0)]
    fig = px.scatter(d, x="volume_24h", y="oi_usd", size="oi_usd", color="venue", hover_name="market_label",
                     log_x=True, log_y=True, title="24h Volume vs OI (log scale)",
                     labels={"volume_24h": "Volume 24h (USD)", "oi_usd": "OI (USD)"},
                     template="plotly_white", height=550, color_discrete_map=VENUE_COLORS)
    st.plotly_chart(fig, use_container_width=True)

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
    agg_bid = [np.nansum([depth_at(x, i) for x in dfd["depth_bid_usd"]]) for i in range(len(BANDS))]
    agg_ask = [np.nansum([depth_at(x, i) for x in dfd["depth_ask_usd"]]) for i in range(len(BANDS))]
    band_lbl = [f"±{b * 100:.2f}%" for b in BANDS]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=band_lbl, y=agg_bid, mode="lines+markers", name="Bids", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=band_lbl, y=agg_ask, mode="lines+markers", name="Asks", line=dict(color="red")))
    fig.update_layout(title="Cumulative Depth by Distance from Mid Price", template="plotly_white", height=500,
                      xaxis_title="Distance from mid", yaxis_title="Depth (USD)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

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

st.caption("Source: DefiLlama Markets API — https://defillama.com/api/public/markets/axelar")
