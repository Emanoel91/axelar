import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

try:  # optional: helps if the API rejects plain python-requests traffic
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
st.title("🛡️ Axelar Validators")

# SIDEBAR
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
# Configuration
# ==================================================
API_URL = "https://api.axelarscan.io/validator/getValidators"
BONDED = "BOND_STATUS_BONDED"
STATUS_LABELS = {
    "BOND_STATUS_BONDED": "Bonded (Active)",
    "BOND_STATUS_UNBONDING": "Unbonding",
    "BOND_STATUS_UNBONDED": "Unbonded",
}
STATUS_COLORS = {"Bonded (Active)": "#00B8F4", "Unbonding": "#FF8A00", "Unbonded": "#B0B0B0"}
BLUE = "#00B8F4"
ORANGE = "#FF8A00"

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
@st.cache_data(ttl=300)
def load_raw():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        r = requests.get(API_URL, headers=headers, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as first_err:
        if cffi_requests is None:
            raise first_err
        r = cffi_requests.get(API_URL, impersonate="chrome", timeout=60)
        r.raise_for_status()
        return r.json()


# ==================================================
# Helpers
# ==================================================
def fmt_num(x, decimals=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    if abs(x) >= 1e9:
        return f"{x / 1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"{x / 1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"{x / 1e3:,.1f}K"
    return f"{x:,.{decimals}f}"


def parse_dt(series):
    try:
        return pd.to_datetime(series, utc=True, errors="coerce", format="ISO8601")
    except (TypeError, ValueError):
        return pd.to_datetime(series, utc=True, errors="coerce")


def nakamoto(values, threshold):
    """Smallest number of top validators whose combined share exceeds `threshold` (0-1)."""
    v = np.sort(np.asarray(values, dtype=float))[::-1]
    total = v.sum()
    if total <= 0:
        return None
    return int(np.searchsorted(np.cumsum(v) / total, threshold, side="right") + 1)


def gini(values):
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return np.nan
    cum = np.cumsum(v)
    return (n + 1 - 2 * np.sum(cum) / cum[-1]) / n


def build_df(items):
    rows = []
    for v in items:
        desc = v.get("description") or {}
        comm = v.get("commission") or {}
        rates = comm.get("commission_rates") or {}
        rows.append({
            "operator_address": v.get("operator_address"),
            "consensus_address": v.get("consensus_address"),
            "delegator_address": v.get("delegator_address"),
            "broadcaster_address": v.get("broadcaster_address"),
            "moniker": (desc.get("moniker") or "").strip(),
            "identity": (desc.get("identity") or "").strip(),
            "website": (desc.get("website") or "").strip(),
            "security_contact": (desc.get("security_contact") or "").strip(),
            "details": (desc.get("details") or "").strip(),
            "status": v.get("status"),
            "jailed": bool(v.get("jailed")),
            "tombstoned": bool(v.get("tombstoned")),
            "tokens": v.get("tokens"),
            "delegator_shares": v.get("delegator_shares"),
            "quadratic_voting_power": v.get("quadratic_voting_power"),
            "commission_rate": rates.get("rate"),
            "commission_max_rate": rates.get("max_rate"),
            "commission_max_change_rate": rates.get("max_change_rate"),
            "commission_update_time": comm.get("update_time"),
            "min_self_delegation": v.get("min_self_delegation"),
            "unbonding_height": v.get("unbonding_height"),
            "unbonding_time": v.get("unbonding_time"),
            "unbonding_ids_count": len(v.get("unbonding_ids") or []),
            "start_height": v.get("start_height"),
            "start_proxy_height": v.get("start_proxy_height"),
            "jailed_until": v.get("jailed_until"),
            "missed_blocks_counter": v.get("missed_blocks_counter"),
            "uptime": v.get("uptime"),
            "proposed_blocks": v.get("proposed_blocks"),
            "proposed_blocks_proportion": v.get("proposed_blocks_proportion"),
            "heartbeat_uptime": v.get("heartbeat_uptime"),
            "stale_heartbeats": bool(v.get("stale_heartbeats")),
        })
    df = pd.DataFrame(rows)

    num_cols = ["tokens", "delegator_shares", "quadratic_voting_power", "commission_rate", "commission_max_rate",
                "commission_max_change_rate", "min_self_delegation", "unbonding_height", "start_height",
                "start_proxy_height", "jailed_until", "missed_blocks_counter", "uptime", "proposed_blocks",
                "proposed_blocks_proportion", "heartbeat_uptime"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["commission_rate", "commission_max_rate", "commission_max_change_rate"]:
        df[c] = df[c] * 100  # fraction -> percent

    df["unbonding_time"] = parse_dt(df["unbonding_time"])
    df["commission_update_time"] = parse_dt(df["commission_update_time"])
    df["jailed_until_dt"] = pd.to_datetime(df["jailed_until"], unit="ms", utc=True, errors="coerce")
    df.loc[df["jailed_until_dt"] < pd.Timestamp("2010-01-01", tz="UTC"), "jailed_until_dt"] = pd.NaT

    df["status_label"] = df["status"].map(STATUS_LABELS).fillna(df["status"])

    df["label"] = np.where(df["moniker"] != "", df["moniker"], "(unnamed) " + df["operator_address"].str[-6:])
    dup = df["label"].duplicated(keep=False)
    df.loc[dup, "label"] = df.loc[dup, "label"] + " · " + df.loc[dup, "operator_address"].str[-4:]
    df["label_short"] = df["label"].str.slice(0, 28)

    # share-price indicator: tokens/shares < 1 means the validator's tokens were reduced (e.g. slashed)
    df["slash_indicator_pct"] = np.where(
        df["delegator_shares"] > 0, (1 - df["tokens"] / df["delegator_shares"]) * 100, np.nan)
    df["slash_indicator_pct"] = df["slash_indicator_pct"].clip(lower=0)
    return df


# ==================================================
# Load + prepare
# ==================================================
try:
    raw = load_raw()
except Exception as e:
    st.error(f"❌ Error fetching validator data: {e}")
    st.stop()

items = raw.get("data", []) if isinstance(raw, dict) else raw
if not items:
    st.warning("The API returned no validators.")
    st.stop()

df = build_df(items)
now_utc = pd.Timestamp.now(tz="UTC")

act = df[df["status"] == BONDED].copy().sort_values("tokens", ascending=False).reset_index(drop=True)
if act.empty:
    st.warning("No bonded validators found in the response.")
    st.stop()

act["rank"] = act.index + 1
act["stake_share_pct"] = act["tokens"] / act["tokens"].sum() * 100
act["cum_share_pct"] = act["stake_share_pct"].cumsum()
act["qvp_share_pct"] = act["quadratic_voting_power"] / act["quadratic_voting_power"].sum() * 100
act["cum_qvp_share_pct"] = act["qvp_share_pct"].cumsum()
act["proposed_share_pct"] = np.where(
    act["proposed_blocks"].sum() > 0, act["proposed_blocks"] / act["proposed_blocks"].sum() * 100, np.nan)
rank_map = act.set_index("operator_address")["rank"].to_dict()

total_bonded = act["tokens"].sum()
w_commission = np.average(act["commission_rate"].fillna(0), weights=act["tokens"])

# ==================================================
# Header KPIs
# ==================================================
st.markdown("### 💎 Validator Set KPIs")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🧮 Total Validators (all statuses)", f"{len(df):,}")
c2.metric("✅ Active (Bonded)", f"{len(act):,}")
c3.metric("⛓️ Jailed", f"{int(df['jailed'].sum()):,}")
c4.metric("☠️ Tombstoned", f"{int(df['tombstoned'].sum()):,}")
st.write(" ")
c5, c6, c7, c8 = st.columns(4)
c5.metric("🔒 Total Bonded Stake", f"{fmt_num(total_bonded)} AXL")
c6.metric("💸 Avg Commission (active)", f"{act['commission_rate'].mean():.2f}%")
c7.metric("⚖️ Stake-Weighted Commission", f"{w_commission:.2f}%")
c8.metric("📶 Avg Uptime (active)", f"{act['uptime'].mean():.2f}%")
st.write(" ")

# ==================================================
# Inner tabs
# ==================================================
tab_over, tab_stake, tab_comm, tab_perf, tab_risk, tab_prof, tab_exp = st.tabs([
    "🌐 Overview", "🏆 Stake & Decentralization", "💸 Commission", "⚙️ Performance",
    "🚨 Risk & Jailing", "🪪 Profiles", "🔍 Explorer & Raw Data"
])

# --------------------------------------------------
# TAB 1 — Overview
# --------------------------------------------------
with tab_over:
    st.subheader("Validator Status")
    status_counts = df["status_label"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    stake_by_status = df.groupby("status_label", as_index=False)["tokens"].sum()

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.pie(status_counts, names="status", values="count", hole=0.45,
                     title="Validators by Status", template="plotly_white", height=420,
                     color="status", color_discrete_map=STATUS_COLORS)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = px.bar(stake_by_status, x="status_label", y="tokens", color="status_label",
                     title="Total Tokens by Status (AXL)", template="plotly_white", height=420,
                     labels={"status_label": "Status", "tokens": "Tokens (AXL)"},
                     color_discrete_map=STATUS_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        jc = df.assign(jail=np.where(df["jailed"], "Jailed", "Not jailed")) \
               .groupby(["status_label", "jail"], as_index=False).size()
        fig = px.bar(jc, x="status_label", y="size", color="jail", barmode="stack",
                     title="Jailed vs Not Jailed by Status", template="plotly_white", height=420,
                     labels={"status_label": "Status", "size": "Validators", "jail": ""},
                     color_discrete_map={"Jailed": "red", "Not jailed": "green"})
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        top10 = act.head(10)
        rest = act["tokens"].iloc[10:].sum()
        d = pd.concat([top10[["label_short", "tokens"]],
                       pd.DataFrame([{"label_short": "All others", "tokens": rest}])])
        fig = px.pie(d, names="label_short", values="tokens", hole=0.45,
                     title="Stake Share — Top 10 vs Others (active set)", template="plotly_white", height=420)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary Table")
    summary = df.groupby("status_label").agg(
        validators=("operator_address", "count"),
        jailed=("jailed", "sum"),
        tombstoned=("tombstoned", "sum"),
        total_tokens=("tokens", "sum"),
        avg_commission_pct=("commission_rate", "mean"),
    ).reset_index().round(2)
    st.dataframe(summary, use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 2 — Stake & Decentralization
# --------------------------------------------------
with tab_stake:
    st.subheader("Decentralization Metrics (active set)")
    n33_lin = nakamoto(act["tokens"], 1 / 3)
    n67_lin = nakamoto(act["tokens"], 2 / 3)
    n33_q = nakamoto(act["quadratic_voting_power"], 1 / 3)
    n67_q = nakamoto(act["quadratic_voting_power"], 2 / 3)
    hhi = float(((act["stake_share_pct"] / 100) ** 2).sum() * 10000)
    g = gini(act["tokens"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🧩 Nakamoto Coeff. (>33.3%, stake)", n33_lin)
    m2.metric("🧩 Nakamoto Coeff. (>66.7%, stake)", n67_lin)
    m3.metric("🧩 Nakamoto Coeff. (>33.3%, quadratic)", n33_q)
    m4.metric("🧩 Nakamoto Coeff. (>66.7%, quadratic)", n67_q)
    st.write(" ")
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("🥇 Top 5 Share", f"{act['stake_share_pct'].head(5).sum():.1f}%")
    m6.metric("🏅 Top 10 Share", f"{act['stake_share_pct'].head(10).sum():.1f}%")
    m7.metric("📐 HHI (0–10,000)", f"{hhi:,.0f}")
    m8.metric("📉 Gini Coefficient", f"{g:.3f}")
    st.caption("Nakamoto coefficient = minimum number of validators needed to exceed the given share of power. "
               "'Quadratic' uses the `quadratic_voting_power` field returned by the API.")

    st.subheader("Top Validators by Stake")
    top_n = st.slider("Number of validators", 5, min(60, len(act)), min(20, len(act)))
    d = act.head(top_n)
    fig = px.bar(d, x="label_short", y="tokens", title=f"Top {top_n} Validators by Tokens (AXL)",
                 labels={"label_short": "Validator", "tokens": "Tokens (AXL)"},
                 template="plotly_white", height=500, color_discrete_sequence=[BLUE])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Cumulative Stake Concentration")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=act["rank"], y=act["cum_share_pct"], mode="lines", name="Stake",
                             line=dict(color=BLUE, width=3)))
    fig.add_trace(go.Scatter(x=act["rank"], y=act["cum_qvp_share_pct"], mode="lines", name="Quadratic power",
                             line=dict(color=ORANGE, width=3)))
    fig.add_hline(y=100 / 3, line_dash="dash", line_color="red", annotation_text="33.3%")
    fig.add_hline(y=200 / 3, line_dash="dash", line_color="black", annotation_text="66.7%")
    fig.update_layout(title="Cumulative Share of Voting Power by Validator Rank", template="plotly_white",
                      height=500, xaxis_title="Validator rank", yaxis_title="Cumulative share (%)",
                      hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        top15 = act.head(15)
        d = top15.melt(id_vars="label_short", value_vars=["stake_share_pct", "qvp_share_pct"],
                       var_name="Metric", value_name="Share (%)")
        d["Metric"] = d["Metric"].map({"stake_share_pct": "Stake share", "qvp_share_pct": "Quadratic share"})
        fig = px.bar(d, x="label_short", y="Share (%)", color="Metric", barmode="group",
                     title="Stake Share vs Quadratic Voting Share (Top 15)", template="plotly_white",
                     height=480, labels={"label_short": "Validator"},
                     color_discrete_map={"Stake share": BLUE, "Quadratic share": ORANGE})
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        tm = act.head(25)[["label_short", "tokens"]].copy()
        rest = act["tokens"].iloc[25:].sum()
        if rest > 0:
            tm = pd.concat([tm, pd.DataFrame([{"label_short": "Others", "tokens": rest}])])
        fig = px.treemap(tm, path=["label_short"], values="tokens", title="Stake Treemap (Top 25 + Others)",
                         template="plotly_white", height=480)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Stake Distribution")
    fig = px.histogram(act, x="tokens", nbins=30, log_y=True, title="Distribution of Validator Stake (log count)",
                       labels={"tokens": "Tokens (AXL)"}, template="plotly_white", height=420,
                       color_discrete_sequence=[BLUE])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Ranking Table")
    st.dataframe(
        act[["rank", "label", "tokens", "stake_share_pct", "cum_share_pct", "quadratic_voting_power",
             "qvp_share_pct", "commission_rate", "uptime"]]
        .rename(columns={"label": "Validator"}).round(3),
        use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 3 — Commission
# --------------------------------------------------
with tab_comm:
    st.subheader("Commission Overview (active set)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📊 Average", f"{act['commission_rate'].mean():.2f}%")
    k2.metric("📍 Median", f"{act['commission_rate'].median():.2f}%")
    k3.metric("⚖️ Stake-Weighted", f"{w_commission:.2f}%")
    k4.metric("0️⃣ Zero-Commission Validators", f"{int((act['commission_rate'] == 0).sum())}")
    st.write(" ")
    k5, k6, k7, k8 = st.columns(4)
    k5.metric("🔻 Lowest", f"{act['commission_rate'].min():.2f}%")
    k6.metric("🔺 Highest", f"{act['commission_rate'].max():.2f}%")
    k7.metric("🔒 Avg Max Rate", f"{act['commission_max_rate'].mean():.2f}%")
    k8.metric("🔁 Avg Max Daily Change", f"{act['commission_max_change_rate'].mean():.2f}%")

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.histogram(act, x="commission_rate", nbins=25, title="Commission Rate Distribution (%)",
                           labels={"commission_rate": "Commission (%)"}, template="plotly_white", height=430,
                           color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = px.scatter(act, x="tokens", y="commission_rate", hover_name="label", log_x=True,
                         title="Commission vs Stake (log x)", template="plotly_white", height=430,
                         labels={"tokens": "Tokens (AXL)", "commission_rate": "Commission (%)"},
                         color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.histogram(act, x="commission_max_rate", nbins=20, title="Max Commission Rate Cap (%)",
                           labels={"commission_max_rate": "Max rate (%)"}, template="plotly_white", height=400,
                           color_discrete_sequence=[ORANGE])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = px.histogram(act, x="commission_max_change_rate", nbins=20,
                           title="Max Daily Commission Change (%)",
                           labels={"commission_max_change_rate": "Max change rate (%)"},
                           template="plotly_white", height=400, color_discrete_sequence=[ORANGE])
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Commission Staleness")
    act["days_since_commission_update"] = (now_utc - act["commission_update_time"]).dt.days
    fig = px.histogram(act.dropna(subset=["days_since_commission_update"]), x="days_since_commission_update",
                       nbins=25, title="Days Since Last Commission Update",
                       labels={"days_since_commission_update": "Days"}, template="plotly_white", height=400,
                       color_discrete_sequence=[BLUE])
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    cols = ["label", "tokens", "commission_rate", "commission_max_rate", "commission_max_change_rate"]
    with col_a:
        st.markdown("**Lowest commission (top 10 by stake among them)**")
        st.dataframe(act.sort_values(["commission_rate", "tokens"], ascending=[True, False])[cols].head(10)
                     .rename(columns={"label": "Validator"}).round(3), use_container_width=True, hide_index=True)
    with col_b:
        st.markdown("**Highest commission**")
        st.dataframe(act.sort_values("commission_rate", ascending=False)[cols].head(10)
                     .rename(columns={"label": "Validator"}).round(3), use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 4 — Performance
# --------------------------------------------------
with tab_perf:
    st.subheader("Performance (active set)")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("📶 Avg Uptime", f"{act['uptime'].mean():.2f}%")
    p2.metric("🔻 Min Uptime", f"{act['uptime'].min():.2f}%")
    p3.metric("⚠️ Uptime < 99%", f"{int((act['uptime'] < 99).sum())}")
    p4.metric("🧱 Total Proposed Blocks", f"{int(act['proposed_blocks'].sum()):,}")
    st.write(" ")
    p5, p6, p7, p8 = st.columns(4)
    p5.metric("❌ Avg Missed Blocks", f"{act['missed_blocks_counter'].mean():.1f}")
    p6.metric("❌ Max Missed Blocks", f"{int(act['missed_blocks_counter'].max())}")
    p7.metric("💓 Avg Heartbeat Uptime", f"{act['heartbeat_uptime'].mean():.2f}%")
    p8.metric("🕸️ Stale Heartbeats", f"{int(act['stale_heartbeats'].sum())}")

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.histogram(act, x="uptime", nbins=25, title="Uptime Distribution (%)",
                           labels={"uptime": "Uptime (%)"}, template="plotly_white", height=420,
                           color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = act.sort_values("missed_blocks_counter", ascending=False).head(20)
        fig = px.bar(d, x="label_short", y="missed_blocks_counter", title="Top 20 by Missed Blocks",
                     labels={"label_short": "Validator", "missed_blocks_counter": "Missed blocks"},
                     template="plotly_white", height=420, color_discrete_sequence=["red"])
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Block Proposals vs Stake")
    if act["proposed_blocks"].sum() > 0:
        mx = float(max(act["stake_share_pct"].max(), act["proposed_share_pct"].max()))
        fig = px.scatter(act, x="stake_share_pct", y="proposed_share_pct", hover_name="label",
                         title="Share of Proposed Blocks vs Share of Stake",
                         labels={"stake_share_pct": "Stake share (%)", "proposed_share_pct": "Proposed blocks share (%)"},
                         template="plotly_white", height=480, color_discrete_sequence=[BLUE])
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Proportional",
                                 line=dict(color="black", dash="dash")))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Points above the dashed line proposed more blocks than their stake share would suggest.")
    else:
        st.info("No block-proposal data available.")

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.histogram(act, x="heartbeat_uptime", nbins=20, title="Heartbeat Uptime Distribution (%)",
                           labels={"heartbeat_uptime": "Heartbeat uptime (%)"}, template="plotly_white",
                           height=400, color_discrete_sequence=[ORANGE])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        sh = act["stale_heartbeats"].map({True: "Stale", False: "Fresh"}).value_counts().reset_index()
        sh.columns = ["state", "count"]
        fig = px.pie(sh, names="state", values="count", hole=0.45, title="Heartbeat Freshness",
                     template="plotly_white", height=400, color="state",
                     color_discrete_map={"Stale": "red", "Fresh": "green"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Lowest-Uptime Validators")
    st.dataframe(
        act.sort_values("uptime")[["label", "tokens", "uptime", "missed_blocks_counter", "proposed_blocks",
                                   "heartbeat_uptime", "stale_heartbeats"]].head(15)
        .rename(columns={"label": "Validator"}).round(3),
        use_container_width=True, hide_index=True)

# --------------------------------------------------
# TAB 5 — Risk & Jailing
# --------------------------------------------------
with tab_risk:
    st.subheader("Risk Indicators (all validators)")
    jailed_df = df[df["jailed"]]
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("⛓️ Currently Jailed", f"{len(jailed_df)}")
    r2.metric("🔒 Tokens Held by Jailed", f"{fmt_num(jailed_df['tokens'].sum())} AXL")
    r3.metric("☠️ Tombstoned", f"{int(df['tombstoned'].sum())}")
    r4.metric("📜 Validators With Jail History", f"{int(df['jailed_until_dt'].notna().sum())}")

    st.subheader("Currently Jailed Validators")
    if len(jailed_df):
        st.dataframe(
            jailed_df.sort_values("tokens", ascending=False)[
                ["label", "status_label", "tokens", "jailed_until_dt", "missed_blocks_counter", "tombstoned"]]
            .rename(columns={"label": "Validator", "status_label": "Status", "jailed_until_dt": "Jailed until (UTC)"}),
            use_container_width=True, hide_index=True)
    else:
        st.success("No validators are currently jailed.")

    col_a, col_b = st.columns(2)
    with col_a:
        jh = df.dropna(subset=["jailed_until_dt"]).copy()
        if len(jh):
            jh["month"] = jh["jailed_until_dt"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
            m = jh.groupby("month", as_index=False).size()
            fig = px.bar(m, x="month", y="size", title="Jail Release Dates by Month",
                         labels={"month": "Month", "size": "Validators"}, template="plotly_white", height=420,
                         color_discrete_sequence=["red"])
            st.plotly_chart(fig, use_container_width=True)
            st.caption("`jailed_until` is the end of the most recent jail period, so this approximates when "
                       "validators were last jailed.")
        else:
            st.info("No jail history in the data.")
    with col_b:
        ub = df[(df["status"] != BONDED)].dropna(subset=["unbonding_time"]).copy()
        if len(ub):
            ub["month"] = ub["unbonding_time"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
            m = ub.groupby("month", as_index=False).size()
            fig = px.bar(m, x="month", y="size", title="Unbonding Completion Dates (non-active) by Month",
                         labels={"month": "Month", "size": "Validators"}, template="plotly_white", height=420,
                         color_discrete_sequence=[ORANGE])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No unbonding data for non-active validators.")

    st.subheader("Token Reduction Indicator (1 − tokens / delegator shares)")
    st.caption("A value above zero means each share is backed by fewer tokens than 1:1, which is consistent with a "
               "past slash of the validator's stake.")
    sl = df[df["slash_indicator_pct"] > 0.0001].sort_values("slash_indicator_pct", ascending=False).head(25)
    if len(sl):
        fig = px.bar(sl, x="label_short", y="slash_indicator_pct", color="status_label",
                     title="Validators With Reduced Token/Share Ratio (Top 25)",
                     labels={"label_short": "Validator", "slash_indicator_pct": "Reduction (%)",
                             "status_label": "Status"},
                     template="plotly_white", height=450, color_discrete_map=STATUS_COLORS)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No validators show a reduced token/share ratio.")

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.histogram(df, x="min_self_delegation", nbins=20, log_y=True,
                           title="Min Self-Delegation Distribution (AXL)",
                           labels={"min_self_delegation": "Min self-delegation"},
                           template="plotly_white", height=400, color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        d = df[df["unbonding_ids_count"] > 0].sort_values("unbonding_ids_count", ascending=False).head(20)
        if len(d):
            fig = px.bar(d, x="label_short", y="unbonding_ids_count", title="Pending Unbonding Entries (Top 20)",
                         labels={"label_short": "Validator", "unbonding_ids_count": "Unbonding IDs"},
                         template="plotly_white", height=400, color_discrete_sequence=[ORANGE])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pending unbonding entries.")

# --------------------------------------------------
# TAB 6 — Profiles
# --------------------------------------------------
with tab_prof:
    st.subheader("Profile Completeness (active set)")
    comp = pd.DataFrame({
        "Field": ["Name (moniker)", "Identity (Keybase)", "Website", "Security contact", "Details"],
        "Share of validators (%)": [
            (act["moniker"] != "").mean() * 100,
            (act["identity"] != "").mean() * 100,
            (act["website"] != "").mean() * 100,
            (act["security_contact"] != "").mean() * 100,
            (act["details"] != "").mean() * 100,
        ],
    })
    fig = px.bar(comp, x="Field", y="Share of validators (%)", title="Share of Active Validators With Each Field",
                 template="plotly_white", height=420, color_discrete_sequence=[BLUE], range_y=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Validator Directory")
    directory = act[["rank", "label", "tokens", "commission_rate", "uptime", "website", "security_contact"]] \
        .rename(columns={"label": "Validator"}).round(3)
    st.dataframe(
        directory, use_container_width=True, hide_index=True,
        column_config={"website": st.column_config.LinkColumn("Website")})

# --------------------------------------------------
# TAB 7 — Explorer & Raw Data
# --------------------------------------------------
with tab_exp:
    st.subheader("Validator Explorer")
    options = df.sort_values("tokens", ascending=False)["label"].tolist()
    sel = st.selectbox("Select validator", options, index=0)
    v = df[df["label"] == sel].iloc[0]

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Status", v["status_label"])
    e2.metric("Tokens (AXL)", fmt_num(v["tokens"]))
    e3.metric("Active Rank", f"#{rank_map[v['operator_address']]}" if v["operator_address"] in rank_map else "-")
    e4.metric("Commission", "-" if pd.isna(v["commission_rate"]) else f"{v['commission_rate']:.2f}%")
    st.write(" ")
    e5, e6, e7, e8 = st.columns(4)
    e5.metric("Uptime", "-" if pd.isna(v["uptime"]) else f"{v['uptime']:.2f}%")
    e6.metric("Missed Blocks", "-" if pd.isna(v["missed_blocks_counter"]) else f"{int(v['missed_blocks_counter'])}")
    e7.metric("Proposed Blocks", "-" if pd.isna(v["proposed_blocks"]) else f"{int(v['proposed_blocks'])}")
    e8.metric("Quadratic Voting Power", "-" if pd.isna(v["quadratic_voting_power"])
              else f"{int(v['quadratic_voting_power']):,}")

    if v["details"]:
        st.markdown(f"**About:** {v['details']}")
    if v["website"]:
        st.markdown(f"**Website:** {v['website']}")
    if v["security_contact"]:
        st.markdown(f"**Security contact:** {v['security_contact']}")
    st.markdown(f"[Open on Axelarscan](https://axelarscan.io/validator/{v['operator_address']})")
    st.markdown("**Addresses**")
    st.code(f"Operator:    {v['operator_address']}\n"
            f"Delegator:   {v['delegator_address']}\n"
            f"Consensus:   {v['consensus_address']}\n"
            f"Broadcaster: {v['broadcaster_address']}", language="text")

    st.subheader("Filterable Table")
    f1, f2, f3 = st.columns(3)
    statuses = f1.multiselect("Status", sorted(df["status_label"].unique()), default=sorted(df["status_label"].unique()))
    jail_filter = f2.selectbox("Jailed", ["All", "Jailed only", "Not jailed only"])
    query = f3.text_input("Search name / address")

    view = df[df["status_label"].isin(statuses)]
    if jail_filter == "Jailed only":
        view = view[view["jailed"]]
    elif jail_filter == "Not jailed only":
        view = view[~view["jailed"]]
    if query:
        q = query.lower()
        view = view[view["label"].str.lower().str.contains(q, regex=False)
                    | view["operator_address"].str.lower().str.contains(q, regex=False)]

    show_cols = ["label", "status_label", "jailed", "tombstoned", "tokens", "quadratic_voting_power",
                 "commission_rate", "commission_max_rate", "uptime", "missed_blocks_counter", "proposed_blocks",
                 "heartbeat_uptime", "stale_heartbeats", "jailed_until_dt", "unbonding_time", "website",
                 "operator_address"]
    st.dataframe(view[show_cols].sort_values("tokens", ascending=False).rename(columns={"label": "Validator"}),
                 use_container_width=True, hide_index=True,
                 column_config={"website": st.column_config.LinkColumn("Website")})

    csv = view.drop(columns=["label_short"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, file_name="axelar_validators.csv", mime="text/csv")

    with st.expander("Show raw API JSON (first 3 validators)"):
        st.json(items[:3], expanded=False)

st.caption("Source: Axelarscan API — https://api.axelarscan.io/validator/getValidators")
