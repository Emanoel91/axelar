import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

try:  # optional: helps if the API rejects plain python-requests traffic (HTTP 403)
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title ------------------------------------------------------------------------------------------------------------
st.title("⚔️ AXL vs Competitors — Market Comparison")
st.info("⏳ Data for 10 tokens is fetched from the DefiLlama Markets API and may take a few moments to load.")

# ==================================================
# Configuration
# ==================================================
BASE_URL = "https://defillama.com/api/public/markets/"

# (ticker, display name, DefiLlama slug)
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
FOCUS = "AXL"
STABLE_QUOTES = {"usdt", "usdc", "usd", "usdh"}
MAJOR_CEX = ["Binance", "Coinbase", "OKX", "Bybit", "Upbit", "Kraken"]
DEFAULT_BANDS = [0.001, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025, 0.05, 0.1, 0.25]
BLUE = "#00B8F4"
GREY = "#B0B0B0"
ORANGE = "#FF8A00"
GROUP_COLORS = {"Axelar": BLUE, "Competitors": GREY}

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

# key -> (label, kind, higher_is_better)   kind: usd | pct | num | ratio
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
    "volume_quality_pct": ("Volume quality (normalised ÷ reported, %)", "pct", True),
    "avg_taker_fee_pct": ("Avg taker fee (vol-weighted, %)", "pct", False),
    "exchanges": ("Exchanges", "num", True),
    "markets": ("Markets", "num", True),
    "perp_exchanges": ("Exchanges with perps", "num", True),
    "spot_exchanges": ("Exchanges with spot", "num", True),
    "dex_markets": ("DEX markets", "num", True),
    "major_cex": (f"Major CEX listings (of {len(MAJOR_CEX)})", "num", True),
    "top_exchange_share_pct": ("Top exchange share of volume (%)", "pct", False),
}


# ==================================================
# Helpers
# ==================================================
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


def fmt_metric(x, kind):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    if kind == "usd":
        return fmt_usd(x)
    if kind == "pct":
        return f"{x:,.2f}%"
    if kind == "ratio":
        return f"{x:,.2f}"
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.4g}"


def wavg(values, weights):
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan


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
    valid = (mk["best_bid"] > 0) & (mk["best_ask"] > 0)
    spread_pct = ((mk["best_ask"] - mk["best_bid"]) / mid * 100).where(valid)

    # aggregated order-book depth (sum over all markets, USD-denominated)
    bid_tot = np.zeros(len(bands))
    ask_tot = np.zeros(len(bands))
    for b, a in zip(mk["depth_bid"], mk["depth_ask"]):
        for i in range(len(bands)):
            bid_tot[i] += depth_at(b, i)
            ask_tot[i] += depth_at(a, i)
    depth = bid_tot + ask_tot
    d1, d2, d5 = (depth[band_index(bands, t)] for t in (0.01, 0.02, 0.05))

    q = mk[(mk["nvol_reported"] > 0) & mk["nvol_normalized"].notna()]
    quality = q["nvol_normalized"].sum() / q["nvol_reported"].sum() * 100 if len(q) else np.nan

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
        "volume_quality_pct": quality, "avg_taker_fee_pct": wavg(mk["taker_fee"], mk["volume_24h"]) * 100,
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


@st.cache_data(ttl=300)
def load_all():
    """Fetch every token in parallel, then summarise. No Streamlit calls inside the worker threads."""
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(lambda t: fetch_json(t[2]), TOKENS))
    metrics, curves, ex_vols, errors = [], {}, {}, {}
    for (ticker, name, _slug), (payload, err) in zip(TOKENS, results):
        if payload is None:
            errors[ticker] = err
            continue
        try:
            m, c, e = summarize(ticker, name, payload)
            metrics.append(m)
            curves[ticker] = c
            ex_vols[ticker] = e
        except Exception as e:  # keep the dashboard alive if one payload is odd
            errors[ticker] = f"processing error: {e}"
    return {"metrics": metrics, "curves": curves, "ex_vols": ex_vols, "errors": errors}


# ==================================================
# Load
# ==================================================
with st.spinner("Fetching market data for all tokens..."):
    data = load_all()

if data["errors"]:
    st.warning("Some tokens could not be loaded and are excluded: " +
               "; ".join(f"**{t}** ({str(e)[:120]})" for t, e in data["errors"].items()))
if not data["metrics"]:
    st.error("❌ No data could be loaded.")
    st.stop()

