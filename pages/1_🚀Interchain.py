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
# THEME TOGGLE (LIGHT / DARK)
# =========================
theme = st.sidebar.radio("Theme", ["Light", "Dark"])

if theme == "Dark":
    st.markdown("""
    <style>
        body, .stApp {
            background-color: #0e1117;
            color: white;
        }
        div[data-testid="stMetricValue"] {
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

# =========================
# SIDEBAR FOOTER
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
        margin-left: 5px;
        text-align: left;  
    }
    .sidebar-footer img {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        margin-right: 5px;
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

st.title("🚀 Axelar GMP & Token Transfers Dashboard")
st.info("Live data from Axelar API")

# =========================
# LOAD DATA
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
    timeframe = st.selectbox("Timeframe", ["day", "week", "month"])

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
# KPI CALC (CURRENT VS PREVIOUS)
# =========================
latest = grouped.tail(1)
prev = grouped.tail(2).head(1)

def calc_delta(curr, prev):
    if prev == 0:
        return 0
    return ((curr - prev) / prev) * 100

tx_curr = latest["total_txs"].values[0]
tx_prev = prev["total_txs"].values[0]

vol_curr = latest["total_volume"].values[0]
vol_prev = prev["total_volume"].values[0]

avg_curr = vol_curr / max(tx_curr, 1)
avg_prev = vol_prev / max(tx_prev, 1)

# =========================
# KPI CARDS
# =========================
def kpi_card(title, value, delta):
    color = "green" if delta >= 0 else "red"
    arrow = "▲" if delta >= 0 else "▼"
    return f"""
    <div style="padding:15px;border-radius:12px;background:#1c1f26;text-align:center;">
        <h4>{title}</h4>
        <h2>{value}</h2>
        <p style="color:{color};font-size:14px;">
            {arrow} {delta:.2f}%
        </p>
    </div>
    """

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(kpi_card(
        "Total Transactions",
        f"{tx_curr:,}",
        calc_delta(tx_curr, tx_prev)
    ), unsafe_allow_html=True)

with col2:
    st.markdown(kpi_card(
        "Total Volume",
        f"${vol_curr:,.0f}",
        calc_delta(vol_curr, vol_prev)
    ), unsafe_allow_html=True)

with col3:
    st.markdown(kpi_card(
        "Avg Volume / Tx",
        f"${avg_curr:,.2f}",
        calc_delta(avg_curr, avg_prev)
    ), unsafe_allow_html=True)

# =========================
# COLORS
# =========================
GMP_COLOR = "#ff7400"
TRANSFER_COLOR = "#00a1f7"

# =========================
# CHARTS ROW 1 (ANIMATED STYLE)
# =========================
col1, col2 = st.columns(2)

with col1:
    fig1 = go.Figure()
    fig1.add_bar(x=grouped["period"], y=grouped["gmp_num_txs"], name="GMP", marker_color=GMP_COLOR)
    fig1.add_bar(x=grouped["period"], y=grouped["transfers_num_txs"], name="Transfers", marker_color=TRANSFER_COLOR)

    fig1.update_layout(
        barmode="stack",
        title=dict(text="Transactions Over Time", x=0.5),
        transition_duration=500
    )

    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = go.Figure()
    fig2.add_bar(x=grouped["period"], y=grouped["gmp_volume"], name="GMP", marker_color=GMP_COLOR)
    fig2.add_bar(x=grouped["period"], y=grouped["transfers_volume"], name="Transfers", marker_color=TRANSFER_COLOR)

    fig2.update_layout(
        barmode="stack",
        title=dict(text="Volume Over Time", x=0.5),
        transition_duration=500
    )

    st.plotly_chart(fig2, use_container_width=True)

# =========================
# CHARTS ROW 2 (DONUTS)
# =========================
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

    st.plotly_chart(fig3, use_container_width=True)

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

    st.plotly_chart(fig4, use_container_width=True)
