import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# --- Page Config -------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelar Master Dashboard",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Sidebar Footer ----------------------------------------------------------------------------------
st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px;
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
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png">
                Powered by Axelar
            </a>
        </div>

        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Title --------------------------------------------------------------------------------------------
st.title("🚀 GMP & Token Transfers")

st.info("📊 Charts initially display data for a default time range.")
st.info("⏳ On-chain data retrieval may take a few moments.")

# --- Time Frame Selection -----------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox(
        "Select Time Frame",
        ["month", "week", "day"]
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        value=pd.to_datetime("2022-01-01")
    )

with col3:
    end_date = st.date_input(
        "End Date",
        value=pd.to_datetime("2025-09-30")
    )

# --- Header -------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color:#ff7f27; padding:1px; border-radius:10px;">
        <h2 style="color:#000000; text-align:center;">
            Axelar Cross-Chain Transfers Overview
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# --- Load API Data ------------------------------------------------------------------------------------
@st.cache_data
def load_data():
    url = "https://api.axelarscan.io/api/interchainChart"

    response = requests.get(url)

    json_data = response.json()

    df = pd.DataFrame(json_data["data"])

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    return df

df = load_data()

# --- Filter Date Range --------------------------------------------------------------------------------
df = df[
    (df["timestamp"] >= pd.to_datetime(start_date)) &
    (df["timestamp"] <= pd.to_datetime(end_date))
]

# --- Resample -----------------------------------------------------------------------------------------
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

# --- Group Data ---------------------------------------------------------------------------------------
grouped = df.groupby("period").agg({
    "gmp_num_txs": "sum",
    "gmp_volume": "sum",
    "transfers_num_txs": "sum",
    "transfers_volume": "sum"
}).reset_index()

grouped["total_txs"] = (
    grouped["gmp_num_txs"] +
    grouped["transfers_num_txs"]
)

grouped["total_volume"] = (
    grouped["gmp_volume"] +
    grouped["transfers_volume"]
)

# --- KPI Cards ----------------------------------------------------------------------------------------
card_style = """
<div style="
    background-color: #f9f9f9;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
">
    <h4 style="margin:0; font-size:20px; color:#555;">
        {label}
    </h4>

    <p style="
        margin:5px 0 0;
        font-size:20px;
        font-weight:bold;
        color:#000;
    ">
        {value}
    </p>
</div>
"""

total_num_txs = (
    grouped["gmp_num_txs"].sum() +
    grouped["transfers_num_txs"].sum()
)

total_volume = (
    grouped["gmp_volume"].sum() +
    grouped["transfers_volume"].sum()
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        card_style.format(
            label="🚀 Number of Transfers",
            value=f"{total_num_txs:,} Txns"
        ),
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        card_style.format(
            label="💸 Volume of Transfers",
            value=f"${total_volume:,.0f}"
        ),
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- Header -------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color:#ff7f27; padding:1px; border-radius:10px;">
        <h2 style="color:#000000; text-align:center;">
            Analysis of Cross-Chain Transfers By Service
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Transactions Count Chart -------------------------------------------------------------------------
fig1 = go.Figure()

fig1.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["gmp_num_txs"],
        name="GMP",
        marker_color="#ff7400"
    )
)

fig1.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["transfers_num_txs"],
        name="Token Transfers",
        marker_color="#00a1f7"
    )
)

fig1.add_trace(
    go.Scatter(
        x=grouped["period"],
        y=grouped["total_txs"],
        name="Total",
        mode="lines",
        marker_color="black"
    )
)

fig1.update_layout(
    barmode="stack",
    title="Number of Transfers by Service Over Time",
    yaxis=dict(title="Txns count"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5
    )
)

# --- Volume Chart -------------------------------------------------------------------------------------
fig2 = go.Figure()

fig2.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["gmp_volume"],
        name="GMP",
        marker_color="#ff7400"
    )
)

fig2.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["transfers_volume"],
        name="Token Transfers",
        marker_color="#00a1f7"
    )
)

