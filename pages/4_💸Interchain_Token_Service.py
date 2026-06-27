import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Interchain Token Service",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>

.block-container{
    padding-top:2rem;
    padding-bottom:2rem;
}

[data-testid="metric-container"]{
    background:linear-gradient(145deg,#1c1c1c,#111111);
    border:1px solid rgba(255,255,255,0.05);
    padding:20px;
    border-radius:18px;
    box-shadow:0 4px 15px rgba(0,0,0,0.25);
    transition:0.25s ease;
}

[data-testid="metric-container"]:hover{
    transform:translateY(-4px);
    border:1px solid rgba(0,255,100,.35);
}

[data-testid="metric-container"] label{
    color:#9f9f9f !important;
    font-size:15px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"]{
    color:white;
    font-size:32px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# API URLs
# =====================================================

ITS_HUB_URL = (
    "https://api.axelarscan.io/gmp/GMPChart?"
    "contractAddress=axelar1aqcj54lzz0rk22gvqgcn8fr5tx4rzwdv5wv5j9dmnacgefvd7wzsy2j2mr"
)

ITS_SERVICE_URL = (
    "https://api.axelarscan.io/gmp/GMPChart?"
    "contractAddress=0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C"
)

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=3600)
def load_data():

    def load_contract(url, contract_name):

        r = requests.get(url, timeout=30)
        r.raise_for_status()

        data = r.json()["data"]

        df = pd.DataFrame(data)

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms"
        )

        df = df[
            [
                "timestamp",
                "volume",
                "num_txs"
            ]
        ]

        df["contract"] = contract_name

        return df

    hub = load_contract(
        ITS_HUB_URL,
        "Axelar ITS Hub"
    )

    its = load_contract(
        ITS_SERVICE_URL,
        "Interchain Token Service"
    )

    df = pd.concat(
        [
            hub,
            its
        ],
        ignore_index=True
    )

    return df


df = load_data()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.markdown(
    """
<style>

.sidebar-footer{
position:fixed;
bottom:20px;
width:250px;
font-size:13px;
color:gray;
margin-left:5px;
text-align:left;
}

.sidebar-footer img{
width:16px;
height:16px;
vertical-align:middle;
border-radius:50%;
margin-right:5px;
}

.sidebar-footer a{
color:gray;
text-decoration:none;
}

</style>

<div class="sidebar-footer">

<div>

<a href="https://x.com/axelar" target="_blank">

<img src="https://img.cryptorank.io/coins/axelar1663924228506.png">

Powered by Axelar

</a>

</div>

<div style="margin-top:5px;">

<a href="https://x.com/0xeman_raz" target="_blank">

<img src="https://pbs.twimg.com/profile_images/2060406047391559681/sA9zPNKM_400x400.jpg">

Built by Eman Raz

</a>

</div>

</div>
""",
unsafe_allow_html=True
)

# =====================================================
# TITLE
# =====================================================

st.title("🌉 Interchain Token Service")

st.info(
    "All data is loaded directly from Axelar public APIs."
)

# =====================================================
# FILTERS
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:

    timeframe = st.selectbox(
        "Timeframe",
        [
            "Month",
            "Week",
            "Day"
        ]
    )

with col2:

    start_date = st.date_input(
        "Start Date",
        df["timestamp"].min().date()
    )

with col3:

    end_date = st.date_input(
        "End Date",
        df["timestamp"].max().date()
    )

# =====================================================
# FILTER DATA
# =====================================================

df = df[
    (
        df["timestamp"] >=
        pd.to_datetime(start_date)
    )
    &
    (
        df["timestamp"] <=
        pd.to_datetime(end_date)
    )
].copy()

# =====================================================
# CREATE PERIOD
# =====================================================

if timeframe == "Day":

    df["period"] = df["timestamp"]

elif timeframe == "Week":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("W")
        .apply(lambda r: r.start_time)
    )

else:

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("M")
        .apply(lambda r: r.start_time)
    )

# =====================================================
# COLOR MAP
# =====================================================

COLOR_MAP = {
    "Interchain Token Service": "#00C853",
    "Axelar ITS Hub": "#3F51B5"
}

# =====================================================
# KPI CALCULATIONS
# =====================================================

total_volume = df["volume"].sum()

total_transactions = int(df["num_txs"].sum())

avg_volume_per_tx = (
    total_volume /
    max(total_transactions, 1)
)

