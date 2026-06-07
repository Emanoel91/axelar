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
# TITLE
# =====================================================

st.title("🛡️ Validator Analysis")

st.info(
    "Validator uptime analysis powered by Axelar uptime snapshots."
)

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data(ttl=300)
def load_uptime():

    url = "https://api.axelarscan.io/validator/searchUptimes"

    try:

        r = requests.get(
            url,
            timeout=60
        )

        r.raise_for_status()

        json_data = r.json()

        if "data" not in json_data:
            return pd.DataFrame()

        df = pd.DataFrame(
            json_data["data"]
        )

        if df.empty:
            return pd.DataFrame()

        # Safe timestamp conversion
        df["timestamp"] = pd.to_numeric(
            df["timestamp"],
            errors="coerce"
        )

        df = df[
            df["timestamp"].notna()
        ]

        df = df[
            df["timestamp"] > 0
        ]

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms",
            errors="coerce"
        )

        df = df.dropna(
            subset=["timestamp"]
        )

        df = df.sort_values(
            "timestamp"
        )

        return df

    except Exception as e:

        st.error(
            f"Failed to load data: {e}"
        )

        return pd.DataFrame()


df = load_uptime()

if df.empty:

    st.error(
        "No validator uptime data available."
    )

    st.stop()

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("Filters")

timeframe = st.sidebar.selectbox(
    "Timeframe",
    [
        "Last 24 Hours",
        "Last 7 Days",
        "Last 30 Days",
        "All Time"
    ]
)

latest_time = df["timestamp"].max()

if timeframe == "Last 24 Hours":

    df = df[
        df["timestamp"]
        >= latest_time - pd.Timedelta(days=1)
    ]

elif timeframe == "Last 7 Days":

    df = df[
        df["timestamp"]
        >= latest_time - pd.Timedelta(days=7)
    ]

elif timeframe == "Last 30 Days":

    df = df[
        df["timestamp"]
        >= latest_time - pd.Timedelta(days=30)
    ]

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
        .apply(
            lambda x:
            validator in x
        )
        .sum()
    )

    misses = (
        total_snapshots
        - appearances
    )

    uptime = (
        appearances
        / total_snapshots
        * 100
        if total_snapshots > 0
        else 0
    )

    records.append(
        {
            "validator": validator,
            "appearances": appearances,
            "misses": misses,
            "uptime": round(
                uptime,
                4
            )
        }
    )

stats_df = pd.DataFrame(records)

# =====================================================
# NETWORK METRICS
# =====================================================

active_df = df.copy()

active_df["active_count"] = (
    active_df["validators"]
    .apply(len)
)

avg_active = (
    active_df["active_count"]
    .mean()
)

best_uptime = (
    stats_df["uptime"].max()
)

worst_uptime = (
    stats_df["uptime"].min()
)

avg_uptime = (
    stats_df["uptime"].mean()
)

# =====================================================
# KPI ROW
# =====================================================

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
        f"{best_uptime:.2f}%"
    )

with col5:

    st.metric(
        "Worst Uptime",
        f"{worst_uptime:.2f}%"
    )

with col6:

    st.metric(
        "Average Uptime",
        f"{avg_uptime:.2f}%"
    )

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
        nbins=25,
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
# CHARTS ROW 2
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
        height=700,
        yaxis={
            "categoryorder":
            "total ascending"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    top_miss = (
        stats_df
        .sort_values(
            "misses",
            ascending=False
        )
        .head(20)
    )

    fig = px.bar(
        top_miss,
        x="misses",
        y="validator",
        orientation="h",
        title="Top 20 Validators by Miss Count"
    )

    fig.update_layout(
        height=700,
        yaxis={
            "categoryorder":
            "total ascending"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# NETWORK HEALTH SCORE
# =====================================================

st.subheader(
    "Network Health Trend"
)

health_df = active_df.copy()

max_active = (
    health_df["active_count"]
    .max()
)

health_df["health_score"] = (
    health_df["active_count"]
    / max_active
    * 100
)

fig = px.area(
    health_df,
    x="timestamp",
    y="health_score",
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

st.subheader(
    "Validator Ranking"
)

ranking = (
    stats_df
    .sort_values(
        "uptime",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)

ranking.index += 1

st.dataframe(
    ranking,
    use_container_width=True,
    height=600
)

# =====================================================
# VALIDATOR EXPLORER
# =====================================================

st.subheader(
    "Validator Explorer"
)

selected_validator = st.selectbox(
    "Select Validator",
    ranking["validator"]
)

timeline = df.copy()

timeline["online"] = (
    timeline["validators"]
    .apply(
        lambda x:
        1
        if selected_validator in x
        else 0
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
    ticktext=[
        "Offline",
        "Online"
    ]
)

fig.update_layout(
    height=500
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# SELECTED VALIDATOR KPI
# =====================================================

selected_stats = stats_df[
    stats_df["validator"]
    == selected_validator
].iloc[0]

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Uptime %",
        f"{selected_stats['uptime']:.2f}%"
    )

with col2:

    st.metric(
        "Appearances",
        f"{int(selected_stats['appearances']):,}"
    )

with col3:

    st.metric(
        "Misses",
        f"{int(selected_stats['misses']):,}"
    )
