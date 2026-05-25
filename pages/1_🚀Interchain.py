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
# FILTERS
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox("Timeframe", ["month", "week", "day"])

with col2:
    start_date = st.date_input("Start Date", pd.to_datetime("2025-01-01"))

with col3:
    end_date = st.date_input("End Date", pd.to_datetime("2027-01-01"))

df = df[
    (df["timestamp"] >= pd.to_datetime(start_date)) &
    (df["timestamp"] <= pd.to_datetime(end_date))
]

# =====================================================
# GROUPING
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
daily = df.copy()
daily["day"] = daily["timestamp"].dt.date
d = daily.groupby("day").sum(numeric_only=True)

weekly = df.copy()
weekly["week"] = weekly["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
w = weekly.groupby("week").sum(numeric_only=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Avg Daily Volume", f"${(d['gmp_volume']+d['transfers_volume']).mean():,.0f}")

with col2:
    st.metric("Avg Weekly Volume", f"${(w['gmp_volume']+w['transfers_volume']).mean():,.0f}")

with col3:
    st.metric("Avg Daily Transactions", f"{(d['gmp_num_txs']+d['transfers_num_txs']).mean():,.0f}")

with col4:
    st.metric("Avg Weekly Transactions", f"{(w['gmp_num_txs']+w['transfers_num_txs']).mean():,.0f}")

# =====================================================
# KPI ROW 3 (FIXED EXACTLY AS REQUESTED)
# =====================================================

def pct_change(series):
    if len(series) < 2:
        return 0
    return ((series.iloc[-1] - series.iloc[-2]) / max(series.iloc[-2], 1)) * 100

df_w = df_raw.copy()
df_w["week"] = df_w["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
w_group = df_w.groupby("week").sum(numeric_only=True)
w_group["tx"] = w_group["gmp_num_txs"] + w_group["transfers_num_txs"]
w_group["vol"] = w_group["gmp_volume"] + w_group["transfers_volume"]

df_m = df_raw.copy()
df_m["month"] = df_m["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)
m_group = df_m.groupby("month").sum(numeric_only=True)
m_group["tx"] = m_group["gmp_num_txs"] + m_group["transfers_num_txs"]
m_group["vol"] = m_group["gmp_volume"] + m_group["transfers_volume"]

weekly_vol_change = pct_change(w_group["vol"])
weekly_tx_change = pct_change(w_group["tx"])
monthly_vol_change = pct_change(m_group["vol"])
monthly_tx_change = pct_change(m_group["tx"])

def render_kpi(title, pct, raw_value):
    color = "green" if raw_value >= 0 else "red"
    arrow = "⬆" if raw_value >= 0 else "⬇"

    st.markdown(f"""
    <div style="padding:12px;border-radius:12px;background:#111;">
        <div style="color:#aaa;font-size:14px;">{title}</div>
        <div style="color:white;font-size:22px;font-weight:600;">
            {pct:.2f}%
        </div>
        <div style="color:{color};font-size:14px;">
            {arrow} {raw_value:.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_kpi("Weekly Volume % Change", weekly_vol_change, weekly_vol_change)

with col2:
    render_kpi("Weekly Tx % Change", weekly_tx_change, weekly_tx_change)

with col3:
    render_kpi("Monthly Volume % Change", monthly_vol_change, monthly_vol_change)

with col4:
    render_kpi("Monthly Tx % Change", monthly_tx_change, monthly_tx_change)

# =====================================================
# CHARTS (UNCHANGED)
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
