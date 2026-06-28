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
# PART III : AXL PRICE CHART
# =====================================================

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

st.divider()
st.header("📈 AXL Price Dashboard")

# =====================================================
# API
# =====================================================

@st.cache_data(ttl=300)
def get_price_chart(start_ts, span, period):

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/chart/{coin}"

    params = {
        "start": start_ts,
        "period": period,
        "span": span
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json()["coins"].get(coin)


@st.cache_data(ttl=300)
def get_candle_chart(start_ts, span):

    coin = f"{CHAIN}:{TOKEN_ADDRESS}"

    url = f"https://coins.llama.fi/chart/{coin}"

    params = {
        "start": start_ts,
        "period": "4H",
        "span": span
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json()["coins"].get(coin)