fig2.add_trace(
    go.Scatter(
        x=grouped["period"],
        y=grouped["total_volume"],
        name="Total",
        mode="lines",
        marker_color="black"
    )
)

fig2.update_layout(
    barmode="stack",
    title="Volume of Transfers by Service Over Time",
    yaxis=dict(title="$USD"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5
    )
)

# --- Display Charts -----------------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.plotly_chart(fig2, use_container_width=True)

# --- Normalized Transactions --------------------------------------------------------------------------
df_norm_tx = grouped.copy()

df_norm_tx["gmp_norm"] = (
    df_norm_tx["gmp_num_txs"] /
    df_norm_tx["total_txs"]
)

df_norm_tx["transfers_norm"] = (
    df_norm_tx["transfers_num_txs"] /
    df_norm_tx["total_txs"]
)

fig3 = go.Figure()

fig3.add_trace(
    go.Bar(
        x=df_norm_tx["period"],
        y=df_norm_tx["gmp_norm"],
        name="GMP",
        marker_color="#ff7400"
    )
)

fig3.add_trace(
    go.Bar(
        x=df_norm_tx["period"],
        y=df_norm_tx["transfers_norm"],
        name="Token Transfers",
        marker_color="#00a1f7"
    )
)

fig3.update_layout(
    barmode="stack",
    title="Normalized Transactions Over Time",
    yaxis_tickformat="%",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5
    )
)

# --- Normalized Volume --------------------------------------------------------------------------------
df_norm_vol = grouped.copy()

df_norm_vol["gmp_norm"] = (
    df_norm_vol["gmp_volume"] /
    df_norm_vol["total_volume"]
)

df_norm_vol["transfers_norm"] = (
    df_norm_vol["transfers_volume"] /
    df_norm_vol["total_volume"]
)

fig4 = go.Figure()

fig4.add_trace(
    go.Bar(
        x=df_norm_vol["period"],
        y=df_norm_vol["gmp_norm"],
        name="GMP",
        marker_color="#ff7400"
    )
)

fig4.add_trace(
    go.Bar(
        x=df_norm_vol["period"],
        y=df_norm_vol["transfers_norm"],
        name="Token Transfers",
        marker_color="#00a1f7"
    )
)

fig4.update_layout(
    barmode="stack",
    title="Normalized Volume Over Time",
    yaxis_tickformat="%",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5
    )
)

# --- Display Normalized Charts ------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.plotly_chart(fig4, use_container_width=True)

# --- Donut Charts -------------------------------------------------------------------------------------
total_gmp_tx = grouped["gmp_num_txs"].sum()
total_transfer_tx = grouped["transfers_num_txs"].sum()

tx_df = pd.DataFrame({
    "Service": ["GMP", "Token Transfers"],
    "Count": [total_gmp_tx, total_transfer_tx]
})

donut_tx = px.pie(
    tx_df,
    names="Service",
    values="Count",
    hole=0.5,
    title="Total Transactions by Service",
    color="Service",
    color_discrete_map={
        "GMP": "#ff7400",
        "Token Transfers": "#00a1f7"
    }
)

donut_tx.update_traces(
    textinfo="label+percent",
    showlegend=False
)

# --- Volume Donut -------------------------------------------------------------------------------------
total_gmp_vol = grouped["gmp_volume"].sum()
total_transfer_vol = grouped["transfers_volume"].sum()

vol_df = pd.DataFrame({
    "Service": ["GMP", "Token Transfers"],
    "Volume": [total_gmp_vol, total_transfer_vol]
})

donut_vol = px.pie(
    vol_df,
    names="Service",
    values="Volume",
    hole=0.5,
    title="Total Volume by Service",
    color="Service",
    color_discrete_map={
        "GMP": "#ff7400",
        "Token Transfers": "#00a1f7"
    }
)

donut_vol.update_traces(
    textinfo="label+percent",
    showlegend=False
)

# --- Display Donuts -----------------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(donut_tx, use_container_width=True)

with col2:
    st.plotly_chart(donut_vol, use_container_width=True)
