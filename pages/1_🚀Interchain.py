import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Axelar Mega Dashboard",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)


# =====================================================
# CSS
# =====================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1c1c1c, #111111);
    border: 1px solid rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 18px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.25);
    transition: 0.25s ease;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    border: 1px solid rgba(255,116,0,0.35);
    box-shadow: 0 8px 24px rgba(255,116,0,0.15);
}

[data-testid="metric-container"] label {
    color: #9f9f9f !important;
    font-size: 15px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: white;
    font-size: 32px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():

    url = "https://api.axelarscan.io/api/interchainChart"

    r = requests.get(url, timeout=30)

    data = r.json()["data"]

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    return df


df_raw = load_data()
df = df_raw.copy()

# =====================================================
# SIDEBAR
# =====================================================

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

# =====================================================
# TITLE
# =====================================================
st.title("🚀 Interchain Analysis")

st.info(
    "All data is loaded from Axelar public API (no database required)."
)

# =====================================================
# FILTERS
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["month", "week", "day"]
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        pd.to_datetime("2025-01-01")
    )

with col3:
    end_date = st.date_input(
        "End Date",
        pd.to_datetime("2027-01-01")
    )

# =====================================================
# FILTER DATA
# =====================================================
df = df[
    (df["timestamp"] >= pd.to_datetime(start_date)) &
    (df["timestamp"] <= pd.to_datetime(end_date))
]

# =====================================================
# RESAMPLE
# =====================================================
if timeframe == "week":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("W")
        .apply(lambda r: r.start_time)
    )

elif timeframe == "month":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("M")
        .apply(lambda r: r.start_time)
    )

else:
    df["period"] = df["timestamp"]

grouped = (
    df.groupby("period")
    .sum(numeric_only=True)
    .reset_index()
)

grouped["total_txs"] = (
    grouped["gmp_num_txs"] +
    grouped["transfers_num_txs"]
)

grouped["total_volume"] = (
    grouped["gmp_volume"] +
    grouped["transfers_volume"]
)

# =====================================================
# BASE STATS
# =====================================================
daily_df = df.copy()

daily_df["day"] = daily_df["timestamp"].dt.date

daily_grouped = (
    daily_df.groupby("day")
    .sum(numeric_only=True)
    .reset_index()
)

daily_grouped["daily_volume"] = (
    daily_grouped["gmp_volume"] +
    daily_grouped["transfers_volume"]
)

daily_grouped["daily_txs"] = (
    daily_grouped["gmp_num_txs"] +
    daily_grouped["transfers_num_txs"]
)

avg_daily_volume = daily_grouped["daily_volume"].mean()
avg_daily_txs = daily_grouped["daily_txs"].mean()

weekly_df = df.copy()

weekly_df["week"] = (
    weekly_df["timestamp"]
    .dt
    .to_period("W")
    .apply(lambda r: r.start_time)
)

weekly_grouped = (
    weekly_df.groupby("week")
    .sum(numeric_only=True)
    .reset_index()
)

weekly_grouped["weekly_volume"] = (
    weekly_grouped["gmp_volume"] +
    weekly_grouped["transfers_volume"]
)

weekly_grouped["weekly_txs"] = (
    weekly_grouped["gmp_num_txs"] +
    weekly_grouped["transfers_num_txs"]
)

avg_weekly_volume = weekly_grouped["weekly_volume"].mean()
avg_weekly_txs = weekly_grouped["weekly_txs"].mean()

# =====================================================
# KPI ROW 1
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Transactions",
        f"{grouped['total_txs'].sum():,}"
    )

with col2:
    st.metric(
        "Total Volume",
        f"${grouped['total_volume'].sum():,.0f}"
    )

with col3:

    avg_volume_per_tx = (
        grouped["total_volume"].sum() /
        max(grouped["total_txs"].sum(), 1)
    )

    st.metric(
        "Avg Volume / Tx",
        f"${avg_volume_per_tx:,.2f}"
    )

