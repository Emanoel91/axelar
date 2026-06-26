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
    border-radius:18px;
    padding:20px;
    border:1px solid rgba(255,255,255,0.05);
    box-shadow:0 4px 15px rgba(0,0,0,0.25);
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# API
# =====================================================

HUB_URL = "https://api.axelarscan.io/gmp/GMPChart?contracts=axelar1aqcj54lzz0rk22gvqgcn8fr5tx4rzwdv5wv5j9dmnacgefvd7wzsy2j2mr"

ITS_URL = "https://api.axelarscan.io/gmp/GMPChart?contracts=0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C"

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=3600)
def load_contract(url, name):

    r = requests.get(url, timeout=30)
    data = r.json()["data"]

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["contract"] = name

    return df


hub = load_contract(HUB_URL, "ITS Hub")
its = load_contract(ITS_URL, "Interchain Token Service")

df = pd.concat([hub, its], ignore_index=True)

# =====================================================
# TITLE
# =====================================================

st.title("🌉 Interchain Token Service")

st.info(
    "This dashboard visualizes Interchain Token Service activity using Axelar public APIs."
)

# =====================================================
# FILTERS
# =====================================================

c1, c2, c3 = st.columns(3)

with c1:

    timeframe = st.selectbox(
        "Timeframe",
        ["Day", "Week", "Month"]
    )

with c2:

    start_date = st.date_input(
        "Start Date",
        df.timestamp.min().date()
    )

with c3:

    end_date = st.date_input(
        "End Date",
        df.timestamp.max().date()
    )

df = df[
    (df.timestamp >= pd.to_datetime(start_date))
    &
    (df.timestamp <= pd.to_datetime(end_date))
]

# =====================================================
# PERIOD
# =====================================================

if timeframe == "Day":

    df["period"] = df["timestamp"]

elif timeframe == "Week":

    df["period"] = (
        df.timestamp.dt.to_period("W")
        .apply(lambda r: r.start_time)
    )

else:

    df["period"] = (
        df.timestamp.dt.to_period("M")
        .apply(lambda r: r.start_time)
    )

# =====================================================
# KPI
# =====================================================

total_volume = df.volume.sum()

total_txs = df.num_txs.sum()

avg_volume = total_volume / max(total_txs,1)

k1,k2,k3 = st.columns(3)

k1.metric(
    "Total Volume",
    f"${total_volume:,.2f}"
)

k2.metric(
    "Total Transactions",
    f"{int(total_txs):,}"
)

k3.metric(
    "Average Volume per Transaction",
    f"${avg_volume:,.2f}"
)

# =====================================================
# GROUP CONTRACT
# =====================================================

contract_df = (
    df.groupby("contract")
    .agg(
        volume=("volume","sum"),
        num_txs=("num_txs","sum")
    )
    .reset_index()
)

# =====================================================
# BAR CHARTS
# =====================================================

left,right = st.columns(2)

with left:

    fig = px.bar(
        contract_df,
        x="contract",
        y="num_txs",
        color="contract",
        barmode="group",
        title="Transactions by Contract"
    )

    fig.update_layout(showlegend=False)

    st.plotly_chart(fig,use_container_width=True)

with right:

    fig = px.bar(
        contract_df,
        x="contract",
        y="volume",
        color="contract",
        barmode="group",
        title="Volume by Contract"
    )

    fig.update_layout(showlegend=False)

    st.plotly_chart(fig,use_container_width=True)

# =====================================================
# DONUTS
# =====================================================

left,right = st.columns(2)

with left:

    fig = px.pie(
        contract_df,
        names="contract",
        values="volume",
        hole=.65,
        title="Volume Share"
    )

    st.plotly_chart(fig,use_container_width=True)

with right:

    fig = px.pie(
        contract_df,
        names="contract",
        values="num_txs",
        hole=.65,
        title="Transaction Share"
    )

    st.plotly_chart(fig,use_container_width=True)

# =====================================================
# TIME SERIES
# =====================================================

time_df = (
    df.groupby("period")
    .agg(
        volume=("volume","sum"),
        num_txs=("num_txs","sum")
    )
    .reset_index()
)

time_df["avg_volume"] = (
    time_df["volume"] /
    time_df["num_txs"].replace(0,1)
)

# =====================================================
# COMBO + LINE
# =====================================================

left,right = st.columns(2)

with left:

    fig = go.Figure()

    fig.add_bar(
        x=time_df.period,
        y=time_df.volume,
        name="Volume",
        yaxis="y1"
    )

    fig.add_trace(

        go.Scatter(
            x=time_df.period,
            y=time_df.num_txs,
            mode="lines+markers",
            name="Transactions",
            yaxis="y2"
        )

    )

    fig.update_layout(

        title="Volume & Transactions",

        yaxis=dict(
            title="Volume ($)"
        ),

        yaxis2=dict(
            title="Transactions",
            overlaying="y",
            side="right"
        ),

        legend=dict(
            orientation="h"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with right:

    fig = px.line(
        time_df,
        x="period",
        y="avg_volume",
        markers=True,
        title="Average Volume per Transaction"
    )

    fig.update_layout(
        yaxis_title="Average Volume ($)",
        xaxis_title=""
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# TABLE
# =====================================================

st.subheader("Aggregated Data")

table = time_df.copy()

table.columns = [
    "Period",
    "Volume",
    "Transactions",
    "Average Volume / Tx"
]

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True
)
