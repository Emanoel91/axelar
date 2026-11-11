import io
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
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
# --- Title ------------------------------------------------------------------------------------------------------------
st.title("📈 AXL vs Competitors — Daily History")
st.info("ℹ️ One snapshot is recorded per day by a GitHub Action (scripts/record_market_snapshot.py). "
        "Charts fill in over time: every new day adds one point per token.")

# ==================================================
# Configuration
# ==================================================
HISTORY_URL = "https://raw.githubusercontent.com/Emanoel91/axelar/main/data/market_history.csv"
LOCAL_PATH = "data/market_history.csv"      # used when the GitHub URL cannot be read (e.g. private repo)
FOCUS = "AXL"
BLUE = "#00B8F4"

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

MAJOR_CEX = ["Binance", "Coinbase", "OKX", "Bybit", "Upbit", "Kraken"]   # same list as the recorder

# key -> (label, kind, higher_is_better)   -- identical to the recorder script
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

GROUPS = {
    "volume": ["volume_24h", "volume_change_pct", "perp_volume", "spot_volume", "perp_share_pct", "dex_share_pct",
               "price_change_pct"],
    "deriv": ["oi_usd", "oi_change_pct", "oi_to_perp_volume", "funding_8h_pct", "funding_annualized_pct",
              "max_leverage"],
    "liq": ["price", "price_dispersion_pct", "avg_spread_pct", "depth_1pct", "depth_2pct", "depth_5pct",
            "depth_to_volume", "avg_taker_fee_pct"],
    "cov": ["exchanges", "markets", "perp_exchanges", "spot_exchanges", "dex_markets", "major_cex",
            "top_exchange_share_pct"],
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


@st.cache_data(ttl=600)
def load_history():
    """Read the CSV written by the daily recorder. Returns (dataframe, source, error)."""
    text, source, err = None, None, None
    try:
        r = requests.get(HISTORY_URL, timeout=30)
        r.raise_for_status()
        text, source = r.text, "GitHub (raw file)"
    except Exception as e:
        err = str(e)
    if text is None and os.path.exists(LOCAL_PATH):
        with open(LOCAL_PATH, encoding="utf-8") as f:
            text, source = f.read(), "local file"
    if text is None:
        return None, None, err

    df = pd.read_csv(io.StringIO(text))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["captured_at_utc"] = pd.to_datetime(df["captured_at_utc"], utc=True, errors="coerce")
    try:
        df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True, errors="coerce", format="ISO8601")
    except (TypeError, ValueError):
        df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True, errors="coerce")
    for c in list(METRICS.keys()) + ["api_total_volume", "api_total_oi"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "ticker"])
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last").sort_values(["date", "ticker"])
    return df.reset_index(drop=True), source, None


# ==================================================
# Load
# ==================================================
hist, source, load_err = load_history()
if hist is None or hist.empty:
    st.warning("No history has been recorded yet.")
    st.markdown(
        "1. Add `scripts/record_market_snapshot.py` and `.github/workflows/record_market_history.yml` to the repo.\n"
        "2. In GitHub open **Actions → Record market history → Run workflow** to record the first day.\n"
        "3. Come back here: the file `data/market_history.csv` will be in the repo and the charts will appear."
    )
    if load_err:
        st.caption(f"Could not read {HISTORY_URL}: {load_err}")
    st.stop()

ticker_order = list(dict.fromkeys(hist["ticker"]))
names = hist.drop_duplicates("ticker", keep="last").set_index("ticker")["name"].to_dict()
if FOCUS not in ticker_order:
    st.error("AXL has no rows in the history file yet.")
    st.stop()

min_d, max_d = hist["date"].min().date(), hist["date"].max().date()
n_days = hist["date"].nunique()