# =====================================================
# KPI ROW 2
# =====================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Avg Daily Volume",
        f"${avg_daily_volume:,.0f}"
    )

with col2:
    st.metric(
        "Avg Weekly Volume",
        f"${avg_weekly_volume:,.0f}"
    )

with col3:
    st.metric(
        "Avg Daily Transactions",
        f"{avg_daily_txs:,.0f}"
    )

with col4:
    st.metric(
        "Avg Weekly Transactions",
        f"{avg_weekly_txs:,.0f}"
    )

# =====================================================
# KPI ROW 3
# =====================================================

def pct_change(series):

    if len(series) < 2:
        return 0

    return (
        (
            series.iloc[-1] - series.iloc[-2]
        ) / max(series.iloc[-2], 1)
    ) * 100


def last_diff(series):

    if len(series) < 2:
        return 0

    return series.iloc[-1] - series.iloc[-2]


# WEEKLY
df_w = df_raw.copy()

df_w["week"] = (
    df_w["timestamp"]
    .dt
    .to_period("W")
    .apply(lambda r: r.start_time)
)

w_group = (
    df_w.groupby("week")
    .sum(numeric_only=True)
    .reset_index()
)

w_group = w_group.sort_values("week")

w_group["tx"] = (
    w_group["gmp_num_txs"] +
    w_group["transfers_num_txs"]
)

w_group["vol"] = (
    w_group["gmp_volume"] +
    w_group["transfers_volume"]
)

weekly_tx_change = pct_change(w_group["tx"])
weekly_vol_change = pct_change(w_group["vol"])

weekly_tx_diff = last_diff(w_group["tx"])
weekly_vol_diff = last_diff(w_group["vol"])

# MONTHLY
df_m = df_raw.copy()

df_m["month"] = (
    df_m["timestamp"]
    .dt
    .to_period("M")
    .apply(lambda r: r.start_time)
)

m_group = (
    df_m.groupby("month")
    .sum(numeric_only=True)
    .reset_index()
)

m_group = m_group.sort_values("month")

m_group["tx"] = (
    m_group["gmp_num_txs"] +
    m_group["transfers_num_txs"]
)

m_group["vol"] = (
    m_group["gmp_volume"] +
    m_group["transfers_volume"]
)

monthly_tx_change = pct_change(m_group["tx"])
monthly_vol_change = pct_change(m_group["vol"])

monthly_tx_diff = last_diff(m_group["tx"])
monthly_vol_diff = last_diff(m_group["vol"])

# DISPLAY
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Weekly Volume % Change",
        f"{weekly_vol_change:.2f}%",
        delta=f"{weekly_vol_diff:,.0f}",
        delta_color="normal"
    )

with col2:
    st.metric(
        "Weekly Tx % Change",
        f"{weekly_tx_change:.2f}%",
        delta=f"{weekly_tx_diff:,.0f}",
        delta_color="normal"
    )

with col3:
    st.metric(
        "Monthly Volume % Change",
        f"{monthly_vol_change:.2f}%",
        delta=f"{monthly_vol_diff:,.0f}",
        delta_color="normal"
    )

with col4:
    st.metric(
        "Monthly Tx % Change",
        f"{monthly_tx_change:.2f}%",
        delta=f"{monthly_tx_diff:,.0f}",
        delta_color="normal"
    )

# =====================================================
# COLORS
# =====================================================
GMP_COLOR = "#ff7400"
TRANSFER_COLOR = "#00a1f7"

# =====================================================
# CHARTS ROW 4
# =====================================================
col1, col2 = st.columns(2)

