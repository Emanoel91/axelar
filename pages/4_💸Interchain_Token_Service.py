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
            "Day",
            "Week",
            "Month"
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

        barmode="group",

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

        barmode="group",

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
