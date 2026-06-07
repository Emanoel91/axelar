import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Validator Analysis",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Validator Analysis")

st.info(
    "Validator uptime analysis based on Axelar uptime snapshots."
)

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=300)
def load_uptime():

    url = "https://api.axelarscan.io/validator/searchUptimes"

    r = requests.get(url, timeout=60)

    r.raise_for_status()

    data = r.json()["data"]

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    return df


df = load_uptime()

# =====================================================
# FILTERS
# =====================================================

col1, col2 = st.columns(2)

with col1:

    start_date = st.date_input(
        "Start Date",
        df["timestamp"].min().date()
    )

with col2:

    end_date = st.date_input(
        "End Date",
        df["timestamp"].max().date()
    )

df = df[
    (df["timestamp"] >= pd.to_datetime(start_date))
    &
    (df["timestamp"] <= pd.to_datetime(end_date))
].copy()

# =====================================================
# BUILD VALIDATOR STATS
# =====================================================

all_validators = sorted(
    {
        validator
        for validator_list in df["validators"]
        for validator in validator_list
    }
)

total_snapshots = len(df)

records = []

for validator in all_validators:

    appearances = (
        df["validators"]
        .apply(lambda x: validator in x)
        .sum()
    )

    misses = total_snapshots - appearances

    uptime = (
        appearances / total_snapshots * 100
        if total_snapshots > 0
        else 0
    )

    records.append(
        {
            "validator": validator,
            "appearances": appearances,
            "misses": misses,
            "uptime": round(uptime, 4)
        }
    )

stats_df = pd.DataFrame(records)

# =====================================================
# KPI ROW
# =====================================================

avg_active = (
    df["validators"]
    .apply(len)
    .mean()
)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "Validators",
        f"{len(stats_df):,}"
    )

with col2:
    st.metric(
        "Snapshots",
        f"{total_snapshots:,}"
    )

with col3:
    st.metric(
        "Avg Active",
        f"{avg_active:.1f}"
    )

with col4:
    st.metric(
        "Best Uptime",
        f"{stats_df['uptime'].max():.2f}%"
    )

with col5:
    st.metric(
        "Worst Uptime",
        f"{stats_df['uptime'].min():.2f}%"
    )

with col6:
    st.metric(
        "Average Uptime",
        f"{stats_df['uptime'].mean():.2f}%"
    )

st.divider()

# =====================================================
# ACTIVE VALIDATORS OVER TIME
# =====================================================

active_df = df.copy()

active_df["active_count"] = (
    active_df["validators"]
    .apply(len)
)

col1, col2 = st.columns(2)

with col1:

    fig = px.line(
        active_df,
        x="timestamp",
        y="active_count",
        title="Active Validators Over Time"
    )

    fig.update_layout(
        height=500
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    fig = px.histogram(
        stats_df,
        x="uptime",
        nbins=30,
        title="Validator Uptime Distribution"
    )

    fig.update_layout(
        height=500
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# TOP UPTIME / MISSES
# =====================================================

col1, col2 = st.columns(2)

with col1:

    top_uptime = (
        stats_df
        .sort_values(
            "uptime",
            ascending=False
        )
        .head(20)
    )

    fig = px.bar(
        top_uptime,
        x="uptime",
        y="validator",
        orientation="h",
        title="Top 20 Validators by Uptime"
    )

    fig.update_layout(
        height=650,
        yaxis={
            "categoryorder": "total ascending"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    top_misses = (
        stats_df
        .sort_values(
            "misses",
            ascending=False
        )
        .head(20)
    )

    fig = px.bar(
        top_misses,
        x="misses",
        y="validator",
        orientation="h",
        title="Top 20 Validators by Miss Count"
    )

    fig.update_layout(
        height=650,
        yaxis={
            "categoryorder": "total ascending"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# NETWORK HEALTH TREND
# =====================================================

st.subheader("Network Health Trend")

health_df = active_df.copy()

health_df["network_health"] = (
    health_df["active_count"]
    /
    health_df["active_count"].max()
    * 100
)

fig = px.area(
    health_df,
    x="timestamp",
    y="network_health",
    title="Network Health Score (%)"
)

fig.update_layout(
    height=450
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# VALIDATOR RANKING TABLE
# =====================================================

st.subheader("Validator Ranking")

ranking = (
    stats_df
    .sort_values(
        "uptime",
        ascending=False
    )
    .reset_index(drop=True)
)

ranking.index += 1

st.dataframe(
    ranking,
    use_container_width=True,
    height=500
)

# =====================================================
# VALIDATOR EXPLORER
# =====================================================

st.subheader("Validator Explorer")

selected_validator = st.selectbox(
    "Select Validator",
    ranking["validator"]
)

timeline = df[
    ["timestamp", "validators"]
].copy()

timeline["online"] = (
    timeline["validators"]
    .apply(
        lambda x:
        1 if selected_validator in x else 0
    )
)

fig = px.line(
    timeline,
    x="timestamp",
    y="online",
    title=f"{selected_validator} Presence Timeline"
)

fig.update_yaxes(
    tickvals=[0, 1],
    ticktext=["Offline", "Online"]
)

fig.update_layout(
    height=450
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# VALIDATOR DETAIL KPI
# =====================================================

selected_row = stats_df[
    stats_df["validator"]
    == selected_validator
].iloc[0]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Uptime %",
        f"{selected_row['uptime']:.2f}%"
    )

with col2:
    st.metric(
        "Appearances",
        f"{int(selected_row['appearances']):,}"
    )

with col3:
    st.metric(
        "Misses",
        f"{int(selected_row['misses']):,}"
    )
