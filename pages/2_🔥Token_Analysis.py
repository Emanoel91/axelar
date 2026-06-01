import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta 
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
}

[data-testid="metric-container"] label {
    color: #9f9f9f !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: white;
}
</style>
""", unsafe_allow_html=True)

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
st.title("🔥 Token Analysis")

st.info(
    "Data source: Axelar GMPChart API"
)

# =====================================================
# FILTERS
# =====================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    token_symbol = st.text_input(
        "Token Symbol",
        value="XRP"
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        datetime.utcnow() - timedelta(days=365)
    )

with col3:
    end_date = st.date_input(
        "End Date",
        datetime.utcnow()
    )

with col4:
    timeframe = st.selectbox(
        "Time Frame",
        ["Day", "Week", "Month"]
    )

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data(ttl=3600)
def load_data(symbol, start_date, end_date):

    from_time = int(
        pd.Timestamp(start_date).timestamp()
    )

    to_time = int(
        pd.Timestamp(end_date).timestamp()
    )

    url = (
        "https://api.axelarscan.io/gmp/GMPChart"
        f"?symbol={symbol}"
        f"&fromTime={from_time}"
        f"&toTime={to_time}"
    )

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()["data"]

    df = pd.DataFrame(data)

    if len(df) == 0:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    df["volume"] = pd.to_numeric(
        df["volume"],
        errors="coerce"
    ).fillna(0)

    df["num_txs"] = pd.to_numeric(
        df["num_txs"],
        errors="coerce"
    ).fillna(0)

    return df


df = load_data(
    token_symbol,
    start_date,
    end_date
)

# =====================================================
# EMPTY DATA
# =====================================================
if df.empty:

    st.warning(
        "No data found for selected filters."
    )

    st.stop()

# =====================================================
# RESAMPLE
# =====================================================
if timeframe == "Week":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("W")
        .apply(lambda r: r.start_time)
    )

elif timeframe == "Month":

    df["period"] = (
        df["timestamp"]
        .dt
        .to_period("M")
        .apply(lambda r: r.start_time)
    )

else:

    df["period"] = (
        df["timestamp"]
        .dt
        .floor("D")
    )

grouped = (
    df.groupby("period")
    .agg({
        "volume": "sum",
        "num_txs": "sum"
    })
    .reset_index()
)

# =====================================================
# CUMULATIVE
# =====================================================
grouped["cumulative_volume"] = (
    grouped["volume"]
    .cumsum()
)

grouped["cumulative_txs"] = (
    grouped["num_txs"]
    .cumsum()
)

# =====================================================
# KPI CALCULATIONS
# =====================================================
total_volume = grouped["volume"].sum()

total_txs = grouped["num_txs"].sum()

avg_volume_per_tx = (
    total_volume / total_txs
    if total_txs > 0
    else 0
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
        f"{int(total_txs):,}"
    )

with col3:

    st.metric(
        "Avg Volume per Txn",
        f"${avg_volume_per_tx:,.2f}"
    )

# =====================================================
# CHART 1
# =====================================================
fig_volume = go.Figure()

fig_volume.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["volume"],
        name="Volume"
    )
)

fig_volume.add_trace(
    go.Scatter(
        x=grouped["period"],
        y=grouped["cumulative_volume"],
        name="Cumulative Volume",
        yaxis="y2",
        mode="lines+markers"
    )
)

fig_volume.update_layout(
    title=f"{token_symbol} Transfer Volume",
    template="plotly_dark",
    hovermode="x unified",
    yaxis=dict(
        title="Volume"
    ),
    yaxis2=dict(
        title="Cumulative Volume",
        overlaying="y",
        side="right"
    ),
    legend=dict(
        orientation="h"
    )
)

# =====================================================
# CHART 2
# =====================================================
fig_txs = go.Figure()

fig_txs.add_trace(
    go.Bar(
        x=grouped["period"],
        y=grouped["num_txs"],
        name="Transactions"
    )
)

fig_txs.add_trace(
    go.Scatter(
        x=grouped["period"],
        y=grouped["cumulative_txs"],
        name="Cumulative Transactions",
        yaxis="y2",
        mode="lines+markers"
    )
)

fig_txs.update_layout(
    title=f"{token_symbol} Transactions",
    template="plotly_dark",
    hovermode="x unified",
    yaxis=dict(
        title="Transactions"
    ),
    yaxis2=dict(
        title="Cumulative Transactions",
        overlaying="y",
        side="right"
    ),
    legend=dict(
        orientation="h"
    )
)

# =====================================================
# CHART ROW
# =====================================================
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        fig_volume,
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        fig_txs,
        use_container_width=True
    )

# =====================================================
# ADDITIONAL KPI CALCULATIONS
# =====================================================

# ---------- DAILY ----------

daily_stats = (
    df.groupby(
        df["timestamp"].dt.floor("D")
    )
    .agg({
        "volume": "sum",
        "num_txs": "sum"
    })
    .reset_index()
)

avg_volume_day = daily_stats["volume"].mean()

avg_tx_day = daily_stats["num_txs"].mean()

# ---------- MONTHLY ----------

monthly_stats = (
    df.groupby(
        df["timestamp"]
        .dt
        .to_period("M")
        .apply(lambda x: x.start_time)
    )
    .agg({
        "volume": "sum",
        "num_txs": "sum"
    })
    .reset_index()
)

avg_volume_month = monthly_stats["volume"].mean()

avg_tx_month = monthly_stats["num_txs"].mean()


# =====================================================
# WEEKLY / MONTHLY CHANGE
# THESE KPIs IGNORE DASHBOARD DATE FILTER
# =====================================================

@st.cache_data(ttl=3600)
def load_full_history(symbol):

    url = (
        "https://api.axelarscan.io/gmp/GMPChart"
        f"?symbol={symbol}"
    )

    r = requests.get(
        url,
        timeout=60
    )

    data = r.json()["data"]

    temp = pd.DataFrame(data)

    if len(temp) == 0:
        return pd.DataFrame()

    temp["timestamp"] = pd.to_datetime(
        temp["timestamp"],
        unit="ms"
    )

    temp["volume"] = pd.to_numeric(
        temp["volume"],
        errors="coerce"
    ).fillna(0)

    temp["num_txs"] = pd.to_numeric(
        temp["num_txs"],
        errors="coerce"
    ).fillna(0)

    return temp


full_df = load_full_history(token_symbol)

weekly_volume_change = 0
weekly_tx_change = 0

monthly_volume_change = 0
monthly_tx_change = 0

if not full_df.empty:

    # ==========================================
    # WEEKLY
    # ==========================================

    weekly = (
        full_df.groupby(
            full_df["timestamp"]
            .dt
            .to_period("W")
            .apply(lambda x: x.start_time)
        )
        .agg({
            "volume": "sum",
            "num_txs": "sum"
        })
        .reset_index()
    )

    if len(weekly) >= 2:

        last_week = weekly.iloc[-1]
        prev_week = weekly.iloc[-2]

        weekly_volume_change = (
            (
                last_week["volume"]
                - prev_week["volume"]
            )
            /
            max(prev_week["volume"], 1)
        ) * 100

        weekly_tx_change = (
            (
                last_week["num_txs"]
                - prev_week["num_txs"]
            )
            /
            max(prev_week["num_txs"], 1)
        ) * 100

    # ==========================================
    # MONTHLY
    # ==========================================

    monthly = (
        full_df.groupby(
            full_df["timestamp"]
            .dt
            .to_period("M")
            .apply(lambda x: x.start_time)
        )
        .agg({
            "volume": "sum",
            "num_txs": "sum"
        })
        .reset_index()
    )

    if len(monthly) >= 2:

        last_month = monthly.iloc[-1]
        prev_month = monthly.iloc[-2]

        monthly_volume_change = (
            (
                last_month["volume"]
                - prev_month["volume"]
            )
            /
            max(prev_month["volume"], 1)
        ) * 100

        monthly_tx_change = (
            (
                last_month["num_txs"]
                - prev_month["num_txs"]
            )
            /
            max(prev_month["num_txs"], 1)
        ) * 100

# =====================================================
# KPI ROW 2
# =====================================================

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Avg Volume per Day",
        f"${avg_volume_day:,.2f}"
    )

with col2:
    st.metric(
        "Avg Volume per Month",
        f"${avg_volume_month:,.2f}"
    )

with col3:
    st.metric(
        "Avg Transactions per Day",
        f"{avg_tx_day:,.2f}"
    )

with col4:
    st.metric(
        "Avg Transactions per Month",
        f"{avg_tx_month:,.2f}"
    )

# =====================================================
# ATH / ATL CALCULATIONS
# =====================================================

ath_volume_row = daily_stats.loc[
    daily_stats["volume"].idxmax()
]

atl_volume_row = daily_stats.loc[
    daily_stats["volume"].idxmin()
]

ath_tx_row = daily_stats.loc[
    daily_stats["num_txs"].idxmax()
]

atl_tx_row = daily_stats.loc[
    daily_stats["num_txs"].idxmin()
]

ath_volume = ath_volume_row["volume"]
atl_volume = atl_volume_row["volume"]

ath_tx = ath_tx_row["num_txs"]
atl_tx = atl_tx_row["num_txs"]

ath_volume_date = pd.to_datetime(
    ath_volume_row["timestamp"]
).strftime("%Y-%m-%d")

atl_volume_date = pd.to_datetime(
    atl_volume_row["timestamp"]
).strftime("%Y-%m-%d")

ath_tx_date = pd.to_datetime(
    ath_tx_row["timestamp"]
).strftime("%Y-%m-%d")

atl_tx_date = pd.to_datetime(
    atl_tx_row["timestamp"]
).strftime("%Y-%m-%d")

# =====================================================
# KPI ROW 3
# =====================================================

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "ATH Volume",
        f"${ath_volume:,.2f}"
    )

    st.markdown(
        f"""
        <div style="
        color:#00d26a;
        font-size:13px;
        margin-top:-8px;">
        📈 {ath_volume_date}
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.metric(
        "ATL Volume",
        f"${atl_volume:,.2f}"
    )

    st.markdown(
        f"""
        <div style="
        color:#ff4b4b;
        font-size:13px;
        margin-top:-8px;">
        📉 {atl_volume_date}
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:

    st.metric(
        "ATH Transactions",
        f"{int(ath_tx):,}"
    )

    st.markdown(
        f"""
        <div style="
        color:#00d26a;
        font-size:13px;
        margin-top:-8px;">
        📈 {ath_tx_date}
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:

    st.metric(
        "ATL Transactions",
        f"{int(atl_tx):,}"
    )

    st.markdown(
        f"""
        <div style="
        color:#ff4b4b;
        font-size:13px;
        margin-top:-8px;">
        📉 {atl_tx_date}
        </div>
        """,
        unsafe_allow_html=True
    )

# =====================================================
# KPI ROW 4
# =====================================================

st.markdown("---")

st.info(
    "The following growth metrics are calculated using the full historical dataset and are NOT affected by the selected dashboard date range."
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Weekly Volume % Change",
        f"{weekly_volume_change:,.2f}%"
    )

with col2:
    st.metric(
        "Weekly Tx % Change",
        f"{weekly_tx_change:,.2f}%"
    )

with col3:
    st.metric(
        "Monthly Volume % Change",
        f"{monthly_volume_change:,.2f}%"
    )

with col4:
    st.metric(
        "Monthly Tx % Change",
        f"{monthly_tx_change:,.2f}%"
    )

# =====================================================
# AVG VOLUME PER TRANSACTION ANALYSIS
# =====================================================

avg_volume_df = grouped.copy()

avg_volume_df["avg_volume_per_tx"] = (
    avg_volume_df["volume"] /
    avg_volume_df["num_txs"].replace(0, pd.NA)
)

avg_volume_df["avg_volume_per_tx"] = (
    avg_volume_df["avg_volume_per_tx"]
    .fillna(0)
)

# =====================================================
# DYNAMIC MOVING AVERAGES
# =====================================================

if timeframe == "Day":

    ma_short = 7
    ma_long = 30

elif timeframe == "Week":

    ma_short = 4
    ma_long = 12

else:  # Month

    ma_short = 3
    ma_long = 6

avg_volume_df["ma_short"] = (
    avg_volume_df["avg_volume_per_tx"]
    .rolling(
        window=ma_short,
        min_periods=1
    )
    .mean()
)

avg_volume_df["ma_long"] = (
    avg_volume_df["avg_volume_per_tx"]
    .rolling(
        window=ma_long,
        min_periods=1
    )
    .mean()
)

# =====================================================
# CHART 1
# AVG VOLUME PER TRANSACTION OVER TIME
# =====================================================

fig_avg_volume = go.Figure()

fig_avg_volume.add_trace(
    go.Scatter(
        x=avg_volume_df["period"],
        y=avg_volume_df["avg_volume_per_tx"],
        mode="lines",
        fill="tozeroy",
        name="Avg Volume / Tx"
    )
)

fig_avg_volume.update_layout(
    title=f"{token_symbol} Average Volume per Transaction Over Time",
    template="plotly_dark",
    hovermode="x unified",
    height=500,
    xaxis_title="",
    yaxis_title="Average Volume per Transaction"
)

# =====================================================
# CHART 2
# MOVING AVERAGES
# =====================================================

fig_ma = go.Figure()

fig_ma.add_trace(
    go.Scatter(
        x=avg_volume_df["period"],
        y=avg_volume_df["ma_short"],
        mode="lines",
        name=f"MA {ma_short}"
    )
)

fig_ma.add_trace(
    go.Scatter(
        x=avg_volume_df["period"],
        y=avg_volume_df["ma_long"],
        mode="lines",
        name=f"MA {ma_long}"
    )
)

fig_ma.update_layout(
    title=f"{token_symbol} Avg Volume per Transaction Moving Averages",
    template="plotly_dark",
    hovermode="x unified",
    height=500,
    xaxis_title="",
    yaxis_title="Average Volume per Transaction"
)

# =====================================================
# DASHBOARD ROW
# =====================================================

st.markdown("---")

st.subheader(
    "Average Volume per Transaction Analysis"
)

col1, col2 = st.columns(2)

with col1:

    st.plotly_chart(
        fig_avg_volume,
        use_container_width=True
    )

with col2:

    st.plotly_chart(
        fig_ma,
        use_container_width=True
    )

@st.cache_data(ttl=300)
def load_recent_transactions(symbol):

    url = (
        "https://api.axelarscan.io/gmp/searchGMP"
        f"?symbol={symbol}"
    )

    r = requests.get(url, timeout=60)

    if r.status_code != 200:
        return pd.DataFrame()

    data = r.json().get("data", [])

    rows = []

    for tx in data:

        try:

            source_chain = tx.get("origin_chain")

            destination_chain = (
                tx.get("call", {})
                  .get("returnValues", {})
                  .get("destinationChain")
            )

            if (
                str(source_chain).lower() == "axelar"
                or
                str(destination_chain).lower() == "axelar"
            ):
                continue

            tx_hash = (
                tx.get("call", {})
                  .get("transactionHash")
            )

            amount = tx.get("amount")

            symbol = tx.get("symbol")

            status = tx.get("simplified_status")

            message_id = tx.get("message_id")

            fee_usd = (
                tx.get("fees", {})
                  .get("base_fee_usd")
            )

            if (
                not source_chain
                or not destination_chain
                or not tx_hash
            ):
                continue

            rows.append(
                {
                    "Source Chain": source_chain,
                    "Destination Chain": destination_chain,
                    "Token": symbol,
                    "Amount": amount,
                    "Fee USD": fee_usd,
                    "Status": status,
                    "Tx Hash": tx_hash,
                    "Message ID": message_id
                }
            )

        except Exception:
            continue

    df = pd.DataFrame(rows)

    df = df.dropna(how="all")

    return df

# =====================================================
# RECENT TRANSACTIONS TABLE
# =====================================================

st.markdown("---")

st.subheader(
    f"Latest {token_symbol} Cross-Chain Transactions"
)

tx_df = load_recent_transactions(token_symbol)

if not tx_df.empty:

    tx_df = tx_df[
        [
            "Source Chain",
            "Destination Chain",
            "Token",
            "Amount",
            "Fee USD",
            "Status",
            "Tx Hash",
            "Message ID"
        ]
    ]

    st.dataframe(
        tx_df,
        use_container_width=True,
        hide_index=True,
        height=650
    )

else:

    st.warning(
        "No recent transactions found."
    )

# =====================================================
# COHORT ANALYSIS
# =====================================================

st.markdown("---")
st.subheader("🔥 Cohort Analysis")

cohort_df = df.copy()

cohort_df["cohort_month"] = (
    cohort_df["timestamp"]
    .dt.strftime("%Y-%m")
)

cohort_df["day_of_month"] = (
    cohort_df["timestamp"]
    .dt.day
)

# =====================================================
# VOLUME HEATMAP
# =====================================================

volume_matrix = (
    cohort_df
    .pivot_table(
        index="cohort_month",
        columns="day_of_month",
        values="volume",
        aggfunc="sum"
    )
    .fillna(0)
)

# =====================================================
# TRANSACTION HEATMAP
# =====================================================

tx_matrix = (
    cohort_df
    .pivot_table(
        index="cohort_month",
        columns="day_of_month",
        values="num_txs",
        aggfunc="sum"
    )
    .fillna(0)
)

# =====================================================
# PLOTS
# =====================================================

col1, col2 = st.columns(2)

# -----------------------------------------------------
# VOLUME COHORT
# -----------------------------------------------------

with col1:

    fig_volume = go.Figure(
        data=go.Heatmap(
            z=volume_matrix.values,
            x=volume_matrix.columns,
            y=volume_matrix.index,
            colorscale="YlOrRd",
            hovertemplate=
            "Month: %{y}<br>" +
            "Day: %{x}<br>" +
            "Volume: %{z:,.2f}<extra></extra>"
        )
    )

    fig_volume.update_layout(
        title="Monthly Cohort Heatmap - Volume",
        xaxis_title="Day of Month",
        yaxis_title="Cohort Month",
        height=500,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        )
    )

    st.plotly_chart(
        fig_volume,
        use_container_width=True
    )