mdf_all = pd.DataFrame(data["metrics"])
if FOCUS not in set(mdf_all["ticker"]):
    st.error("❌ Axelar (AXL) data could not be loaded, so the comparison cannot be built.")
    st.stop()

# ==================================================
# Controls
# ==================================================
available_peers = [t for t in mdf_all["ticker"] if t != FOCUS]
ctrl1, ctrl2 = st.columns([3, 1])
peers = ctrl1.multiselect("Competitors to compare with AXL", available_peers, default=available_peers)
log_scale = ctrl2.checkbox("Log scale for USD charts", value=True)

cdf = mdf_all[mdf_all["ticker"].isin([FOCUS] + peers)].copy().reset_index(drop=True)
cdf["group"] = np.where(cdf["ticker"] == FOCUS, "Axelar", "Competitors")
n_tok = len(cdf)

palette = [c for c in px.colors.qualitative.Bold if c.lower() != BLUE.lower()]
color_map = {FOCUS: BLUE}
for i, t in enumerate([x for x in cdf["ticker"] if x != FOCUS]):
    color_map[t] = palette[i % len(palette)]


def rank_of(col, ascending=False):
    s = cdf[["ticker", col]].dropna()
    if FOCUS not in set(s["ticker"]):
        return None, len(s)
    s = s.sort_values(col, ascending=ascending).reset_index(drop=True)
    return int(s.index[s["ticker"] == FOCUS][0]) + 1, len(s)


def rank_label(col, ascending=False):
    r, n = rank_of(col, ascending)
    return "n/a" if r is None else f"#{r} of {n}"


def cmp_bar(col, title, usd=False, asc=False, height=420):
    d = cdf.dropna(subset=[col]).sort_values(col, ascending=asc)
    fig = px.bar(d, x="ticker", y=col, color="group", color_discrete_map=GROUP_COLORS, hover_name="name",
                 title=title, labels={"ticker": "Token", col: METRICS[col][0]}, template="plotly_white",
                 height=height)
    if usd and log_scale:
        fig.update_yaxes(type="log")
    fig.update_layout(showlegend=False)
    return fig


def signed_bar(col, title, height=420):
    d = cdf.dropna(subset=[col]).sort_values(col, ascending=False)
    fig = go.Figure(go.Bar(
        x=d["ticker"], y=d[col],
        marker_color=["green" if v >= 0 else "red" for v in d[col]],
        marker_line_color=[BLUE if t == FOCUS else "rgba(0,0,0,0)" for t in d["ticker"]],
        marker_line_width=[4 if t == FOCUS else 0 for t in d["ticker"]],
        hovertext=d["name"]))
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(title=title, template="plotly_white", height=height, xaxis_title="Token",
                      yaxis_title=METRICS[col][0], showlegend=False)
    return fig


# ==================================================
# Header KPIs — where does Axelar stand?
# ==================================================
axl = cdf[cdf["ticker"] == FOCUS].iloc[0]
st.markdown(f"### 💎 Axelar (AXL) Position vs {n_tok - 1} Competitors")
k1, k2, k3, k4 = st.columns(4)
k1.metric("📊 24h Volume", fmt_usd(axl["volume_24h"]), rank_label("volume_24h"), delta_color="off")
k2.metric("🧾 Open Interest", fmt_usd(axl["oi_usd"]), rank_label("oi_usd"), delta_color="off")
k3.metric("🌊 Depth ±2%", fmt_usd(axl["depth_2pct"]), rank_label("depth_2pct"), delta_color="off")
k4.metric("🏦 Exchanges", f"{int(axl['exchanges'])}", rank_label("exchanges"), delta_color="off")
st.write(" ")
k5, k6, k7, k8 = st.columns(4)
k5.metric("↔️ Avg Spread", fmt_metric(axl["avg_spread_pct"], "pct"), rank_label("avg_spread_pct", True),
          delta_color="off")
k6.metric("🧪 Volume Quality", fmt_metric(axl["volume_quality_pct"], "pct"), rank_label("volume_quality_pct"),
          delta_color="off")
k7.metric("⭐ Major CEX Listings", f"{int(axl['major_cex'])} / {len(MAJOR_CEX)}", rank_label("major_cex"),
          delta_color="off")
k8.metric("🌐 DEX Share of Volume", fmt_metric(axl["dex_share_pct"], "pct"), rank_label("dex_share_pct"),
          delta_color="off")
st.caption("The small grey label under each value is AXL's rank among the selected tokens "
           "(for spread, #1 = tightest).")