# ==================================================
# Controls
# ==================================================
available_peers = [t for t in ticker_order if t != FOCUS]
c1, c2 = st.columns([3, 2])
peers = c1.multiselect("Competitors to compare with AXL", available_peers, default=available_peers)
if min_d < max_d:
    rng = c2.date_input("Date range (UTC days)", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    start_d, end_d = (rng[0], rng[1]) if isinstance(rng, (list, tuple)) and len(rng) == 2 else (min_d, max_d)
else:
    start_d = end_d = min_d
    c2.caption(f"Only one day recorded so far ({min_d}).")

o1, o2, o3 = st.columns(3)
mode = o1.radio("Values", ["Actual values", "Indexed (first day = 100)"], horizontal=True)
smooth = o2.checkbox("7-day moving average (of recorded days)", value=False)
log_scale = o3.checkbox("Log scale for USD charts", value=False)
indexed_mode = mode.startswith("Indexed")

cdf = hist[hist["ticker"].isin([FOCUS] + peers)
           & (hist["date"] >= pd.Timestamp(start_d)) & (hist["date"] <= pd.Timestamp(end_d))].copy()
if cdf.empty:
    st.warning("No data in the selected range.")
    st.stop()
if cdf["date"].nunique() < 2:
    st.info("Only one day is available in the selected range, so each token shows a single point. "
            "Lines appear from the second recorded day.")

palette = [c for c in px.colors.qualitative.Bold if c.lower() != BLUE.lower()]
color_map = {FOCUS: BLUE}
for i, t in enumerate([x for x in ticker_order if x != FOCUS]):
    color_map[t] = palette[i % len(palette)]

# ==================================================
# Header KPIs — AXL latest day vs previous recorded day
# ==================================================
latest_date = hist["date"].max()
last_capture = hist["captured_at_utc"].max()
st.markdown("### 💎 Recording Status & AXL Latest Values")
s1, s2, s3, s4 = st.columns(4)
s1.metric("📅 Days Recorded", f"{n_days}")
s2.metric("🗓️ First → Last Day", f"{min_d} → {max_d}")
s3.metric("🪙 Tokens", f"{len(ticker_order)}")
s4.metric("🕒 Last Snapshot (UTC)", "-" if pd.isna(last_capture) else last_capture.strftime("%Y-%m-%d %H:%M"))
st.caption(f"Data source: {source}. Each day's values describe the 24 hours before that snapshot.")

axl_hist = hist[hist["ticker"] == FOCUS].sort_values("date")
axl_last = axl_hist.iloc[-1]
axl_prev = axl_hist.iloc[-2] if len(axl_hist) >= 2 else None
day_slice = hist[hist["date"] == axl_last["date"]]


def kpi(col, label, key, ascending=False):
    kind = METRICS[key][1]
    val = axl_last[key]
    s = day_slice[["ticker", key]].dropna().sort_values(key, ascending=ascending).reset_index(drop=True)
    rank = "n/a"
    if FOCUS in set(s["ticker"]):
        rank = f"#{int(s.index[s['ticker'] == FOCUS][0]) + 1} of {len(s)}"
    delta = None
    if axl_prev is not None and pd.notna(val) and pd.notna(axl_prev[key]) and axl_prev[key] != 0:
        delta = f"{(val / axl_prev[key] - 1) * 100:+.1f}% vs previous day"
    col.metric(f"{label} · {rank}", fmt_metric(val, kind), delta)


k1, k2, k3, k4 = st.columns(4)
kpi(k1, "📊 24h Volume", "volume_24h")
kpi(k2, "🧾 Open Interest", "oi_usd")
kpi(k3, "🌊 Depth ±2%", "depth_2pct")
kpi(k4, "🏦 Exchanges", "exchanges")
st.write(" ")

# ==================================================
# Chart helpers
# ==================================================
def line_fig(col):
    label, kind, _ = METRICS[col]
    d = cdf[["date", "ticker", "name", col]].sort_values(["ticker", "date"]).copy()
    if smooth:
        d[col] = d.groupby("ticker")[col].transform(lambda s: s.rolling(7, min_periods=1).mean())
    indexed = False
    if indexed_mode and kind in ("usd", "num", "ratio"):
        base = d.groupby("ticker")[col].transform(lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan)
        d[col] = np.where(base > 0, d[col] / base * 100, np.nan)
        indexed = True
    d = d.dropna(subset=[col])
    if d.empty:
        return None
    title = label + (" — indexed (first day = 100)" if indexed else "") + (" — 7d avg" if smooth else "")
    fig = px.line(d, x="date", y=col, color="ticker", markers=True, hover_name="name",
                  color_discrete_map=color_map, title=title,
                  labels={"date": "Date", col: "Index" if indexed else label, "ticker": "Token"},
                  template="plotly_white", height=420)
    if log_scale and kind == "usd" and not indexed:
        fig.update_yaxes(type="log")
    return fig


def render_group(prefix, keys):
    for i in range(0, len(keys), 2):
        cols = st.columns(2)
        for c, k in zip(cols, keys[i:i + 2]):
            with c:
                fig = line_fig(k)
                if fig is None:
                    st.info(f"No data yet: {METRICS[k][0]}")
                else:
                    st.plotly_chart(fig, use_container_width=True, key=f"{prefix}_{k}")


# ==================================================
# Inner tabs
# ==================================================
tab_vol, tab_deriv, tab_liq, tab_cov, tab_rel, tab_data = st.tabs([
    "📊 Volume & Activity", "⚡ Derivatives", "🌊 Liquidity & Pricing", "🏦 Exchange Coverage",
    "🏁 AXL vs Peers Over Time", "🗂️ Data & Quality"
])

with tab_vol:
    render_group("vol", GROUPS["volume"])
    if indexed_mode:
        st.caption("Percentage-type metrics (changes, shares) are always shown as actual values, "
                   "because indexing to 100 is not meaningful for them.")

with tab_deriv:
    no_perp = [t for t in cdf["ticker"].unique() if cdf.loc[cdf["ticker"] == t, "oi_usd"].isna().all()]
    if no_perp:
        st.caption("No perpetual markets recorded for: " + ", ".join(no_perp))
    render_group("deriv", GROUPS["deriv"])

with tab_liq:
    st.caption("Depth is summed across exchanges and is a lower bound where exchanges report capped placeholder values.")
    render_group("liq", GROUPS["liq"])

with tab_cov:
    render_group("cov", GROUPS["cov"])

# --------------------------------------------------
# AXL vs peers over time
# --------------------------------------------------
with tab_rel:
    st.subheader("How Does AXL Compare With the Peer Group Day by Day?")
    key = st.selectbox("Metric", list(METRICS.keys()), format_func=lambda k: METRICS[k][0])
    label, kind, hib = METRICS[key]
    pv = cdf.pivot_table(index="date", columns="ticker", values=key, aggfunc="last")
    peer_cols = [c for c in pv.columns if c != FOCUS]
    if FOCUS not in pv.columns or pv[FOCUS].dropna().empty or not peer_cols:
        st.info("Not enough data for this metric yet.")
    else:
        med = pv[peer_cols].median(axis=1)
        col_a, col_b = st.columns(2)
        with col_a:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pv.index, y=pv[FOCUS], mode="lines+markers", name="AXL",
                                     line=dict(color=BLUE, width=2)))
            fig.add_trace(go.Scatter(x=pv.index, y=med, mode="lines+markers", name="Peer median",
                                     line=dict(color="#7F7F7F", width=2, dash="dash")))
            fig.update_layout(title=f"{label}: AXL vs Peer Median", template="plotly_white", height=420,
                              xaxis_title="Date", yaxis_title=label, hovermode="x unified")
            if log_scale and kind == "usd":
                fig.update_yaxes(type="log")
            st.plotly_chart(fig, use_container_width=True, key="rel_levels")
        with col_b:
            ratio = (pv[FOCUS] / med.where(med != 0)).dropna()
            if ratio.empty:
                st.info("The peer median is zero or missing, so the ratio cannot be drawn.")
            else:
                fig = go.Figure(go.Scatter(x=ratio.index, y=ratio.values, mode="lines+markers", name="AXL ÷ median",
                                           line=dict(color=BLUE, width=2)))
                fig.add_hline(y=1, line_dash="dash", line_color="black", line_width=1)
                fig.update_layout(title=f"{label}: AXL ÷ Peer Median", template="plotly_white", height=420,
                                  xaxis_title="Date", yaxis_title="Ratio (1 = same as median)",
                                  hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True, key="rel_ratio")

        asc = hib is False                        # lower-is-better metrics: rank 1 = lowest
        ranks = pv.rank(axis=1, method="min", ascending=asc)[FOCUS].dropna()
        counts = pv.notna().sum(axis=1).reindex(ranks.index)
        fig = go.Figure(go.Scatter(x=ranks.index, y=ranks.values, mode="lines+markers", name="AXL rank",
                                   line=dict(color=BLUE, width=2),
                                   customdata=counts.values,
                                   hovertemplate="%{x|%Y-%m-%d}<br>Rank %{y} of %{customdata}<extra></extra>"))
        fig.update_yaxes(autorange="reversed", dtick=1)
        fig.update_layout(title=f"AXL Rank by {label} (1 = " + ("lowest" if asc else "highest") + ")",
                          template="plotly_white", height=380, xaxis_title="Date", yaxis_title="Rank")
        st.plotly_chart(fig, use_container_width=True, key="rel_rank")

    st.subheader("Rank Summary (first vs latest day in range)")
    rows = []
    first_day, last_day = cdf["date"].min(), cdf["date"].max()
    for k, (lab, kd, h) in METRICS.items():
        if h is None:
            continue
        def rank_on(day):
            s = cdf[cdf["date"] == day][["ticker", k]].dropna().sort_values(k, ascending=(h is False))
            s = s.reset_index(drop=True)
            if FOCUS not in set(s["ticker"]):
                return None, len(s), np.nan
            return int(s.index[s["ticker"] == FOCUS][0]) + 1, len(s), float(s.loc[s["ticker"] == FOCUS, k].iloc[0])
        r0, n0, _ = rank_on(first_day)
        r1, n1, v1 = rank_on(last_day)
        change = "-" if r0 is None or r1 is None else ("▲ improved" if r1 < r0 else ("▼ worse" if r1 > r0 else "= same"))
        rows.append({"Metric": lab, "AXL latest": fmt_metric(v1, kd),
                     "Rank first day": "n/a" if r0 is None else f"#{r0} of {n0}",
                     "Rank latest day": "n/a" if r1 is None else f"#{r1} of {n1}", "Change": change})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Rank 1 = highest value, except spread, price dispersion, taker fee and top-exchange share, where 1 = lowest.")