# -----------------------------------------------------
# TX COHORT
# -----------------------------------------------------

with col2:

    fig_tx = go.Figure(
        data=go.Heatmap(
            z=tx_matrix.values,
            x=tx_matrix.columns,
            y=tx_matrix.index,
            colorscale="Blues",
            hovertemplate=
            "Month: %{y}<br>" +
            "Day: %{x}<br>" +
            "Transactions: %{z:,.0f}<extra></extra>"
        )
    )

    fig_tx.update_layout(
        title="Monthly Cohort Heatmap - Transactions",
        xaxis_title="Day of Month",
        yaxis_title="Cohort Month",
        height=500,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        )
    )

    st.plotly_chart(
        fig_tx,
        use_container_width=True
    )

# =====================================================
# WEEKDAY ANALYSIS
# =====================================================

st.markdown("---")
st.subheader("📅 Weekday Analysis")

# =====================================================
# PREPARE DATA
# =====================================================

weekday_df = df.copy()

weekday_df["weekday"] = (
    weekday_df["timestamp"]
    .dt.day_name()
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
# DAILY DATA
# =====================================================

weekday_daily = (
    weekday_df
    .groupby(
        [
            weekday_df["timestamp"].dt.floor("D"),
            "weekday"
        ]
    )
    .agg(
        {
            "volume": "sum",
            "num_txs": "sum"
        }
    )
    .reset_index()
)

# =====================================================
# AVERAGES BY WEEKDAY
# =====================================================

avg_volume_weekday = (
    weekday_daily
    .groupby("weekday")["volume"]
    .mean()
    .reindex(weekday_order)
    .reset_index()
)

avg_tx_weekday = (
    weekday_daily
    .groupby("weekday")["num_txs"]
    .mean()
    .reindex(weekday_order)
    .reset_index()
)

# =====================================================
# FORMATTERS
# =====================================================

def human_format(num):

    if pd.isna(num):
        return "0"

    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"

    elif num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"

    elif num >= 1_000:
        return f"{num/1_000:.2f}K"

    return f"{num:.2f}"


def generate_colors(values):

    max_value = values.max()
    min_value = values.min()

    colors = []

    for v in values:

        if v == max_value:
            colors.append("#01b433")

        elif v == min_value:
            colors.append("#fa3535")

        else:
            colors.append("#6eb5fc")

    return colors

# =====================================================
# LABELS
# =====================================================

avg_volume_weekday["label"] = (
    avg_volume_weekday["volume"]
    .apply(human_format)
)

avg_tx_weekday["label"] = (
    avg_tx_weekday["num_txs"]
    .apply(human_format)
)

# =====================================================
# CHARTS
# =====================================================

col1, col2 = st.columns(2)

# =====================================================
# AVG VOLUME BY WEEKDAY
# =====================================================

with col1:

    fig_volume = px.bar(

        avg_volume_weekday,

        x="weekday",
        y="volume",

        text="label"
    )

    fig_volume.update_traces(

        marker_color=generate_colors(
            avg_volume_weekday["volume"]
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
                avg_volume_weekday["volume"].max() * 1.20
            ]
        )
    )

    st.plotly_chart(
        fig_volume,
        use_container_width=True
    )

