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

    col1, col2 = st.columns([1, 6])

    with col1:
        st.image(
            "https://axelarscan.io/logos/logo.png",
            width=18
        )

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

st.info(
    "All data is loaded from Axelar public API (no database required)."
)

# =====================================================
# FILTERS
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["month", "week", "day"]
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        pd.to_datetime("2025-01-01")
    )

with col3:
    end_date = st.date_input(
        "End Date",
        pd.to_datetime("2027-01-01")
    )

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

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("W")
        .apply(lambda r: r.start_time)
    )

elif timeframe == "month":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("M")
        .apply(lambda r: r.start_time)
    )

else:
    df["period"] = df["timestamp"]

grouped = (
    df.groupby("period")
    .sum(numeric_only=True)
    .reset_index()
)

grouped["total_txs"] = (
    grouped["gmp_num_txs"] +
    grouped["transfers_num_txs"]
)

grouped["total_volume"] = (
    grouped["gmp_volume"] +
    grouped["transfers_volume"]
)

# =====================================================
# BASE STATS
# =====================================================
daily_df = df.copy()

daily_df["day"] = daily_df["timestamp"].dt.date

daily_grouped = (
    daily_df.groupby("day")
    .sum(numeric_only=True)
    .reset_index()
)

daily_grouped["daily_volume"] = (
    daily_grouped["gmp_volume"] +
    daily_grouped["transfers_volume"]
)

daily_grouped["daily_txs"] = (
    daily_grouped["gmp_num_txs"] +
    daily_grouped["transfers_num_txs"]
)

avg_daily_volume = daily_grouped["daily_volume"].mean()
avg_daily_txs = daily_grouped["daily_txs"].mean()

weekly_df = df.copy()

weekly_df["week"] = (
    weekly_df["timestamp"]
    .dt
    .to_period("W")
    .apply(lambda r: r.start_time)
)

weekly_grouped = (
    weekly_df.groupby("week")
    .sum(numeric_only=True)
    .reset_index()
)

weekly_grouped["weekly_volume"] = (
    weekly_grouped["gmp_volume"] +
    weekly_grouped["transfers_volume"]
)

weekly_grouped["weekly_txs"] = (
    weekly_grouped["gmp_num_txs"] +
    weekly_grouped["transfers_num_txs"]
)

avg_weekly_volume = weekly_grouped["weekly_volume"].mean()
avg_weekly_txs = weekly_grouped["weekly_txs"].mean()

# =====================================================
# KPI ROW 1
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Transactions",
        f"{grouped['total_txs'].sum():,}"
    )

with col2:
    st.metric(
        "Total Volume",
        f"${grouped['total_volume'].sum():,.0f}"
    )

with col3:

    avg_volume_per_tx = (
        grouped["total_volume"].sum() /
        max(grouped["total_txs"].sum(), 1)
    )

    st.metric(
        "Avg Volume / Tx",
        f"${avg_volume_per_tx:,.2f}"
    )

# =====================================================
# KPI ROW 2
# =====================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Avg Daily Volume",
        f"${avg_daily_volume:,.0f}"
    )

with col2:
    st.metric(
        "Avg Weekly Volume",
        f"${avg_weekly_volume:,.0f}"
    )

with col3:
    st.metric(
        "Avg Daily Transactions",
        f"{avg_daily_txs:,.0f}"
    )

with col4:
    st.metric(
        "Avg Weekly Transactions",
        f"{avg_weekly_txs:,.0f}"
    )

# =====================================================
# KPI ROW 3
# =====================================================

def pct_change(series):

    if len(series) < 2:
        return 0

    return (
        (
            series.iloc[-1] - series.iloc[-2]
        ) / max(series.iloc[-2], 1)
    ) * 100


def last_diff(series):

    if len(series) < 2:
        return 0

    return series.iloc[-1] - series.iloc[-2]


# WEEKLY
df_w = df_raw.copy()

df_w["week"] = (
    df_w["timestamp"]
    .dt
    .to_period("W")
    .apply(lambda r: r.start_time)
)

w_group = (
    df_w.groupby("week")
    .sum(numeric_only=True)
    .reset_index()
)

w_group = w_group.sort_values("week")

w_group["tx"] = (
    w_group["gmp_num_txs"] +
    w_group["transfers_num_txs"]
)

w_group["vol"] = (
    w_group["gmp_volume"] +
    w_group["transfers_volume"]
)

weekly_tx_change = pct_change(w_group["tx"])
weekly_vol_change = pct_change(w_group["vol"])

weekly_tx_diff = last_diff(w_group["tx"])
weekly_vol_diff = last_diff(w_group["vol"])

# MONTHLY
df_m = df_raw.copy()

df_m["month"] = (
    df_m["timestamp"]
    .dt
    .to_period("M")
    .apply(lambda r: r.start_time)
)

m_group = (
    df_m.groupby("month")
    .sum(numeric_only=True)
    .reset_index()
)

m_group = m_group.sort_values("month")

m_group["tx"] = (
    m_group["gmp_num_txs"] +
    m_group["transfers_num_txs"]
)

m_group["vol"] = (
    m_group["gmp_volume"] +
    m_group["transfers_volume"]
)

monthly_tx_change = pct_change(m_group["tx"])
monthly_vol_change = pct_change(m_group["vol"])

monthly_tx_diff = last_diff(m_group["tx"])
monthly_vol_diff = last_diff(m_group["vol"])