st.write(" ")

# ==================================================
# Inner tabs
# ==================================================
tab_score, tab_vol, tab_deriv, tab_liq, tab_cov, tab_data = st.tabs([
    "🏁 Scorecard", "📊 Volume & Activity", "⚡ Derivatives", "🌊 Liquidity & Pricing",
    "🏦 Exchange Coverage", "🗂️ Data & Notes"
])

# --------------------------------------------------
# TAB 1 — Scorecard
# --------------------------------------------------
with tab_score:
    st.subheader("Axelar vs the Peer Group")
    rows = []
    for key in ["volume_24h", "perp_volume", "spot_volume", "oi_usd", "exchanges", "major_cex", "depth_2pct",
                "depth_to_volume", "avg_spread_pct", "price_dispersion_pct", "volume_quality_pct", "dex_share_pct"]:
        label, kind, hib = METRICS[key]
        asc = hib is False
        r, n = rank_of(key, asc)
        peers_only = cdf.loc[cdf["ticker"] != FOCUS, key].dropna()
        med = peers_only.median() if len(peers_only) else np.nan
        val = axl[key]
        mult = val / med if pd.notna(val) and pd.notna(med) and med != 0 else np.nan
        rows.append({"Metric": label, "AXL": fmt_metric(val, kind),
                     "Rank": "n/a" if r is None else f"#{r} of {n}",
                     "Peer median": fmt_metric(med, kind),
                     "AXL ÷ median": "-" if pd.isna(mult) else f"{mult:.2f}x"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Rank 1 = highest value, except spread and price dispersion where 1 = lowest. "
               "Tokens without a given market type (e.g. no perpetuals) are left out of that ranking.")

    st.subheader("Percentile Radar")
    radar_metrics = ["volume_24h", "oi_usd", "exchanges", "major_cex", "depth_2pct", "avg_spread_pct",
                     "volume_quality_pct"]
    pct_rank = pd.DataFrame({"ticker": cdf["ticker"]})
    for key in radar_metrics:
        s = cdf[key]
        asc = METRICS[key][2] is False
        pr = s.rank(pct=True, ascending=not asc) * 100        # higher = better after orientation
        pct_rank[key] = pr.fillna(0)
    default_radar = [FOCUS] + cdf.sort_values("volume_24h", ascending=False)["ticker"].tolist()
    default_radar = [t for t in dict.fromkeys(default_radar) if t != FOCUS][:3]
    chosen = st.multiselect("Tokens on the radar", cdf["ticker"].tolist(), default=[FOCUS] + default_radar)
    theta = [METRICS[k][0].split(" (")[0] for k in radar_metrics]
    fig = go.Figure()
    for t in chosen:
        vals = pct_rank.loc[pct_rank["ticker"] == t, radar_metrics].iloc[0].tolist()
        fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=theta + theta[:1], name=t, fill="toself",
                                      opacity=0.45 if t != FOCUS else 0.7,
                                      line=dict(color=color_map.get(t), width=4 if t == FOCUS else 2)))
    fig.update_layout(title="Percentile Rank Across Key Dimensions (100 = best in group)", template="plotly_white",
                      height=560, polar=dict(radialaxis=dict(range=[0, 100], showticklabels=True)))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Percentile of the selected group, so a small group gives coarse steps. "
               "Tokens without a metric score 0 on it.")

# --------------------------------------------------
# TAB 2 — Volume & Activity
# --------------------------------------------------
with tab_vol:
    st.subheader("Trading Volume (24h)")
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("volume_24h", "Total 24h Volume (USD)", usd=True), use_container_width=True)
    with col_b:
        st.plotly_chart(signed_bar("volume_change_pct", "Volume Change vs Previous 24h (%)"),
                        use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        d = cdf.melt(id_vars=["ticker"], value_vars=["perp_volume", "spot_volume"], var_name="Segment",
                     value_name="USD")
        d["Segment"] = d["Segment"].map({"perp_volume": "Perp", "spot_volume": "Spot"})
        order = cdf.sort_values("volume_24h", ascending=False)["ticker"].tolist()
        fig = px.bar(d, x="ticker", y="USD", color="Segment", barmode="stack",
                     category_orders={"ticker": order}, title="Perp vs Spot Volume (USD)",
                     labels={"ticker": "Token"}, template="plotly_white", height=420,
                     color_discrete_map={"Perp": BLUE, "Spot": ORANGE})
        if log_scale:
            st.caption("Stacked bars are shown on a linear axis (log scale would distort the stack).")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = cdf.copy()
        d["CEX"] = 100 - d["dex_share_pct"]
        d["DEX"] = d["dex_share_pct"]
        d = d.melt(id_vars=["ticker"], value_vars=["CEX", "DEX"], var_name="Venue", value_name="Share (%)")
        fig = px.bar(d, x="ticker", y="Share (%)", color="Venue", barmode="stack",
                     category_orders={"ticker": order}, title="CEX vs DEX Share of Volume (%)",
                     labels={"ticker": "Token"}, template="plotly_white", height=420,
                     color_discrete_map={"CEX": BLUE, "DEX": ORANGE})
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("perp_share_pct", "Perp Share of Total Volume (%)"), use_container_width=True)
    with col_b:
        st.plotly_chart(signed_bar("price_change_pct", "Price Change 24h (volume-weighted, %)"),
                        use_container_width=True)

