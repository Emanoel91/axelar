import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Axelar Dashboard",
    page_icon="🚀",
    layout="wide"
)
# =========================
# --- Sidebar Footer Slightly Left-Aligned ---
# =========================

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
                <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.title("🚀 Interchain Analysis")

st.info("All data is loaded from Axelar public API (no database required).")

# =========================
# LOAD API DATA
# =========================
@st.cache_data
def load_data():
    url = "https://api.axelarscan.io/api/interchainChart"
    r = requests.get(url, timeout=30)
    data = r.json()["data"]

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

df = load_data()

# =========================
# FILTERS
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox("Timeframe", ["month", "week", "day"])

with col2:
    start_date = st.date_input("Start Date", pd.to_datetime("2022-01-01"))

with col3:
    end_date = st.date_input("End Date", pd.to_datetime("2027-01-01"))

df = df[
    (df["timestamp"] >= pd.to_datetime(start_date)) &
    (df["timestamp"] <= pd.to_datetime(end_date))
]

# =========================
# RESAMPLE
# =========================
if timeframe == "week":
    df["period"] = df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
elif timeframe == "month":
    df["period"] = df["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)
else:
    df["period"] = df["timestamp"]

grouped = df.groupby("period").sum(numeric_only=True).reset_index()

grouped["total_txs"] = grouped["gmp_num_txs"] + grouped["transfers_num_txs"]
grouped["total_volume"] = grouped["gmp_volume"] + grouped["transfers_volume"]

# =========================
# KPI CARDS
# =========================
card = """
<div style="padding:15px;border-radius:12px;background:#f5f5f5;text-align:center;">
<h3>{}</h3>
<h2>{}</h2>
</div>
"""

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(card.format("Total Transactions", f"{grouped['total_txs'].sum():,}"), unsafe_allow_html=True)

with col2:
    st.markdown(card.format("Total Volume", f"${grouped['total_volume'].sum():,.0f}"), unsafe_allow_html=True)

with col3:
    st.markdown(card.format("Avg Volume / Tx", f"${(grouped['total_volume'].sum()/max(grouped['total_txs'].sum(),1)):,.2f}"), unsafe_allow_html=True)

# =========================
# CHARTS SECTION
# =========================
st.subheader("📊 Transactions Over Time")

fig1 = go.Figure()
fig1.add_bar(x=grouped["period"], y=grouped["gmp_num_txs"], name="GMP")
fig1.add_bar(x=grouped["period"], y=grouped["transfers_num_txs"], name="Transfers")
fig1.update_layout(barmode="stack")

st.plotly_chart(fig1, use_container_width=True)

st.subheader("💰 Volume Over Time")

fig2 = go.Figure()
fig2.add_bar(x=grouped["period"], y=grouped["gmp_volume"], name="GMP")
fig2.add_bar(x=grouped["period"], y=grouped["transfers_volume"], name="Transfers")
fig2.update_layout(barmode="stack")

st.plotly_chart(fig2, use_container_width=True)

# =========================
# DONUT CHARTS
# =========================
st.subheader("📌 Share of Activity")

tx_df = pd.DataFrame({
    "Service": ["GMP", "Transfers"],
    "Value": [grouped["gmp_num_txs"].sum(), grouped["transfers_num_txs"].sum()]
})

fig3 = px.pie(tx_df, names="Service", values="Value", hole=0.5, title="Transactions Share")

st.plotly_chart(fig3, use_container_width=True)

vol_df = pd.DataFrame({
    "Service": ["GMP", "Transfers"],
    "Value": [grouped["gmp_volume"].sum(), grouped["transfers_volume"].sum()]
})

fig4 = px.pie(vol_df, names="Service", values="Value", hole=0.5, title="Volume Share")

st.plotly_chart(fig4, use_container_width=True)
