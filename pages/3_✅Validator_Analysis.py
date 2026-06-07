import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Validator Analysis",
    page_icon="🛡️",
    layout="wide"
)

# =====================================================
# TITLE + DESCRIPTION
# =====================================================

st.title("🛡️ Validator Analysis")

st.markdown(
    """
### What is Uptime?
Uptime represents how often a validator is actively included in consensus snapshots.
Higher uptime means better reliability, lower downtime risk, and stronger network contribution.
"""
)

st.info(
    "Data is sourced from Axelar validator uptime snapshots."
)

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=300)
def load_uptime():

    url = "https://api.axelarscan.io/validator/searchUptimes"

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    data = r.json().get("data", [])

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()]
    df = df[df["timestamp"] > 0]

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        errors="coerce"
    )

    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp")

    return df


df = load_uptime()

if df.empty:
    st.error("No data available.")
    st.stop()

# =====================================================
# FILTERS
# =====================================================

st.sidebar.header("Filters")

timeframe = st.sidebar.selectbox(
    "Timeframe",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
)

latest_time = df["timestamp"].max()

if timeframe == "Last 24 Hours":
    df = df[df["timestamp"] >= latest_time - pd.Timedelta(days=1)]

elif timeframe == "Last 7 Days":
    df = df[df["timestamp"] >= latest_time - pd.Timedelta(days=7)]

elif timeframe == "Last 30 Days":
    df = df[df["timestamp"] >= latest_time - pd.Timedelta(days=30)]

# =====================================================
# VALIDATOR STATS
# =====================================================

all_validators = sorted({v for lst in df["validators"] for v in lst})

total_snapshots = len(df)

records = []

for v in all_validators:

    appearances = df["validators"].apply(lambda x: v in x).sum()
    misses = total_snapshots - appearances

    uptime = (appearances / total_snapshots * 100) if total_snapshots else 0

    records.append({
        "validator": v,
        "appearances": appearances,
        "misses": misses,
        "uptime": uptime
    })

stats_df = pd.DataFrame(records)

# =====================================================
# METRICS
# =====================================================

active_df = df.copy()
active_df["active_count"] = active_df["validators"].apply(len)

avg_active = active_df["active_count"].mean()

best_uptime = stats_df["uptime"].max()
worst_uptime = stats_df["uptime"].min()
avg_uptime = stats_df["uptime"].mean()

# =====================================================
# KPI ROW (TOOLTIPS WITH ? HOVER)
# =====================================================

def kpi(label, tooltip):
    return f"{label} ℹ️"

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(kpi("Validators", "Unique validators observed in snapshots"), f"{len(stats_df):,}")

with col2:
    st.metric(kpi("Snapshots", "Number of block snapshots analyzed"), f"{total_snapshots:,}")

with col3:
    st.metric(kpi("Avg Active", "Average validators active per snapshot"), f"{avg_active:.1f}")

with col4:
    st.metric(kpi("Best Uptime", "Highest uptime among validators"), f"{best_uptime:.2f}%")

with col5:
    st.metric(kpi("Worst Uptime", "Lowest uptime among validators"), f"{worst_uptime:.2f}%")

with col6:
    st.metric(kpi("Average Uptime", "Average uptime across all validators"), f"{avg_uptime:.2f}%")

st.divider()

# =====================================================
# CHARTS ROW 1
# =====================================================

col1, col2 = st.columns(2)

with col1:

    fig = px.line(
        active_df,
        x="timestamp",
        y="active_count",
        title="Active Validators Over Time"
    )

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

with col2:

    fig = px.histogram(
        stats_df,
        x="uptime",
        nbins=25,
        title="Validator Uptime Distribution"
    )

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ROW 2 (UPDATED LAYOUT)
# =====================================================

col1, col2 = st.columns(2)

with col1:

    health_df = active_df.copy()

    max_active = health_df["active_count"].max()

    health_df["health_score"] = (
        health_df["active_count"] / max_active * 100
        if max_active else 0
    )

    fig = px.area(
        health_df,
        x="timestamp",
        y="health_score",
        title="Network Health Score (%)"
    )

    fig.update_layout(height=450)

    st.plotly_chart(fig, use_container_width=True)

with col2:

    top_miss = stats_df.sort_values("misses", ascending=False).head(20)

    fig = px.bar(
        top_miss,
        x="misses",
        y="validator",
        orientation="h",
        title="Top 20 Validators by Miss Count"
    )

    fig.update_layout(height=450)

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# RANKING TABLE
# =====================================================

st.subheader("Validator Ranking")

ranking = stats_df.sort_values("uptime", ascending=False).reset_index(drop=True)
ranking.index += 1

st.dataframe(ranking, use_container_width=True, height=600)