# --------------------------------------------------
# TAB 3 — Derivatives
# --------------------------------------------------
with tab_deriv:
    st.subheader("Perpetual Futures")
    no_perp = cdf.loc[cdf["oi_usd"].isna(), "ticker"].tolist()
    if no_perp:
        st.caption("No perpetual markets listed (excluded from the charts below): " + ", ".join(no_perp))

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("oi_usd", "Open Interest (USD)", usd=True), use_container_width=True)
    with col_b:
        st.plotly_chart(signed_bar("oi_change_pct", "Open Interest Change vs Previous (%)"),
                        use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(signed_bar("funding_annualized_pct", "Funding Rate, OI-Weighted (annualised %)"),
                        use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("oi_to_perp_volume", "Open Interest ÷ Perp Volume"), use_container_width=True)
    st.caption("A higher OI/volume ratio means positions are held longer relative to daily turnover; "
               "a low ratio points to short-term, high-turnover trading. Funding is the 8h-normalised rate "
               "weighted by open interest, annualised ×3×365.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("max_leverage", "Maximum Leverage Offered (x)"), use_container_width=True)
    with col_b:
        d = cdf.dropna(subset=["oi_usd", "volume_24h"])
        d = d[(d["oi_usd"] > 0) & (d["volume_24h"] > 0)]
        if len(d):
            fig = px.scatter(d, x="volume_24h", y="oi_usd", size="exchanges", color="ticker", text="ticker",
                             hover_name="name", log_x=True, log_y=True, color_discrete_map=color_map,
                             title="Volume vs Open Interest (bubble = exchanges)",
                             labels={"volume_24h": "24h volume (USD)", "oi_usd": "OI (USD)"},
                             template="plotly_white", height=420)
            fig.update_traces(textposition="top center")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TAB 4 — Liquidity & Pricing
# --------------------------------------------------
with tab_liq:
    st.subheader("Order-Book Depth")
    st.caption("Depth = USD liquidity on both sides of the book within ±X% of the mid price, summed across all "
               "markets of the token (liquidity on different exchanges is added together).")
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("depth_1pct", "Depth within ±1% (USD)", usd=True), use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("depth_5pct", "Depth within ±5% (USD)", usd=True), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("depth_to_volume", "Depth ±2% ÷ 24h Volume"), use_container_width=True)
    with col_b:
        fig = go.Figure()
        for t in cdf["ticker"]:
            c = data["curves"].get(t)
            if not c:
                continue
            pts = [(b, dv) for b, dv in zip(c["bands"], c["depth"]) if b <= 0.05]
            fig.add_trace(go.Scatter(x=[f"±{b * 100:.2f}%" for b, _ in pts], y=[dv for _, dv in pts],
                                     mode="lines+markers", name=t,
                                     line=dict(color=color_map.get(t), width=5 if t == FOCUS else 2)))
        fig.update_layout(title="Cumulative Depth by Distance from Mid (up to ±5%)", template="plotly_white",
                          height=420, xaxis_title="Distance from mid", yaxis_title="Depth (USD)",
                          hovermode="x unified")
        if log_scale:
            fig.update_yaxes(type="log")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Spreads & Price Consistency")
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("avg_spread_pct", "Avg Bid/Ask Spread (vol-weighted, %) — lower is better",
                                asc=True), use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("price_dispersion_pct",
                                "Cross-Exchange Price Dispersion (vol-weighted, %) — lower is better", asc=True),
                        use_container_width=True)

    st.subheader("Volume Quality & Costs")
    col_a, col_b = st.columns(2)
    with col_a:
        fig = cmp_bar("volume_quality_pct", "Volume Quality: Normalised ÷ Reported Volume (%)")
        fig.add_hline(y=100, line_dash="dash", line_color="black", line_width=1)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("avg_taker_fee_pct", "Avg Taker Fee (vol-weighted, %)", asc=True),
                        use_container_width=True)
    st.caption("Normalised volume adjusts reported volume to what order-book liquidity can plausibly support. "
               "Values far below 100% suggest a lot of reported volume is low-quality or thinly supported.")