with col1:

    fig1 = go.Figure()

    fig1.add_bar(
        x=grouped["period"],
        y=grouped["gmp_num_txs"],
        name="GMP",
        marker_color=GMP_COLOR
    )

    fig1.add_bar(
        x=grouped["period"],
        y=grouped["transfers_num_txs"],
        name="Transfers",
        marker_color=TRANSFER_COLOR
    )

    fig1.update_layout(
        barmode="stack",
        title="Transactions Over Time"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

with col2:

    fig2 = go.Figure()

    fig2.add_bar(
        x=grouped["period"],
        y=grouped["gmp_volume"],
        name="GMP",
        marker_color=GMP_COLOR
    )

    fig2.add_bar(
        x=grouped["period"],
        y=grouped["transfers_volume"],
        name="Transfers",
        marker_color=TRANSFER_COLOR
    )

    fig2.update_layout(
        barmode="stack",
        title="Volume Over Time"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# =====================================================
# CHARTS ROW 5 (NEW)
# =====================================================

monthly_daily = df.copy()

monthly_daily["day"] = (
    monthly_daily["timestamp"]
    .dt
    .floor("D")
)

daily_month = (
    monthly_daily.groupby("day")
    .sum(numeric_only=True)
    .reset_index()
)

daily_month["daily_volume"] = (
    daily_month["gmp_volume"] +
    daily_month["transfers_volume"]
)

daily_month["daily_txs"] = (
    daily_month["gmp_num_txs"] +
    daily_month["transfers_num_txs"]
)

daily_month["month"] = (
    pd.to_datetime(daily_month["day"])
    .dt
    .to_period("M")
    .astype(str)
)

# =====================================================
# MONTHLY VOLUME STATS
# =====================================================
monthly_volume_stats = (
    daily_month
    .groupby("month")["daily_volume"]
    .agg(["max", "mean", "min"])
    .reset_index()
)

monthly_volume_stats.columns = [
    "month",
    "max_volume",
    "avg_volume",
    "min_volume"
]

# =====================================================
# MONTHLY TX STATS
# =====================================================
monthly_tx_stats = (
    daily_month
    .groupby("month")["daily_txs"]
    .agg(["max", "mean", "min"])
    .reset_index()
)

monthly_tx_stats.columns = [
    "month",
    "max_txs",
    "avg_txs",
    "min_txs"
]

col1, col2 = st.columns(2)

# =====================================================
# VOLUME CHART
# =====================================================
with col1:

    fig5 = go.Figure()

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["max_volume"],
            mode="lines+markers",
            name="Max Daily Volume"
        )
    )

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["avg_volume"],
            mode="lines+markers",
            name="Avg Daily Volume"
        )
    )

    fig5.add_trace(
        go.Scatter(
            x=monthly_volume_stats["month"],
            y=monthly_volume_stats["min_volume"],
            mode="lines+markers",
            name="Min Daily Volume"
        )
    )

    fig5.update_layout(
        title="Monthly Daily Volume Statistics",
        xaxis_title="Month",
        yaxis_title="Volume",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig5,
        use_container_width=True
    )

# =====================================================
# TX CHART
# =====================================================
with col2:

    fig6 = go.Figure()

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["max_txs"],
            mode="lines+markers",
            name="Max Daily Tx"
        )
    )

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["avg_txs"],
            mode="lines+markers",
            name="Avg Daily Tx"
        )
    )

    fig6.add_trace(
        go.Scatter(
            x=monthly_tx_stats["month"],
            y=monthly_tx_stats["min_txs"],
            mode="lines+markers",
            name="Min Daily Tx"
        )
    )

    fig6.update_layout(
        title="Monthly Daily Transaction Statistics",
        xaxis_title="Month",
        yaxis_title="Transactions",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig6,
        use_container_width=True
    )

# =====================================================
# DONUT CHARTS ROW 6
# =====================================================
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
        title="Transactions Share"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

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
        title="Volume Share"
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

# =====================================================
# COHORT ANALYSIS
# =====================================================

st.markdown("---")
st.subheader("📊 Cohort Analysis")

cohort_df = df.copy()

# DAILY
cohort_df["day"] = (
    cohort_df["timestamp"]
    .dt
    .floor("D")
)