# =====================================================
# KPI ROW
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Total Volume",
        f"${total_volume:,.2f}"
    )

with col2:

    st.metric(
        "Total Transactions",
        f"{total_transactions:,}"
    )

with col3:

    st.metric(
        "Average Volume per Transaction",
        f"${avg_volume_per_tx:,.2f}"
    )

# =====================================================
# TIME SERIES DATA
# =====================================================

time_contract = (
    df.groupby(
        [
            "period",
            "contract"
        ]
    )
    .agg(
        volume=("volume", "sum"),
        num_txs=("num_txs", "sum")
    )
    .reset_index()
)

# =====================================================
# ROW 2
# Transactions by Contract Over Time
# =====================================================

left, right = st.columns(2)

with left:

    fig = go.Figure()

    for contract in [
        "Interchain Token Service",
        "Axelar ITS Hub"
    ]:

        temp = time_contract[
            time_contract["contract"] == contract
        ]

        fig.add_trace(

            go.Bar(

                x=temp["period"],
                y=temp["num_txs"],

                name=contract,

                marker_color=COLOR_MAP[contract],

                hovertemplate=
                "<b>%{fullData.name}</b><br>" +
                "Date: %{x}<br>" +
                "Transactions: %{y:,}<extra></extra>"

            )

        )

    fig.update_layout(

        title="Transactions by Contract Over Time",

        barmode="stack",

        xaxis_title="",

        yaxis_title="Transactions",

        legend_title="Contract",

        template="plotly_dark",

        height=500

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# Volume by Contract Over Time
# =====================================================

with right:

    fig = go.Figure()

    for contract in [
        "Interchain Token Service",
        "Axelar ITS Hub"
    ]:

        temp = time_contract[
            time_contract["contract"] == contract
        ]

        fig.add_trace(

            go.Bar(

                x=temp["period"],

                y=temp["volume"],

                name=contract,

                marker_color=COLOR_MAP[contract],

                hovertemplate=
                "<b>%{fullData.name}</b><br>" +
                "Date: %{x}<br>" +
                "Volume: $%{y:,.2f}<extra></extra>"

            )

        )

    fig.update_layout(

        title="Volume by Contract Over Time",

        barmode="stack",

        xaxis_title="",

        yaxis_title="Volume ($)",

        legend_title="Contract",

        template="plotly_dark",

        height=500

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# CONTRACT SUMMARY
# =====================================================

contract_summary = (
    df.groupby("contract")
    .agg(
        volume=("volume", "sum"),
        num_txs=("num_txs", "sum")
    )
    .reset_index()
)

# =====================================================
# ROW 3
# DONUT CHARTS
# =====================================================

left, right = st.columns(2)

# =====================================================
# DONUT - VOLUME SHARE
# =====================================================

with left:

    fig = go.Figure()

    fig.add_trace(

        go.Pie(

            labels=contract_summary["contract"],

            values=contract_summary["volume"],

            hole=0.65,

            marker=dict(

                colors=[
                    COLOR_MAP[c]
                    for c in contract_summary["contract"]
                ]

            ),

            textinfo="percent",

            hovertemplate=
            "<b>%{label}</b><br>" +
            "Volume: $%{value:,.2f}<br>" +
            "Share: %{percent}<extra></extra>"

        )

    )

    fig.update_layout(

        title="Volume Share by Contract",

        template="plotly_dark",

        height=500,

        showlegend=True

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# DONUT - TRANSACTION SHARE
# =====================================================

with right:

    fig = go.Figure()

    fig.add_trace(

        go.Pie(

            labels=contract_summary["contract"],

            values=contract_summary["num_txs"],

            hole=0.65,

            marker=dict(

                colors=[
                    COLOR_MAP[c]
                    for c in contract_summary["contract"]
                ]

            ),

            textinfo="percent",

            hovertemplate=
            "<b>%{label}</b><br>" +
            "Transactions: %{value:,}<br>" +
            "Share: %{percent}<extra></extra>"

        )

    )

    fig.update_layout(

        title="Transaction Share by Contract",

        template="plotly_dark",

        height=500,

        showlegend=True

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# PREPARE DATA FOR LAST ROW
# =====================================================

total_time = (
    df.groupby("period")
    .agg(
        volume=("volume", "sum"),
        num_txs=("num_txs", "sum")
    )
    .reset_index()
)

total_time = total_time.sort_values("period")

total_time["avg_volume_per_tx"] = (
    total_time["volume"] /
    total_time["num_txs"].replace(0, 1)
)

# =====================================================
# ROW 4
# =====================================================

left, right = st.columns(2)

# =====================================================
# Volume & Transactions Over Time
# =====================================================

with left:

    fig = go.Figure()

    # -------------------------------
    # BAR : Volume
    # -------------------------------

    fig.add_trace(

        go.Bar(

            x=total_time["period"],

            y=total_time["volume"],

            name="Volume",

            marker_color="#00C853",

            hovertemplate=
            "<b>Date:</b> %{x}<br>"
            "<b>Volume:</b> $%{y:,.2f}"
            "<extra></extra>"

        )

    )

    # -------------------------------
    # LINE : Transactions
    # -------------------------------

    fig.add_trace(

        go.Scatter(

            x=total_time["period"],

            y=total_time["num_txs"],

            mode="lines+markers",

            name="Transactions",

            line=dict(
                color="#3F51B5",
                width=3
            ),

            marker=dict(
                size=7
            ),

            yaxis="y2",

            hovertemplate=
            "<b>Date:</b> %{x}<br>"
            "<b>Transactions:</b> %{y:,}"
            "<extra></extra>"

        )

    )

    fig.update_layout(

        title="Volume & Transactions Over Time",

        template="plotly_dark",

        height=520,

        hovermode="x unified",

        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),

        xaxis=dict(
            title=""
        ),

        yaxis=dict(
            title="Volume ($)",
            showgrid=True,
            zeroline=False
        ),

        yaxis2=dict(
            title="Transactions",
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False
        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# Average Volume per Transaction
# =====================================================

with right:

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=total_time["period"],

            y=total_time["avg_volume_per_tx"],

            mode="lines+markers",

            name="Average Volume",

            line=dict(
                color="#00C853",
                width=3
            ),

            marker=dict(
                size=7
            ),

            hovertemplate=
            "<b>Date:</b> %{x}<br>"
            "<b>Average:</b> $%{y:,.2f}"
            "<extra></extra>"

        )

    )

    fig.update_layout(

        title="Average Volume per Transaction",

        template="plotly_dark",

        height=520,

        hovermode="x unified",

        showlegend=False,

        xaxis=dict(
            title=""
        ),

        yaxis=dict(
            title="Average Volume ($)",
            zeroline=False
        )

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ===================================================================== Part 2 ==============================================================================================
# =====================================================
# GLOBAL KPI (NOT AFFECTED BY FILTERS)
# =====================================================

st.info(
    "⚠️ These KPIs are calculated using the complete historical dataset from both Axelar ITS APIs and are NOT affected by the selected Start Date, End Date, or Timeframe."
)

# ==========================================================
# API URLs
# ==========================================================

URLS = [
    "https://api.axelarscan.io/gmp/GMPChart?contractAddress=axelar1aqcj54lzz0rk22gvqgcn8fr5tx4rzwdv5wv5j9dmnacgefvd7wzsy2j2mr",
    "https://api.axelarscan.io/gmp/GMPChart?contractAddress=0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C"
]


# ==========================================================
# Load Data
# ==========================================================

@st.cache_data(ttl=3600)
def load_data():

    dfs = []

    for url in URLS:

        response = requests.get(url)
        response.raise_for_status()

        data = response.json()["data"]

        df = pd.DataFrame(data)

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        dfs.append(df)

    # Merge two contracts
    df = pd.concat(dfs)

    df = (
        df.groupby("timestamp", as_index=False)
        .agg(
            volume=("volume", "sum"),
            num_txs=("num_txs", "sum"),
        )
        .sort_values("timestamp")
    )

    # ------------------------------------------------------
    # Fill Missing Dates
    # ------------------------------------------------------

    df = (
        df.set_index("timestamp")
          .resample("D")
          .sum()
          .fillna(0)
          .reset_index()
    )

    return df


df = load_data()

# ==========================================================
# Historical KPIs
# ==========================================================

ath_volume_row = df.loc[df["volume"].idxmax()]
ath_volume = ath_volume_row["volume"]
ath_volume_date = ath_volume_row["timestamp"].strftime("%Y-%m-%d")

ath_tx_row = df.loc[df["num_txs"].idxmax()]
ath_tx = int(ath_tx_row["num_txs"])
ath_tx_date = ath_tx_row["timestamp"].strftime("%Y-%m-%d")


# ==========================================================
# Average (Last 30 Days)
# ==========================================================

avg_volume = df["volume"].tail(30).mean()
avg_tx = df["num_txs"].tail(30).mean()


# ==========================================================
# Helper Functions
# ==========================================================

def current_period(series, days):
    return series.tail(days).sum()


def previous_period(series, days):
    return series.iloc[-2 * days:-days].sum()


def pct_change(current, previous):

    if previous == 0:
        return None

    return ((current - previous) / previous) * 100


def delta_string(delta):

    if delta is None:
        return "N/A"

    return f"{delta:+.2f}%"


# ==========================================================
# Recent Activity
# ==========================================================

last7_volume = current_period(df["volume"], 7)
prev7_volume = previous_period(df["volume"], 7)

last30_volume = current_period(df["volume"], 30)
prev30_volume = previous_period(df["volume"], 30)

last7_tx = current_period(df["num_txs"], 7)
prev7_tx = previous_period(df["num_txs"], 7)

last30_tx = current_period(df["num_txs"], 30)
prev30_tx = previous_period(df["num_txs"], 30)


vol7_delta = pct_change(last7_volume, prev7_volume)
vol30_delta = pct_change(last30_volume, prev30_volume)

tx7_delta = pct_change(last7_tx, prev7_tx)
tx30_delta = pct_change(last30_tx, prev30_tx)

# ==========================================================
# Row 1
# ==========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "ATH Volume",
        f"${ath_volume:,.2f}",
        ath_volume_date,
    )

with col2:
    st.metric(
        "ATH Transactions",
        f"{ath_tx:,}",
        ath_tx_date,
    )

with col3:
    st.metric(
        "Avg Daily Volume (30D)",
        f"${avg_volume:,.2f}",
    )

with col4:
    st.metric(
        "Avg Daily Transactions (30D)",
        f"{avg_tx:,.0f}",
    )


# ==========================================================
# Row 2
# ==========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "7D Volume",
        f"${last7_volume:,.2f}",
        delta_string(vol7_delta),
    )

with col2:
    st.metric(
        "30D Volume",
        f"${last30_volume:,.2f}",
        delta_string(vol30_delta),
    )

with col3:
    st.metric(
        "7D Transactions",
        f"{last7_tx:,}",
        delta_string(tx7_delta),
    )

with col4:
    st.metric(
        "30D Transactions",
        f"{last30_tx:,}",
        delta_string(tx30_delta),
    )

# =========================================================== Part 3: User Analysis ====================================================================================
import numpy as np
from datetime import datetime, date

# ==========================================================
# Section Title
# ==========================================================
st.title("Axelar Interchain Token Service - Top Users")

# ==========================================================
# Date Filter
# ==========================================================

st.markdown("### Date Filter")

col1, col2, col3 = st.columns([1, 1, 4])

default_start = date(2023, 12, 18)
default_end = date.today()

with col1:
    start_date = st.date_input(
        "From",
        value=default_start,
        min_value=default_start,
        max_value=default_end,
    )

with col2:
    end_date = st.date_input(
        "To",
        value=default_end,
        min_value=default_start,
        max_value=default_end,
    )

if start_date > end_date:
    st.error("Start date must be before End date.")
    st.stop()

from_time = int(
    datetime.combine(start_date, datetime.min.time()).timestamp()
)

to_time = int(
    datetime.combine(end_date, datetime.max.time()).timestamp()
)

st.markdown("---")
# ==========================================================
# API URLs
# ==========================================================

BASE_URL = "https://api.axelarscan.io/gmp/GMPTopUsers"

CONTRACT_1 = "axelar1aqcj54lzz0rk22gvqgcn8fr5tx4rzwdv5wv5j9dmnacgefvd7wzsy2j2mr"
CONTRACT_2 = "0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C"

# ==========================================================
# Load Data
# ==========================================================

@st.cache_data(ttl=600)
def load_data(from_time, to_time):

    urls = [
        f"{BASE_URL}?contractAddress={CONTRACT_1}&fromTime={from_time}&toTime={to_time}",
        f"{BASE_URL}?contractAddress={CONTRACT_2}&fromTime={from_time}&toTime={to_time}"
    ]

    data = []

    for url in urls:

        try:

            response = requests.get(url, timeout=30)

            if response.status_code == 200:

                js = response.json()

                if "data" in js:
                    data.extend(js["data"])

        except Exception:
            pass

    if len(data) == 0:
        return pd.DataFrame(
            columns=["key", "volume", "num_txs"]
        )

    df = pd.DataFrame(data)

    df["volume"] = pd.to_numeric(df["volume"])
    df["num_txs"] = pd.to_numeric(df["num_txs"])

    # Merge duplicate addresses
    df = (
        df.groupby("key", as_index=False)
        .agg(
            volume=("volume", "sum"),
            num_txs=("num_txs", "sum")
        )
    )

    return df


df = load_data(from_time, to_time)

if df.empty:
    st.warning("No data found.")
    st.stop()

# ==========================================================
# Rankings
# ==========================================================

df["Volume Rank"] = (
    df["volume"]
    .rank(method="min", ascending=False)
    .astype(int)
)

df["Tx Rank"] = (
    df["num_txs"]
    .rank(method="min", ascending=False)
    .astype(int)
)

# ==========================================================
# Volume Groups
# ==========================================================

volume_bins = [
    0,
    10,
    100,
    1_000,
    10_000,
    100_000,
    1_000_000,
    np.inf
]

volume_labels = [
    "<10$",
    "10$-100$",
    "100$-1K$",
    "1K$-10K$",
    "10K$-100K$",
    "100K$-1M$",
    ">1M$"
]

df["Volume Group"] = pd.cut(
    df["volume"],
    bins=volume_bins,
    labels=volume_labels,
    include_lowest=True
)

volume_count = (
    df["Volume Group"]
    .value_counts()
    .sort_index()
)

# ==========================================================
# Transaction Groups
# ==========================================================

tx_bins = [
    0,
    1,
    2,
    5,
    10,
    50,
    100,
    np.inf
]

tx_labels = [
    "1",
    "2",
    "3-5",
    "6-10",
    "11-50",
    "51-100",
    ">100"
]

df["Tx Group"] = pd.cut(
    df["num_txs"],
    bins=tx_bins,
    labels=tx_labels,
    include_lowest=True
)

tx_count = (
    df["Tx Group"]
    .value_counts()
    .sort_index()
)

# ==========================================================
# Top 10 Tables
# ==========================================================

top_volume = (
    df.sort_values(
        "volume",
        ascending=False
    )
    .head(10)
)

top_tx = (
    df.sort_values(
        "num_txs",
        ascending=False
    )
    .head(10)
)

# ==========================================================
# KPIs
# ==========================================================

unique_addresses = len(df)

avg_volume = df["volume"].mean()

avg_transactions = df["num_txs"].mean()

total_volume = df["volume"].sum()

total_transactions = df["num_txs"].sum()

# ==========================================================
# KPI Section
# ==========================================================

st.markdown("---")
st.subheader("Network Statistics")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Unique Addresses",
    f"{unique_addresses:,}"
)

c2.metric(
    "Avg Volume per Address",
    f"${avg_volume:,.2f}"
)

c3.metric(
    "Avg Transactions per Address",
    f"{avg_transactions:,.2f}"
)

# ==========================================================
# Volume Distribution
# ==========================================================

st.markdown("---")
st.subheader("Users by Transfer Volume")

col1, col2 = st.columns(2)

fig_volume_bar = px.bar(
    x=volume_count.index,
    y=volume_count.values,
    text=volume_count.values,
    color=volume_count.values,
    color_continuous_scale="Oranges"
)

fig_volume_bar.update_traces(
    textposition="outside"
)

fig_volume_bar.update_layout(
    showlegend=False,
    coloraxis_showscale=False,
    xaxis_title="Transfer Volume",
    yaxis_title="Number of Users",
    height=500
)

col1.plotly_chart(
    fig_volume_bar,
    use_container_width=True
)

fig_volume_pie = px.pie(
    names=volume_count.index,
    values=volume_count.values,
    hole=0.45,
    color_discrete_sequence=px.colors.sequential.Oranges_r
)

fig_volume_pie.update_traces(
    textposition="inside",
    textinfo="percent+label"
)

fig_volume_pie.update_layout(
    height=500
)

col2.plotly_chart(
    fig_volume_pie,
    use_container_width=True
)

# ==========================================================
# Transaction Distribution
# ==========================================================

st.markdown("---")
st.subheader("Users by Number of Transactions")

col1, col2 = st.columns(2)

fig_tx_bar = px.bar(
    x=tx_count.index,
    y=tx_count.values,
    text=tx_count.values,
    color=tx_count.values,
    color_continuous_scale="Blues"
)

fig_tx_bar.update_traces(
    textposition="outside"
)

fig_tx_bar.update_layout(
    showlegend=False,
    coloraxis_showscale=False,
    xaxis_title="Transactions",
    yaxis_title="Number of Users",
    height=500
)

col1.plotly_chart(
    fig_tx_bar,
    use_container_width=True
)

fig_tx_pie = px.pie(
    names=tx_count.index,
    values=tx_count.values,
    hole=0.45,
    color_discrete_sequence=px.colors.sequential.Blues_r
)

fig_tx_pie.update_traces(
    textposition="inside",
    textinfo="percent+label"
)

fig_tx_pie.update_layout(
    height=500
)

col2.plotly_chart(
    fig_tx_pie,
    use_container_width=True
)

# ==========================================================
# Top 10 Addresses
# ==========================================================

st.markdown("---")
st.subheader("Top 10 Addresses")

col1, col2 = st.columns(2)

# ----------------------------------------------------------
# Top 10 by Volume
# ----------------------------------------------------------

with col1:

    st.markdown("#### Top 10 by Volume")

    volume_table = top_volume.copy()

    volume_table.insert(
        0,
        "Rank",
        range(1, len(volume_table) + 1)
    )

    volume_table["Volume ($)"] = volume_table["volume"].map(
        lambda x: f"${x:,.2f}"
    )

    volume_table = volume_table.rename(
        columns={
            "key": "Address"
        }
    )

    st.dataframe(
        volume_table[
            [
                "Rank",
                "Address",
                "Volume ($)",
                "num_txs"
            ]
        ].rename(
            columns={
                "num_txs": "Transactions"
            }
        ),
        hide_index=True,
        use_container_width=True
    )

# ----------------------------------------------------------
# Top 10 by Transactions
# ----------------------------------------------------------

with col2:

    st.markdown("#### Top 10 by Transactions")

    tx_table = top_tx.copy()

    tx_table.insert(
        0,
        "Rank",
        range(1, len(tx_table) + 1)
    )

    tx_table["Volume ($)"] = tx_table["volume"].map(
        lambda x: f"${x:,.2f}"
    )

    tx_table = tx_table.rename(
        columns={
            "key": "Address",
            "num_txs": "Transactions"
        }
    )

    st.dataframe(
        tx_table[
            [
                "Rank",
                "Address",
                "Transactions",
                "Volume ($)"
            ]
        ],
        hide_index=True,
        use_container_width=True
    )

# ==========================================================
# Address Lookup
# ==========================================================

st.markdown("---")
st.subheader("Address Lookup")

with st.container(border=True):

    address = st.text_input(
        "Enter Wallet Address",
        placeholder="0x..."
    )

    if address:

        address = address.strip().lower()

        result = df[
            df["key"].str.lower() == address
        ]

        if result.empty:

            st.error("Address not found in selected time range.")

        else:

            r = result.iloc[0]

            volume_share = (
                r["volume"] / total_volume * 100
                if total_volume > 0 else 0
            )

            tx_share = (
                r["num_txs"] / total_transactions * 100
                if total_transactions > 0 else 0
            )

            st.success("Address Found")

            st.code(r["key"], language=None)

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Transfer Volume",
                f"${r['volume']:,.2f}"
            )

            c2.metric(
                "Transactions",
                f"{int(r['num_txs']):,}"
            )

            c3.metric(
                "Volume Rank",
                f"#{int(r['Volume Rank'])}"
            )

            c4.metric(
                "Transaction Rank",
                f"#{int(r['Tx Rank'])}"
            )

            st.markdown("### Address Statistics")

            cc1, cc2 = st.columns(2)

            cc1.metric(
                "Share of Total Volume",
                f"{volume_share:.4f}%"
            )

            cc2.metric(
                "Share of Total Transactions",
                f"{tx_share:.4f}%"
            )

# ==========================================================
# Footer
# ==========================================================

st.markdown("---")

st.caption(
    f"""
    Showing data from **{start_date.strftime('%Y-%m-%d')}**
    to **{end_date.strftime('%Y-%m-%d')}**
    """
)