# --------------------------------------------------
# TAB 5 — Exchange Coverage
# --------------------------------------------------
with tab_cov:
    st.subheader("Listing Footprint")
    col_a, col_b = st.columns(2)
    with col_a:
        d = cdf.melt(id_vars=["ticker"], value_vars=["perp_exchanges", "spot_exchanges"], var_name="Type",
                     value_name="Exchanges")
        d["Type"] = d["Type"].map({"perp_exchanges": "Perp", "spot_exchanges": "Spot"})
        order = cdf.sort_values("exchanges", ascending=False)["ticker"].tolist()
        fig = px.bar(d, x="ticker", y="Exchanges", color="Type", barmode="group",
                     category_orders={"ticker": order}, title="Exchanges Listing Perp / Spot Markets",
                     labels={"ticker": "Token"}, template="plotly_white", height=420,
                     color_discrete_map={"Perp": BLUE, "Spot": ORANGE})
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("major_cex", f"Major CEX Listings (of {len(MAJOR_CEX)}: "
                                             f"{', '.join(MAJOR_CEX)})"), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(cmp_bar("markets", "Total Markets (pairs)"), use_container_width=True)
    with col_b:
        st.plotly_chart(cmp_bar("top_exchange_share_pct",
                                "Volume Share of the Largest Exchange (%) — lower = less concentrated", asc=True),
                        use_container_width=True)

    st.subheader("Where Does Each Token Trade? (% of the token's 24h volume)")
    ex_df = pd.DataFrame({t: pd.Series(data["ex_vols"].get(t, {})) for t in cdf["ticker"]}).fillna(0.0)
    if ex_df.empty or ex_df.values.sum() == 0:
        st.info("No exchange volume data available.")
    else:
        share = ex_df.div(ex_df.sum(axis=0).replace(0, np.nan), axis=1).fillna(0) * 100
        top_ex = share.sum(axis=1).sort_values(ascending=False).head(15).index
        z = share.loc[top_ex]
        fig = px.imshow(z.values, x=list(z.columns), y=list(z.index), text_auto=".0f", aspect="auto",
                        color_continuous_scale="Blues", labels=dict(color="% of volume"),
                        title="Share of Each Token's Volume by Exchange (top 15 exchanges)", height=620)
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TAB 6 — Data & Notes
# --------------------------------------------------
with tab_data:
    st.subheader("Full Comparison Table")
    show = cdf.drop(columns=["group"]).rename(columns={k: v[0] for k, v in METRICS.items()})
    show = show.rename(columns={"ticker": "Ticker", "name": "Token", "tags": "Tags"})
    st.dataframe(show.round(4), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", show.to_csv(index=False).encode("utf-8"),
                       file_name="axl_vs_competitors.csv", mime="text/csv")

    with st.expander("ℹ️ Methodology & limitations"):
        st.markdown(
            """
- **Source:** DefiLlama `markets` endpoints (one per token). All figures are a **snapshot of the last 24 hours**
  versus the previous 24 hours; the API has no longer history.
- **All sums are computed from the individual markets** returned by each API (CEX + DEX, perp + spot), so every
  token is treated identically.
- **Price** uses the median of USD-pegged quotes (USDT/USDC/USD/USDH) with non-zero volume. Spread, depth and
  price-change metrics use all markets because they are ratios or already USD-denominated.
- **Depth** adds up liquidity across exchanges; it measures total available liquidity, not the depth of a single book.
- **Funding** is the open-interest-weighted 8h-normalised funding rate. **OI/volume** uses perp volume only.
- **Tokens with no perpetual markets** (for example Across or Stargate) have no OI, funding or leverage values.
- **Not available in this API:** market cap, FDV, TVL and on-chain bridge activity. Volume-to-market-cap style
  ratios therefore cannot be built from these endpoints alone.
- **Percentile radar** is relative to the selected group only.
            """
        )

st.caption("Source: DefiLlama Markets API — https://defillama.com/api/public/markets/{token}")