# =====================================================
# AVG TRANSACTIONS BY WEEKDAY
# =====================================================

with col2:

    fig_tx = px.bar(

        avg_tx_weekday,

        x="weekday",
        y="num_txs",

        text="label"
    )

    fig_tx.update_traces(

        marker_color=generate_colors(
            avg_tx_weekday["num_txs"]
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
                avg_tx_weekday["num_txs"].max() * 1.20
            ]
        )
    )

    st.plotly_chart(
        fig_tx,
        use_container_width=True
    )

# =================================================
# KPI CALCULATIONS
# =================================================

active_routes = len(
    routes_df["route"]
    .unique()
)

source_chains = sorted(
    routes_df["source_chain"]
    .dropna()
    .unique()
    .tolist()
)

destination_chains = sorted(
    routes_df["destination_chain"]
    .dropna()
    .unique()
    .tolist()
)

# =================================================
# CHAIN LIST FORMATTER
# =================================================

def compact_chain_list(
    chains,
    max_items=4
):

    if len(chains) <= max_items:

        return " • ".join(
            chains
        )

    return (
        " • ".join(
            chains[:max_items]
        )
        + f" +{len(chains)-max_items}"
    )

source_chain_text = (
    compact_chain_list(
        source_chains
    )
)

destination_chain_text = (
    compact_chain_list(
        destination_chains
    )
)

# =================================================
# KPI ROW
# =================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Active Routes",
        f"{active_routes:,}"
    )

with col2:

    st.metric(
        "Source Chains",
        f"{len(source_chains):,}"
    )

    st.caption(
        source_chain_text
    )

with col3:

    st.metric(
        "Destination Chains",
        f"{len(destination_chains):,}"
    )

    st.caption(
        destination_chain_text
    )