# DISPLAY
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Weekly Volume % Change",
        f"{weekly_vol_change:.2f}%",
        delta=f"{weekly_vol_diff:,.0f}",
        delta_color="normal"
    )

with col2:
    st.metric(
        "Weekly Tx % Change",
        f"{weekly_tx_change:.2f}%",
        delta=f"{weekly_tx_diff:,.0f}",
        delta_color="normal"
    )

with col3:
    st.metric(
        "Monthly Volume % Change",
        f"{monthly_vol_change:.2f}%",
        delta=f"{monthly_vol_diff:,.0f}",
        delta_color="normal"
    )

with col4:
    st.metric(
        "Monthly Tx % Change",
        f"{monthly_tx_change:.2f}%",
        delta=f"{monthly_tx_diff:,.0f}",
        delta_color="normal"
    )

# =====================================================
# COLORS
# =====================================================
GMP_COLOR = "#ff7400"
TRANSFER_COLOR = "#00a1f7"

# =====================================================
# CHARTS ROW 4
# =====================================================
col1, col2 = st.columns(2)

with col1:

    fig1 = go.Figure()

    fig1.add_bar(
        x=grouped["period"],
        y=grouped["gmp_num_txs"],
        name="GMP",
        marker_color=GMP_COLOR
    )

    fig1.add_bar(
        x=grouped["period"],
        y=grouped["transfers_num_txs"],
        name="Transfers",
        marker_color=TRANSFER_COLOR
    )

    fig1.update_layout(
        barmode="stack",
        title="Transactions Over Time"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

with col2:

    fig2 = go.Figure()

    fig2.add_bar(
        x=grouped["period"],
        y=grouped["gmp_volume"],
        name="GMP",
        marker_color=GMP_COLOR
    )

    fig2.add_bar(
        x=grouped["period"],
        y=grouped["transfers_volume"],
        name="Transfers",
        marker_color=TRANSFER_COLOR
    )

    fig2.update_layout(
        barmode="stack",
        title="Volume Over Time"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# =====================================================
# CHARTS ROW 5 (NEW MONTHLY ANALYSIS)
# =====================================================

# DAILY BASE
monthly_daily = df.copy()

monthly_daily["day"] = monthly_daily["timestamp"].dt.date

daily_month = (
    monthly_daily.groupby("day")
    .sum(numeric_only=True)
    .reset_index()
)

daily_month["daily_volume"] = (
    daily_month["gmp_volume"] +
    daily_month["transfers_volume"]
)

daily_month["daily_txs"] = (
    daily_month["gmp_num_txs"] +
    daily_month["transfers_num_txs"]
)

daily_month["month"] = pd.to_datetime(
    daily_month["day"]
).to_period("M").astype(str)

# MONTHLY STATS VOLUME
monthly_volume_stats = (
    daily_month.groupby("month")["daily_volume"]
    .agg(["max", "mean", "min"])
    .reset_index()
)

monthly_volume_stats.columns = [
    "month",
    "max_volume",
    "avg_volume",
    "min_volume"
]

# MONTHLY STATS TXS
monthly_tx_stats = (
    daily_month.groupby("month")["daily_txs"]
    .agg(["max", "mean", "min"])
    .reset_index()
)

monthly_tx_stats.columns = [
    "month",
    "max_txs",
    "avg_txs",
    "min_txs"
]

col1, col2 = st.columns(2)

# =====================================================
# MONTHLY VOLUME STATS
# =====================================================
with col1:

    fig5 = go.Figure()

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["max_volume"],
            mode="lines+markers",
            name="Max Daily Volume"
        )
    )

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["avg_volume"],
            mode="lines+markers",
            name="Avg Daily Volume"
        )
    )

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["min_volume"],
            mode="lines+markers",
            name="Min Daily Volume"
        )
    )

    fig5.update_layout(
        title="Monthly Daily Volume Statistics",
        xaxis_title="Month",
        yaxis_title="Volume",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig5,
        use_container_width=True
    )

# =====================================================
# MONTHLY TX STATS
# =====================================================
with col2:

    fig6 = go.Figure()

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["max_txs"],
            mode="lines+markers",
            name="Max Daily Tx"
        )
    )

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["avg_txs"],
            mode="lines+markers",
            name="Avg Daily Tx"
        )
    )

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["min_txs"],
            mode="lines+markers",
            name="Min Daily Tx"
        )
    )

    fig6.update_layout(
        title="Monthly Daily Transaction Statistics",
        xaxis_title="Month",
        yaxis_title="Transactions",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig6,
        use_container_width=True
    )

# =====================================================
# DONUT CHARTS ROW 6
# =====================================================
col1, col2 = st.columns(2)

with col1:

    tx_df = pd.DataFrame({
        "Service": ["GMP", "Transfers"],
        "Value": [
            grouped["gmp_num_txs"].sum(),
            grouped["transfers_num_txs"].sum()
        ]
    })

    fig3 = px.pie(
        tx_df,
        names="Service",
        values="Value",
        hole=0.5,
        title="Transactions Share"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

with col2:

    vol_df = pd.DataFrame({
        "Service": ["GMP", "Transfers"],
        "Value": [
            grouped["gmp_volume"].sum(),
            grouped["transfers_volume"].sum()
        ]
    })

    fig4 = px.pie(
        vol_df,
        names="Service",
        values="Value",
        hole=0.5,
        title="Volume Share"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )
