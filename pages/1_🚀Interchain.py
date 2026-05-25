import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Axelar Dashboard",
    page_icon="🚀",
    layout="wide"
)

# =====================================================
# CSS
# =====================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1c1c1c, #111111);
    border: 1px solid rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 18px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.25);
    transition: 0.25s ease;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    border: 1px solid rgba(255,116,0,0.35);
    box-shadow: 0 8px 24px rgba(255,116,0,0.15);
}

[data-testid="metric-container"] label {
    color: #9f9f9f !important;
    font-size: 15px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: white;
    font-size: 32px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    url = "https://api.axelarscan.io/api/interchainChart"
    r = requests.get(url, timeout=30)
    data = r.json()["data"]
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


df_raw = load_data()
df = df_raw.copy()

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("### ")
    col1, col2 = st.columns([1, 6])

    with col1:
        st.image("https://axelarscan.io/logos/logo.png", width=18)

    with col2:
        st.markdown('Powered by [Axelar](https://x.com/axelar)')

    col1, col2 = st.columns([1, 6])

    with col1:
        st.image(
            "https://pbs.twimg.com/profile_images/2058533217540423680/JomSr3XY_400x400.jpg",
            width=18
        )

    with col2:
        st.markdown('Built by [Eman Raz](https://x.com/0xeman_raz)')

# =====================================================
# TITLE
# =====================================================
st.title("🚀 Interchain Analysis")

st.info("All data is loaded from Axelar public API (no database required).")

# =====================================================
# FILTERS
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox("Timeframe", ["month", "week", "day"])

with col2:
    start_date = st.date_input("Start Date", pd.to_datetime("2025-01-01"))

with col3:
    end_date = st.date_input("End Date", pd.to_datetime("2027-01-01"))

# =====================================================
# FILTER DATA
# =====================================================
df = df[
    (df["timestamp"] >= pd.to_datetime(start_date)) &
    (df["timestamp"] <= pd.to_datetime(end_date))
]

# =====================================================
# RESAMPLE
# =====================================================
if timeframe == "week":
    df["period"] = df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)

elif timeframe == "month":
    df["period"] = df["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)

else:
    df["period"] = df["timestamp"]

grouped = df.groupby("period").sum(numeric_only=True).reset_index()

grouped["total_txs"] = grouped["gmp_num_txs"] + grouped["transfers_num_txs"]
grouped["total_volume"] = grouped["gmp_volume"] + grouped["transfers_volume"]

# =====================================================
# KPI ROW 1
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Transactions", f"{grouped['total_txs'].sum():,}")

with col2:
    st.metric("Total Volume", f"${grouped['total_volume'].sum():,.0f}")

with col3:
    avg_volume_per_tx = grouped["total_volume"].sum() / max(grouped["total_txs"].sum(), 1)
    st.metric("Avg Volume / Tx", f"${avg_volume_per_tx:,.2f}")

# =====================================================
# KPI ROW 2
# =====================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Avg Daily Volume", f"${df.groupby(df['timestamp'].dt.date).sum(numeric_only=True).eval('gmp_volume + transfers_volume').mean():,.0f}")

with col2:
    weekly_df = df.copy()
    weekly_df["week"] = weekly_df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
    w = weekly_df.groupby("week").sum(numeric_only=True)
    st.metric("Avg Weekly Volume", f"${(w['gmp_volume']+w['transfers_volume']).mean():,.0f}")

with col3:
    daily_txs = df.groupby(df["timestamp"].dt.date).sum(numeric_only=True)
    st.metric("Avg Daily Transactions", f"{(daily_txs['gmp_num_txs']+daily_txs['transfers_num_txs']).mean():,.0f}")

with col4:
    st.metric("Avg Weekly Transactions", f"{(w['gmp_num_txs']+w['transfers_num_txs']).mean():,.0f}")

# =====================================================
# KPI ROW 3 (UPDATED)
# =====================================================

def pct_change(series):
    if len(series) < 2:
        return 0
    return ((series.iloc[-1] - series.iloc[-2]) / max(series.iloc[-2], 1)) * 100

# WEEKLY
df_w = df_raw.copy()
df_w["week"] = df_w["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
w_group = df_w.groupby("week").sum(numeric_only=True).reset_index()
w_group["tx"] = w_group["gmp_num_txs"] + w_group["transfers_num_txs"]
w_group["vol"] = w_group["gmp_volume"] + w_group["transfers_volume"]

weekly_tx_change = pct_change(w_group["tx"])
weekly_vol_change = pct_change(w_group["vol"])

# MONTHLY
df_m = df_raw.copy()
df_m["month"] = df_m["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)
m_group = df_m.groupby("month").sum(numeric_only=True).reset_index()
m_group["tx"] = m_group["gmp_num_txs"] + m_group["transfers_num_txs"]
m_group["vol"] = m_group["gmp_volume"] + m_group["transfers_volume"]

monthly_tx_change = pct_change(m_group["tx"])
monthly_vol_change = pct_change(m_group["vol"])

def arrow(val):
    if val >= 0:
        return f"⬆ مقدار تغییر: {val:.2f}%"
    else:
        return f"⬇ مقدار تغییر: {val:.2f}%"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Weekly Volume % Change",
        f"{weekly_vol_change:.2f}%",
        arrow(weekly_vol_change)
    )

with col2:
    st.metric(
        "Weekly Tx % Change",
        f"{weekly_tx_change:.2f}%",
        arrow(weekly_tx_change)
    )

with col3:
    st.metric(
        "Monthly Volume % Change",
        f"{monthly_vol_change:.2f}%",
        arrow(monthly_vol_change)
    )

with col4:
    st.metric(
        "Monthly Tx % Change",
        f"{monthly_tx_change:.2f}%",
        arrow(monthly_tx_change)
    )

# =====================================================
# CHARTS
# =====================================================
GMP_COLOR = "#ff7400"
TRANSFER_COLOR = "#00a1f7"

col1, col2 = st.columns(2)

with col1:
    fig1 = go.Figure()
    fig1.add_bar(x=grouped["period"], y=grouped["gmp_num_txs"], name="GMP", marker_color=GMP_COLOR)
    fig1.add_bar(x=grouped["period"], y=grouped["transfers_num_txs"], name="Transfers", marker_color=TRANSFER_COLOR)
    fig1.update_layout(barmode="stack", title="Transactions Over Time")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = go.Figure()
    fig2.add_bar(x=grouped["period"], y=grouped["gmp_volume"], name="GMP", marker_color=GMP_COLOR)
    fig2.add_bar(x=grouped["period"], y=grouped["transfers_volume"], name="Transfers", marker_color=TRANSFER_COLOR)
    fig2.update_layout(barmode="stack", title="Volume Over Time")
    st.plotly_chart(fig2, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    tx_df = pd.DataFrame({
        "Service": ["GMP", "Transfers"],
        "Value": [grouped["gmp_num_txs"].sum(), grouped["transfers_num_txs"].sum()]
    })

    fig3 = px.pie(tx_df, names="Service", values="Value", hole=0.5, title="Transactions Share")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    vol_df = pd.DataFrame({
        "Service": ["GMP", "Transfers"],
        "Value": [grouped["gmp_volume"].sum(), grouped["transfers_volume"].sum()]
    })

    fig4 = px.pie(vol_df, names="Service", values="Value", hole=0.5, title="Volume Share")
    st.plotly_chart(fig4, use_container_width=True)