# MONTH COHORT
cohort_df["cohort_month"] = (
    cohort_df["timestamp"]
    .dt
    .to_period("M")
    .astype(str)
)

# DAY INDEX INSIDE MONTH
cohort_df["day_index"] = (
    cohort_df["timestamp"]
    .dt
    .day
)

# TOTAL DAILY VOLUME
cohort_daily = (
    cohort_df
    .groupby(["cohort_month", "day_index"])
    .sum(numeric_only=True)
    .reset_index()
)

cohort_daily["total_volume"] = (
    cohort_daily["gmp_volume"] +
    cohort_daily["transfers_volume"]
)

cohort_daily["total_txs"] = (
    cohort_daily["gmp_num_txs"] +
    cohort_daily["transfers_num_txs"]
)

# =====================================================
# VOLUME COHORT
# =====================================================

volume_pivot = cohort_daily.pivot_table(
    index="cohort_month",
    columns="day_index",
    values="total_volume",
    aggfunc="sum"
)

# =====================================================
# TX COHORT
# =====================================================

tx_pivot = cohort_daily.pivot_table(
    index="cohort_month",
    columns="day_index",
    values="total_txs",
    aggfunc="sum"
)

# =====================================================
# HEATMAPS
# =====================================================

col1, col2 = st.columns(2)

# -----------------------------------------------------
# VOLUME HEATMAP
# -----------------------------------------------------
with col1:

    fig_cohort_volume = go.Figure(
        data=go.Heatmap(
            z=volume_pivot.values,
            x=volume_pivot.columns,
            y=volume_pivot.index,
            colorscale="Oranges",
            colorbar_title="Volume"
        )
    )

    fig_cohort_volume.update_layout(
        title="Monthly Cohort Heatmap — Volume",
        xaxis_title="Day of Month",
        yaxis_title="Cohort Month",
        height=500
    )

    st.plotly_chart(
        fig_cohort_volume,
        use_container_width=True
    )

# -----------------------------------------------------
# TX HEATMAP
# -----------------------------------------------------
with col2:

    fig_cohort_tx = go.Figure(
        data=go.Heatmap(
            z=tx_pivot.values,
            x=tx_pivot.columns,
            y=tx_pivot.index,
            colorscale="Blues",
            colorbar_title="Transactions"
        )
    )

    fig_cohort_tx.update_layout(
        title="Monthly Cohort Heatmap — Transactions",
        xaxis_title="Day of Month",
        yaxis_title="Cohort Month",
        height=500
    )

    st.plotly_chart(
        fig_cohort_tx,
        use_container_width=True
    )

# =====================================================================================================================================================================

# =====================================================
# ADVANCED ANALYTICS
# =====================================================

st.markdown("---")
st.header("📈 Advanced Analytics")

# =====================================================
# PREPARE DAILY DATA
# =====================================================

advanced_df = df.copy()

advanced_df["day"] = (
    advanced_df["timestamp"]
    .dt
    .floor("D")
)

daily_adv = (
    advanced_df
    .groupby("day")
    .sum(numeric_only=True)
    .reset_index()
)

# TOTALS
daily_adv["total_volume"] = (
    daily_adv["gmp_volume"] +
    daily_adv["transfers_volume"]
)

daily_adv["total_txs"] = (
    daily_adv["gmp_num_txs"] +
    daily_adv["transfers_num_txs"]
)

# =====================================================
# ROLLING COHORT
# =====================================================

st.subheader("🔄 Rolling Cohort Analysis")

daily_adv["rolling_7d_volume"] = (
    daily_adv["total_volume"]
    .rolling(7)
    .mean()
)

daily_adv["rolling_30d_volume"] = (
    daily_adv["total_volume"]
    .rolling(30)
    .mean()
)

daily_adv["rolling_7d_txs"] = (
    daily_adv["total_txs"]
    .rolling(7)
    .mean()
)

daily_adv["rolling_30d_txs"] = (
    daily_adv["total_txs"]
    .rolling(30)
    .mean()
)

