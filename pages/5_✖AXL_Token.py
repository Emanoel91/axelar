import streamlit as st
import requests

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelarscan",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# --- Title -----------------------------------------------------------------------------------------------------
st.title("📊 AXL Token Info")

st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Footer Slightly Left-Aligned ---------------------------------------------------------------------
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
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo">
                Powered by Axelar
            </a>
        </div>
        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/2060406047391559681/sA9zPNKM_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Fetch Token Info from API ----------------------------------------------------------------------------------
@st.cache_data(ttl=300)
def get_token_info():
    url = "https://api.axelarscan.io/api/getTokenInfo"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

try:
    data = get_token_info()

    price = data.get("price", 0)
    market_cap = data.get("marketCap", 0)
    circulating_supply = data.get("circulatingSupply", 0)
    max_supply = data.get("maxSupply", 0)
    total_burned = data.get("totalBurned", 0)
    inflation = data.get("inflation", 0)

    # --- KPI Display Section -----------------------------------------------------------------------------------
    st.markdown("### 💎 AXL Key Performance Indicators")

    st.markdown(
        """
        <style>
        div[data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: 700;
            color: #00B8F4;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 15px;
            color: #888;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Row 1 ---
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "💰 Current Price (USD)",
            f"${float(price):,.3f}"
        )

    with col2:
        st.metric(
            "🏦 Market Cap (USD)",
            f"${float(market_cap):,.0f}"
        )

    # --- Row 2 ---
    col3, col4 = st.columns(2)

    with col3:
        st.metric(
            "🔄 Circulating Supply",
            f"{float(circulating_supply):,.0f} AXL"
        )

    with col4:
        st.metric(
            "📈 Max Supply",
            f"{float(max_supply):,.0f} AXL"
        )

    # --- Row 3 ---
    col5, col6 = st.columns(2)

    with col5:
        st.metric(
            "🔥 Total Burned",
            f"{float(total_burned):,.0f} AXL"
        )

    with col6:
        st.metric(
            "📊 Inflation",
            f"{float(inflation) * 100:.2f}%"
        )

except Exception as e:
    st.error(f"❌ Error fetching token data: {e}")

# ======================================================================= Part 2: AXL Price Analysis =============================================================
import streamlit as st
import requests

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Axelar (AXL) Dashboard",
    page_icon="🟢",
    layout="wide"
)

st.title("🟢 Axelar (AXL) Dashboard")
st.header("💲 Current AXL Price")

# =====================================================
# FIXED TOKEN
# =====================================================

CHAIN = "ethereum"
TOKEN_ADDRESS = "0x467719ad09025fcc6cf6f8311755809d45a5e5f3"

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

[data-testid="metric-container"]{
    background:linear-gradient(
        135deg,
        rgba(220,252,231,0.95),
        rgba(187,247,208,0.85)
    );
    border:1px solid #86efac;
    padding:25px;
    border-radius:18px;
    box-shadow:0px 4px 15px rgba(34,197,94,.15);
}

div[data-testid="stMetricLabel"]{
    font-size:18px !important;
    font-weight:700 !important;
    color:#166534 !important;
}

div[data-testid="stMetricValue"]{
    font-size:42px !important;
    font-weight:800 !important;
    color:#14532d !important;
}

.small-metric [data-testid="metric-container"]{
    background:#111111;
    border:1px solid rgba(255,255,255,.08);
}

.small-metric div[data-testid="stMetricLabel"]{
    color:white !important;
    font-size:14px !important;
}

.small-metric div[data-testid="stMetricValue"]{
    color:white !important;
    font-size:24px !important;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# API
# =====================================================

@st.cache_data(ttl=300)
def get_token_price():

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/prices/current/{coin}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    return data["coins"].get(coin)

# =====================================================
# LOAD DATA AUTOMATICALLY
# =====================================================

try:

    token = get_token_price()

    if token is None:
        st.error("AXL token not found.")
        st.stop()

    symbol = token.get("symbol", "AXL")
    price = float(token.get("price", 0))
    decimals = token.get("decimals", "-")
    confidence = token.get("confidence", 0)

    # =================================================
    # MAIN KPI
    # =================================================

    st.metric(
        label="Current Price (AXL)",
        value=f"${price:,.6f}"
    )

    st.write("")

    # =================================================
    # DETAILS
    # =================================================

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="small-metric">', unsafe_allow_html=True)
        st.metric("Token", "Axelar (AXL)")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="small-metric">', unsafe_allow_html=True)
        st.metric("Decimals", decimals)
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="small-metric">', unsafe_allow_html=True)

        st.metric(
            "Confidence",
            f"{confidence:.2%}" if confidence else "N/A"
        )

        st.markdown("</div>", unsafe_allow_html=True)

except Exception as e:

    st.error(f"Error : {e}")

# =====================================================
# PART II : HISTORICAL AXL PRICE
# =====================================================

from datetime import datetime, timezone

st.divider()
st.header("📅 Historical AXL Price")

# =====================================================
# API
# =====================================================

@st.cache_data(ttl=300)
def get_historical_price(timestamp):

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/prices/historical/{timestamp}/{coin}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    return data["coins"].get(coin)

# =====================================================
# DATE SELECTION
# =====================================================

selected_date = st.date_input(
    "Select Historical Date",
    value=datetime.utcnow().date(),
    key="historical_date"
)

# =====================================================
# LOAD DATA AUTOMATICALLY
# =====================================================

try:

    dt = datetime.combine(
        selected_date,
        datetime.min.time()
    ).replace(tzinfo=timezone.utc)

    timestamp = int(dt.timestamp())

    token = get_historical_price(timestamp)

    if token is None:
        st.warning("Historical price is not available for this date.")
        st.stop()

    symbol = token.get("symbol", "AXL")
    price = float(token.get("price", 0))
    confidence = token.get("confidence", 0)

    actual_timestamp = token.get("timestamp")

    actual_date = datetime.utcfromtimestamp(
        actual_timestamp
    ).strftime("%Y-%m-%d %H:%M UTC")

    # =================================================
    # MAIN KPI
    # =================================================

    st.metric(
        label="Historical Price (AXL)",
        value=f"${price:,.6f}"
    )

    # =================================================
    # DETAILS
    # =================================================

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Token",
            "Axelar (AXL)"
        )

    with col2:
        st.metric(
            "Confidence",
            f"{confidence:.2%}" if confidence else "N/A"
        )

    with col3:
        st.metric(
            "Timestamp",
            actual_date
        )

except Exception as e:

    st.error(f"Error: {e}")

# =====================================================
# PART III : AXL PRICE DASHBOARD
# =====================================================

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

st.divider()
st.header("📈 AXL Price Dashboard")

# =====================================================
# FIXED TOKEN
# =====================================================

CHAIN = "ethereum"
TOKEN_ADDRESS = "0x467719ad09025fcc6cf6f8311755809d45a5e5f3"

# =====================================================
# API : PRICE CHART
# =====================================================

@st.cache_data(ttl=300)
def get_price_chart(start_ts, span, period):

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/chart/{coin}"

    params = {
        "start": start_ts,
        "span": span,
        "period": period
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["coins"].get(coin)


# =====================================================
# API : CANDLE DATA
# =====================================================

@st.cache_data(ttl=300)
def get_candle_4h(start_ts, span):

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/chart/{coin}"

    params = {
        "start": start_ts,
        "span": span,
        "period": "4H"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["coins"].get(coin)


# =====================================================
# DASHBOARD SETTINGS
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:

    start_date = st.date_input(
        "Start Date",
        value=datetime(2024, 1, 1).date()
    )

with col2:

    end_date = st.date_input(
        "End Date",
        value=datetime.utcnow().date()
    )

with col3:

    period = st.selectbox(
        "Interval",
        [
            "1H",
            "4H",
            "12H",
            "1D",
            "7D"
        ],
        index=3
    )

# =====================================================
# TIME CONVERSION
# =====================================================

start_ts = int(
    datetime.combine(
        start_date,
        datetime.min.time()
    ).replace(
        tzinfo=timezone.utc
    ).timestamp()
)

end_ts = int(
    datetime.combine(
        end_date,
        datetime.min.time()
    ).replace(
        tzinfo=timezone.utc
    ).timestamp()
)

if end_ts <= start_ts:

    st.error("End Date must be after Start Date")
    st.stop()

seconds_map = {
    "1H": 3600,
    "4H": 14400,
    "12H": 43200,
    "1D": 86400,
    "7D": 604800
}

span = int(
    (end_ts - start_ts) /
    seconds_map[period]
)

if span < 1:
    span = 1

# =====================================================
# LOAD PRICE DATA
# =====================================================

token = get_price_chart(
    start_ts,
    span,
    period
)

if token is None:

    st.error("No chart data found.")
    st.stop()

symbol = token["symbol"]

prices = token["prices"]

df_chart = pd.DataFrame(prices)

df_chart["datetime"] = pd.to_datetime(
    df_chart["timestamp"],
    unit="s"
)

# =====================================================
# PRICE STATISTICS
# =====================================================

first_price = df_chart["price"].iloc[0]

last_price = df_chart["price"].iloc[-1]

change_pct = (
    (last_price - first_price)
    / first_price
) * 100

ath_price = df_chart["price"].max()

atl_price = df_chart["price"].min()

avg_price = df_chart["price"].mean()

# =====================================================
# LINE CHART
# =====================================================

fig = px.line(
    df_chart,
    x="datetime",
    y="price",
    title="Axelar (AXL) Price History"
)

fig.update_traces(
    line_width=3
)

fig.update_layout(
    height=650,
    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# KPI ROW 1
# =====================================================

k1, k2, k3 = st.columns(3)

with k1:
    st.metric(
        "Start Price",
        f"${first_price:,.6f}"
    )

with k2:
    st.metric(
        "Current Price",
        f"${last_price:,.6f}"
    )

with k3:
    st.metric(
        "Return",
        f"{change_pct:.2f}%"
    )

# =====================================================
# KPI ROW 2
# =====================================================

k4, k5, k6 = st.columns(3)

with k4:
    st.metric(
        "Highest Price",
        f"${ath_price:,.6f}"
    )

with k5:
    st.metric(
        "Lowest Price",
        f"${atl_price:,.6f}"
    )

with k6:
    st.metric(
        "Average Price",
        f"${avg_price:,.6f}"
    )

# =====================================================
# CANDLESTICK CHART (4H)
# =====================================================

st.subheader("🕯️ Candlestick Chart")

candle_span = int(
    (end_ts - start_ts) / (4 * 3600)
)

if candle_span < 1:
    candle_span = 1

candle_token = get_candle_4h(
    start_ts,
    candle_span
)

if candle_token is not None:

    candle_prices = candle_token["prices"]

    df_candle = pd.DataFrame(candle_prices)

    df_candle["datetime"] = pd.to_datetime(
        df_candle["timestamp"],
        unit="s"
    )

    df_candle["date"] = (
        df_candle["datetime"]
        .dt
        .floor("D")
    )

    ohlc = (
        df_candle
        .groupby("date")["price"]
        .agg(
            Open="first",
            High="max",
            Low="min",
            Close="last"
        )
        .reset_index()
    )

    fig_candle = go.Figure()

    fig_candle.add_trace(

        go.Candlestick(

            x=ohlc["date"],

            open=ohlc["Open"],

            high=ohlc["High"],

            low=ohlc["Low"],

            close=ohlc["Close"],

            name="AXL"

        )

    )

    fig_candle.update_layout(

        height=700,

        xaxis_title="Date",

        yaxis_title="Price (USD)",

        hovermode="x unified",

        xaxis_rangeslider_visible=False

    )

    st.plotly_chart(
        fig_candle,
        use_container_width=True
    )

# =====================================================
# TECHNICAL INDICATORS
# =====================================================

st.divider()

st.header("📊 Technical Indicators")

# نمایش خودکار مهم‌ترین اندیکاتورها

selected_indicators = [

    "SMA",

    "EMA",

    "RSI",

    "MACD",

    "Bollinger Bands",

    "Z-Score"

]

# =====================================================
# DATAFRAME
# =====================================================

df_ind = df_chart.copy()

df_ind["returns"] = (
    df_ind["price"]
    .pct_change()
)

df_ind["log_returns"] = np.log(
    df_ind["price"]
).diff()

window = 14

rolling = 20

# =====================================================
# MOVING AVERAGES
# =====================================================

df_ind["SMA"] = (

    df_ind["price"]

    .rolling(20)

    .mean()

)

df_ind["EMA"] = (

    df_ind["price"]

    .ewm(span=20)

    .mean()

)

df_ind["WMA"] = (

    df_ind["price"]

    .rolling(20)

    .apply(

        lambda x:

        np.dot(

            x,

            np.arange(

                1,

                len(x)+1

            )

        )

        /

        np.sum(

            np.arange(

                1,

                len(x)+1

            )

        )

    )

)

# =====================================================
# RSI
# =====================================================

delta = df_ind["price"].diff()

gain = delta.clip(lower=0)

loss = -delta.clip(upper=0)

avg_gain = gain.rolling(window).mean()

avg_loss = loss.rolling(window).mean()

rs = avg_gain / avg_loss

df_ind["RSI"] = 100 - (

    100 /

    (1 + rs)

)

# =====================================================
# MACD
# =====================================================

ema12 = (

    df_ind["price"]

    .ewm(span=12)

    .mean()

)

ema26 = (

    df_ind["price"]

    .ewm(span=26)

    .mean()

)

df_ind["MACD"] = ema12 - ema26

df_ind["MACD_signal"] = (

    df_ind["MACD"]

    .ewm(span=9)

    .mean()

)

# =====================================================
# BOLLINGER BANDS
# =====================================================

df_ind["BB_MID"] = (

    df_ind["price"]

    .rolling(20)

    .mean()

)

df_ind["BB_STD"] = (

    df_ind["price"]

    .rolling(20)

    .std()

)

df_ind["BB_UPPER"] = (

    df_ind["BB_MID"]

    +

    2 * df_ind["BB_STD"]

)

df_ind["BB_LOWER"] = (

    df_ind["BB_MID"]

    -

    2 * df_ind["BB_STD"]

)

# =====================================================
# Z SCORE
# =====================================================

df_ind["Z"] = (

    df_ind["price"]

    -

    df_ind["BB_MID"]

) / df_ind["BB_STD"]

# =====================================================
# ROC
# =====================================================

df_ind["ROC"] = (

    df_ind["price"]

    .pct_change(periods=10)

    * 100

)

# =====================================================
# MOMENTUM
# =====================================================

df_ind["Momentum"] = (

    df_ind["price"]

    -

    df_ind["price"].shift(10)

)

# =====================================================
# ROLLING STATISTICS
# =====================================================

df_ind["Rolling_Mean"] = (

    df_ind["price"]

    .rolling(20)

    .mean()

)

df_ind["Rolling_Std"] = (

    df_ind["price"]

    .rolling(20)

    .std()

)

# =====================================================
# VOLATILITY
# =====================================================

df_ind["Volatility"] = (

    df_ind["returns"]

    .rolling(20)

    .std()

    * np.sqrt(365)

)
# =====================================================
# CANDLESTICK + INDICATORS
# =====================================================

st.subheader("🕯️ Candlestick + Technical Indicators")

fig = go.Figure()

# -----------------------------------------------------
# Candlestick
# -----------------------------------------------------

fig.add_trace(
    go.Candlestick(
        x=ohlc["date"],
        open=ohlc["Open"],
        high=ohlc["High"],
        low=ohlc["Low"],
        close=ohlc["Close"],
        name="AXL Price"
    )
)

# -----------------------------------------------------
# SMA
# -----------------------------------------------------

if "SMA" in selected_indicators:

    fig.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["SMA"],
            name="SMA 20",
            line=dict(width=2)
        )
    )

# -----------------------------------------------------
# EMA
# -----------------------------------------------------

if "EMA" in selected_indicators:

    fig.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["EMA"],
            name="EMA 20",
            line=dict(width=2)
        )
    )

# -----------------------------------------------------
# Bollinger Bands
# -----------------------------------------------------

if "Bollinger Bands" in selected_indicators:

    fig.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["BB_UPPER"],
            name="BB Upper",
            line=dict(dash="dot")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["BB_LOWER"],
            name="BB Lower",
            line=dict(dash="dot")
        )
    )

fig.update_layout(
    height=750,
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    yaxis_title="Price (USD)"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# RSI
# =====================================================

if "RSI" in selected_indicators:

    st.subheader("📉 Relative Strength Index (RSI)")

    fig_rsi = px.line(
        df_ind,
        x="datetime",
        y="RSI",
        title="RSI (14)"
    )

    fig_rsi.add_hline(
        y=70,
        line_dash="dash"
    )

    fig_rsi.add_hline(
        y=30,
        line_dash="dash"
    )

    fig_rsi.update_layout(
        height=350,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_rsi,
        use_container_width=True
    )

# =====================================================
# MACD
# =====================================================

if "MACD" in selected_indicators:

    st.subheader("📊 MACD")

    fig_macd = go.Figure()

    fig_macd.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["MACD"],
            name="MACD"
        )
    )

    fig_macd.add_trace(
        go.Scatter(
            x=df_ind["datetime"],
            y=df_ind["MACD_signal"],
            name="Signal"
        )
    )

    fig_macd.update_layout(
        height=350,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_macd,
        use_container_width=True
    )

# =====================================================
# Z-SCORE
# =====================================================

if "Z-Score" in selected_indicators:

    st.subheader("📐 Z-Score")

    fig_z = px.line(
        df_ind,
        x="datetime",
        y="Z",
        title="Price Z-Score"
    )

    fig_z.add_hline(
        y=2,
        line_dash="dash"
    )

    fig_z.add_hline(
        y=-2,
        line_dash="dash"
    )

    fig_z.update_layout(
        height=350,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_z,
        use_container_width=True
    )

# =====================================================
# DASHBOARD FOOTER
# =====================================================

st.divider()

st.caption(
    "Axelar (AXL) Dashboard | Powered by DefiLlama API | Streamlit"
)
