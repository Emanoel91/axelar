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

/* =========================
GLOBAL
========================= */

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* =========================
METRIC CARDS
========================= */

[data-testid="metric-container"] {

    background: linear-gradient(
        145deg,
        #1c1c1c,
        #111111
    );

    border: 1px solid rgba(255,255,255,0.05);

    padding: 20px;

    border-radius: 18px;

    box-shadow:
        0 4px 15px rgba(0,0,0,0.25);

    transition: 0.25s ease;
}

[data-testid="metric-container"]:hover {

    transform: translateY(-4px);

    border: 1px solid rgba(255,116,0,0.35);

    box-shadow:
        0 8px 24px rgba(255,116,0,0.15);
}

/* metric label */
[data-testid="metric-container"] label {

    color: #9f9f9f !important;

    font-size: 15px !important;
}

/* metric value */
[data-testid="metric-container"] [data-testid="stMetricValue"] {

    color: white;

    font-size: 32px;
}

/* =========================
RESPONSIVE
========================= */

@media (max-width: 1200px) {

    [data-testid="metric-container"] [data-testid="stMetricValue"] {

        font-size: 26px;
    }
}

@media (max-width: 768px) {

    [data-testid="metric-container"] {

        padding: 16px;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {

        font-size: 22px;
    }
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:

    st.markdown("### ")

    col1, col2 = st.columns([1, 6])

    with col1:
        st.image(
            "https://axelarscan.io/logos/logo.png",
            width=18
        )

    with col2:
        st.markdown(
            'Powered by ''[Axelar](https://x.com/axelar)'
        )

    col1, col2 = st.columns([1, 6])

    with col1:
        st.image(
            "https://pbs.twimg.com/profile_images/2058533217540423680/JomSr3XY_400x400.jpg",
            width=18
        )

    with col2:
        st.markdown(
            'Built by ''[Eman Raz](https://x.com/0xeman_raz)'
        )

# =====================================================
# TITLE
# =====================================================
st.title("🚀 Interchain Analysis")

st.info(
    "All data is loaded from Axelar public API (no database required)."
)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():

    url = "https://api.axelarscan.io/api/interchainChart"

    r = requests.get(url, timeout=30)

    data = r.json()["data"]

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    return df


df = load_data()

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
        .dt.to_period("W")
        .apply(lambda r: r.start_time)
    )

elif timeframe == "month":

    df["period"] = (
        df["timestamp"]
        .dt.to_period("M")
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
# DAILY / WEEKLY STATS
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
    .dt.to_period("W")
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
# SPACE
# =====================================================
st.markdown("<br>", unsafe_allow_html=True)

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
# COLORS
# =====================================================
GMP_COLOR = "#ff7400"

TRANSFER_COLOR = "#00a1f7"

# =====================================================
# CHARTS ROW 1
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
        title=dict(text="Transactions Over Time")
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
        title=dict(text="Volume Over Time")
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# =====================================================
# DONUT CHARTS
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
        title="Transactions Share",
        color="Service",
        color_discrete_map={
            "GMP": GMP_COLOR,
            "Transfers": TRANSFER_COLOR
        }
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
        title="Volume Share",
        color="Service",
        color_discrete_map={
            "GMP": GMP_COLOR,
            "Transfers": TRANSFER_COLOR
        }
    )

    st.plotly_chart(
        fig4,
        use_container_width=True

    )