col1, col2 = st.columns(2)

# -----------------------------------------------------
# ROLLING VOLUME
# -----------------------------------------------------
with col1:

    fig_roll_vol = go.Figure()

    fig_roll_vol.add_trace(
        go.Scatter(
            x=daily_adv["day"],
            y=daily_adv["rolling_7d_volume"],
            mode="lines",
            name="7D Rolling Volume"
        )
    )

    fig_roll_vol.add_trace(
        go.Scatter(
            x=daily_adv["day"],
            y=daily_adv["rolling_30d_volume"],
            mode="lines",
            name="30D Rolling Volume"
        )
    )

    fig_roll_vol.update_layout(
        title="Rolling Volume Trend",
        xaxis_title="Date",
        yaxis_title="Volume",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_roll_vol,
        use_container_width=True
    )

# -----------------------------------------------------
# ROLLING TX
# -----------------------------------------------------
with col2:

    fig_roll_tx = go.Figure()

    fig_roll_tx.add_trace(
        go.Scatter(
            x=daily_adv["day"],
            y=daily_adv["rolling_7d_txs"],
            mode="lines",
            name="7D Rolling Tx"
        )
    )

    fig_roll_tx.add_trace(
        go.Scatter(
            x=daily_adv["day"],
            y=daily_adv["rolling_30d_txs"],
            mode="lines",
            name="30D Rolling Tx"
        )
    )

    fig_roll_tx.update_layout(
        title="Rolling Transaction Trend",
        xaxis_title="Date",
        yaxis_title="Transactions",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_roll_tx,
        use_container_width=True
    )

# =====================================================
# VOLUME DECAY COHORT
# =====================================================

st.subheader("📉 Volume Decay Cohort")

volume_decay = daily_adv.copy()

peak_volume = volume_decay["total_volume"].max()

volume_decay["decay_pct"] = (
    volume_decay["total_volume"] / peak_volume
) * 100

fig_decay = go.Figure()

fig_decay.add_trace(
    go.Scatter(
        x=volume_decay["day"],
        y=volume_decay["decay_pct"],
        mode="lines+markers",
        name="Volume Decay %"
    )
)

fig_decay.update_layout(
    title="Volume Decay From Historical Peak",
    xaxis_title="Date",
    yaxis_title="% Of Peak Volume",
    hovermode="x unified"
)

st.plotly_chart(
    fig_decay,
    use_container_width=True
)

# =====================================================
# WEEKDAY ANALYSIS
# =====================================================

st.subheader("📅 Weekday Analysis")

# =====================================================
# PREPARE DATA
# =====================================================

weekday_df = df.copy()

weekday_df["weekday"] = (
    weekday_df["timestamp"]
    .dt
    .day_name()
)

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

# =====================================================
# DAILY AGGREGATION
# =====================================================

weekday_daily = (
    weekday_df
    .groupby([
        weekday_df["timestamp"].dt.floor("D"),
        "weekday"
    ])
    .sum(numeric_only=True)
    .reset_index()
)

# =====================================================
# TOTALS
# =====================================================

weekday_daily["daily_volume"] = (
    weekday_daily["gmp_volume"] +
    weekday_daily["transfers_volume"]
)

weekday_daily["daily_txs"] = (
    weekday_daily["gmp_num_txs"] +
    weekday_daily["transfers_num_txs"]
)

# =====================================================
# AVERAGES
# =====================================================

avg_volume_weekday = (
    weekday_daily
    .groupby("weekday")["daily_volume"]
    .mean()
    .reindex(weekday_order)
    .reset_index()
)

avg_tx_weekday = (
    weekday_daily
    .groupby("weekday")["daily_txs"]
    .mean()
    .reindex(weekday_order)
    .reset_index()
)

# =====================================================
# BEAUTIFUL NUMBER FORMAT
# =====================================================