# --------------------------------------------------
# Data & quality
# --------------------------------------------------
with tab_data:
    st.subheader("Recording Coverage")
    cov_rows = []
    all_days = pd.date_range(min_d, max_d, freq="D")
    for t in ticker_order:
        days = set(hist.loc[hist["ticker"] == t, "date"])
        missing = [d.date().isoformat() for d in all_days if d not in days]
        cov_rows.append({"Ticker": t, "Token": names.get(t, ""), "Days recorded": len(days),
                         "Missing days": len(missing), "Missing dates": ", ".join(missing[:10]) +
                         (" …" if len(missing) > 10 else "")})
    st.dataframe(pd.DataFrame(cov_rows), use_container_width=True, hide_index=True)
    st.caption("A missing day means the daily job did not run or that token's API could not be read that day. "
               "Past days cannot be recovered, because the API only exposes the last 24 hours.")

    st.subheader("Freshness of the Source Data")
    fr = hist[hist["date"] == latest_date][["ticker", "captured_at_utc", "last_updated"]].copy()
    fr["Hours between source update and snapshot"] = ((fr["captured_at_utc"] - fr["last_updated"])
                                                      .dt.total_seconds() / 3600).round(1)
    fr = fr.rename(columns={"ticker": "Ticker", "captured_at_utc": "Snapshot (UTC)",
                            "last_updated": "API dataset last updated (UTC)"})
    st.dataframe(fr, use_container_width=True, hide_index=True)
    st.caption("If the same 'last updated' time repeats on several days, the API did not refresh and those days "
               "would hold identical values.")

    st.subheader("Reconciliation With the API's Own Totals")
    rec = hist[["date", "ticker", "volume_24h", "api_total_volume", "oi_usd", "api_total_oi"]].copy()
    rec["Volume diff %"] = np.where(rec["api_total_volume"] > 0,
                                    (rec["volume_24h"] / rec["api_total_volume"] - 1) * 100, np.nan)
    rec["OI diff %"] = np.where(rec["api_total_oi"] > 0, (rec["oi_usd"] / rec["api_total_oi"] - 1) * 100, np.nan)
    bad = rec[(rec["Volume diff %"].abs() >= 0.5) | (rec["OI diff %"].abs() >= 0.5)]
    if bad.empty:
        st.success("Every recorded day matches the API's own totals (difference below 0.5%).")
    else:
        st.warning(f"{len(bad)} token-days differ from the API's own totals by 0.5% or more:")
        st.dataframe(bad.round({c: 3 for c in bad.select_dtypes("number").columns}),
                     use_container_width=True, hide_index=True)

    st.subheader("History Table")
    view = cdf.drop(columns=["api_total_volume", "api_total_oi"]).rename(columns={k: v[0] for k, v in METRICS.items()})
    view["date"] = view["date"].dt.date
    st.dataframe(view.round({c: 4 for c in view.select_dtypes("number").columns}),
                 use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", view.to_csv(index=False).encode("utf-8"),
                       file_name="axl_market_history.csv", mime="text/csv")

st.caption("Source: DefiLlama Markets API, recorded daily — https://defillama.com/api/public/markets/{token}")
