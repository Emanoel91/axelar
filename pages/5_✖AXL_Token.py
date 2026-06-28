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

# =========================================================================== Part 2: Price Analysis ====================================================================
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# =========================
# Config
# =========================
TOKEN = "ethereum:0x467719ad09025fcc6cf6f8311755809d45a5e5f3"
BASE_URL = f"https://coins.llama.fi/chart/{TOKEN}"

START_TS = int(datetime(2023, 1, 1).timestamp())
END_TS = int(datetime.now().timestamp())

SPAN_LIMIT = 500  # API limit

# =========================
# Fetch function (chunked)
# =========================
def fetch_chunked_prices(start_ts, end_ts):
    all_prices = []
    current_start = start_ts

    while current_start < end_ts:

        params = {
            "start": current_start,
            "period": "1d",
            "span": SPAN_LIMIT
        }

        r = requests.get(BASE_URL, params=params)
        data = r.json()

        coins = data.get("coins", {})
        token_data = coins.get(TOKEN, {})

        prices = token_data.get("prices", [])

        if not prices:
            break

        all_prices.extend(prices)

        # move forward
        last_ts = prices[-1]["timestamp"]
        current_start = last_ts + 1

    return all_prices


# =========================
# Streamlit UI
# =========================
st.title("AXL Price Chart (2023 → Today)")

with st.spinner("Fetching data from DefiLlama..."):
    prices = fetch_chunked_prices(START_TS, END_TS)

if not prices:
    st.error("No data received from API")
    st.stop()

# =========================
# DataFrame
# =========================
df = pd.DataFrame(prices)

df = df.drop_duplicates(subset=["timestamp"])
df = df.sort_values("timestamp")

df["date"] = pd.to_datetime(df["timestamp"], unit="s")

# =========================
# Chart
# =========================
st.subheader("AXL Daily Price")

st.line_chart(
    df.set_index("date")["price"]
)

# =========================
# Stats
# =========================
st.subheader("Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Start Price", round(df["price"].iloc[0], 4))
col2.metric("Latest Price", round(df["price"].iloc[-1], 4))
col3.metric("Data Points", len(df))