def human_format(num):

    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"

    elif num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"

    elif num >= 1_000:
        return f"{num/1_000:.2f}K"

    return f"{num:.2f}"

# ====================================================
# COLOR FUNCTION
# ====================================================

def generate_colors(values):

    max_value = values.max()
    min_value = values.min()

    colors = []

    for v in values:

        if v == max_value:
            colors.append("#90faae")  # GREEN

        elif v == min_value:
            colors.append("#ec9085")  # RED

        else:
            colors.append("#ff9951")  # ORANGE

    return colors

# =====================================================
# ADD LABELS
# =====================================================

avg_volume_weekday["label"] = (
    avg_volume_weekday["daily_volume"]
    .apply(human_format)
)

avg_tx_weekday["label"] = (
    avg_tx_weekday["daily_txs"]
    .apply(human_format)
)

# =====================================================
# COLUMNS
# =====================================================

col1, col2 = st.columns(2)

# =====================================================
# VOLUME CHART
# =====================================================

with col1:

    fig_volume = px.bar(

        avg_volume_weekday,

        x="weekday",
        y="daily_volume",

        text="label"
    )

    fig_volume.update_traces(

        marker_color=generate_colors(
            avg_volume_weekday["daily_volume"]
        ),

        textposition="outside",

        textfont_size=13,

        marker_line_width=0,

        cliponaxis=False
    )

    fig_volume.update_layout(

        title="Average Volume by Weekday",

        xaxis_title="Weekday",
        yaxis_title="Average Volume",

        template="plotly_dark",

        showlegend=False,

        height=500,

        yaxis=dict(
            range=[
                0,
                avg_volume_weekday["daily_volume"].max() * 1.20
            ]
        )
    )

    st.plotly_chart(
        fig_volume,
        use_container_width=True
    )

# =====================================================
# TRANSACTION CHART
# =====================================================

with col2:

    fig_tx = px.bar(

        avg_tx_weekday,

        x="weekday",
        y="daily_txs",

        text="label"
    )

    fig_tx.update_traces(

        marker_color=generate_colors(
            avg_tx_weekday["daily_txs"]
        ),

        textposition="outside",

        textfont_size=13,

        marker_line_width=0,

        cliponaxis=False
    )

    fig_tx.update_layout(

        title="Average Transactions by Weekday",

        xaxis_title="Weekday",
        yaxis_title="Average Transactions",

        template="plotly_dark",

        showlegend=False,

        height=500,

        yaxis=dict(
            range=[
                0,
                avg_tx_weekday["daily_txs"].max() * 1.20
            ]
        )
    )

    st.plotly_chart(
        fig_tx,
        use_container_width=True
    )

# ============================================================
# CHAIN FLOW ANALYSIS
# ============================================================

st.subheader("🌉 Chain Flow Analysis")

# ============================================================
# FETCH DATA
# ============================================================

try:

    chain_stats_url = (
        "https://api.axelarscan.io/gmp/GMPStatsByChains"
    )

    params = {}

    if selected_symbol != "All":
        params["symbol"] = selected_symbol

    params["fromTime"] = int(start_date.timestamp())
    params["toTime"] = int(end_date.timestamp())

    response = requests.get(
        chain_stats_url,
        params=params,
        timeout=60
    )

    chain_json = response.json()

    rows = []

    for source in chain_json.get("source_chains", []):

        source_chain = source["key"]

        for dest in source.get(
            "destination_chains",
            []
        ):

            rows.append({

                "source_chain": source_chain,
                "destination_chain": dest["key"],
                "transactions": dest["num_txs"],
                "volume": dest["volume"]

            })

    chain_df = pd.DataFrame(rows)

except Exception as e:

    st.error(
        f"Failed loading chain flow data: {e}"
    )

    chain_df = pd.DataFrame()

# ============================================================
# STOP IF EMPTY
# ============================================================

