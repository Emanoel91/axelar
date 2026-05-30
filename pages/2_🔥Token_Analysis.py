import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta 

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
with st.sidebar:

    st.image(
        "https://axelarscan.io/logos/logo.png",
        width=80
    )

    st.markdown(
        "Powered by [Axelar](https://axelar.network)"
    )

    st.markdown("---")

    st.markdown(
        "Built with Streamlit"
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