if not chain_df.empty:

    # ========================================================
    # HELPER
    # ========================================================

    def human_format(num):

        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.2f}B"

        elif num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"

        elif num >= 1_000:
            return f"{num/1_000:.2f}K"

        return f"{num:.2f}"

    # ========================================================
    # SANKEY PREP
    # ========================================================

    chains = pd.unique(
        chain_df[
            ["source_chain",
             "destination_chain"]
        ].values.ravel()
    )

    chain_to_idx = {
        chain:i
        for i, chain in enumerate(chains)
    }

    # ========================================================
    # SANKEY ROW
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        sankey_volume = go.Figure(

            go.Sankey(

                node=dict(
                    label=list(chains)
                ),

                link=dict(

                    source=chain_df[
                        "source_chain"
                    ].map(chain_to_idx),

                    target=chain_df[
                        "destination_chain"
                    ].map(chain_to_idx),

                    value=chain_df["volume"]

                )
            )
        )

        sankey_volume.update_layout(

            title="Chain Flow by Volume",

            template="plotly_dark",

            height=650
        )

        st.plotly_chart(
            sankey_volume,
            use_container_width=True
        )

    with col2:

        sankey_tx = go.Figure(

            go.Sankey(

                node=dict(
                    label=list(chains)
                ),

                link=dict(

                    source=chain_df[
                        "source_chain"
                    ].map(chain_to_idx),

                    target=chain_df[
                        "destination_chain"
                    ].map(chain_to_idx),

                    value=chain_df["transactions"]

                )
            )
        )

        sankey_tx.update_layout(

            title="Chain Flow by Transactions",

            template="plotly_dark",

            height=650
        )

        st.plotly_chart(
            sankey_tx,
            use_container_width=True
        )

    # ========================================================
    # RANKINGS
    # ========================================================

    source_volume = (
        chain_df
        .groupby("source_chain")["volume"]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    destination_volume = (
        chain_df
        .groupby("destination_chain")["volume"]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    source_tx = (
        chain_df
        .groupby("source_chain")["transactions"]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    destination_tx = (
        chain_df
        .groupby("destination_chain")["transactions"]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(

            source_volume,

            x="source_chain",
            y="volume",

            text=source_volume[
                "volume"
            ].apply(human_format)
        )

        fig.update_layout(

            title="Top Source Chains by Volume",

            template="plotly_dark",

            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        fig = px.bar(

            destination_volume,

            x="destination_chain",
            y="volume",

            text=destination_volume[
                "volume"
            ].apply(human_format)
        )

        fig.update_layout(

            title="Top Destination Chains by Volume",

            template="plotly_dark",

            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(

            source_tx,

            x="source_chain",
            y="transactions",

            text="transactions"
        )

        fig.update_layout(

            title="Top Source Chains by Transactions",

            template="plotly_dark",

            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        fig = px.bar(

            destination_tx,

            x="destination_chain",
            y="transactions",

            text="transactions"
        )

        fig.update_layout(

            title="Top Destination Chains by Transactions",

            template="plotly_dark",

            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # HEATMAPS
    # ========================================================

    st.subheader("🔥 Chain Pair Analysis")

    col1, col2 = st.columns(2)

    with col1:

        volume_heatmap = (
            chain_df
            .pivot_table(

                index="source_chain",
                columns="destination_chain",

                values="volume",

                aggfunc="sum",

                fill_value=0
            )
        )

        fig = px.imshow(

            volume_heatmap,

            aspect="auto",

            text_auto=".0f",

            title="Volume Heatmap"
        )

        fig.update_layout(
            template="plotly_dark",
            height=650
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        tx_heatmap = (
            chain_df
            .pivot_table(

                index="source_chain",
                columns="destination_chain",

                values="transactions",

                aggfunc="sum",

                fill_value=0
            )
        )

        fig = px.imshow(

            tx_heatmap,

            aspect="auto",

            text_auto=True,

            title="Transactions Heatmap"
        )

        fig.update_layout(
            template="plotly_dark",
            height=650
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )
