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
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from time import time

# =====================================================
# Configuration
# =====================================================

TOKEN = "ethereum:0x467719ad09025fcc6cf6f8311755809d45a5e5f3"

BASE_URL = "https://coins.llama.fi/chart"

START = int(datetime(2015, 1, 1).timestamp())
END = int(time())

# =====================================================
# Request
# =====================================================

url = f"{BASE_URL}/{TOKEN}"

params = {
    "start": START,
    "end": END,
    "period": "1d"
}

print("=" * 80)
print("Request URL:")
print(url)
print()

print("Parameters:")
print(params)
print("=" * 80)

response = requests.get(url, params=params)

print("\nHTTP Status Code:", response.status_code)

try:
    data = response.json()
except Exception:
    print("Response is not JSON.")
    print(response.text)
    raise

print("\nFull API Response:")
print(data)

# =====================================================
# Check response
# =====================================================

if "coins" not in data:
    raise Exception("API response does not contain 'coins' field.")

coins = data["coins"]

print("\nCoins returned by API:")
print(list(coins.keys()))

if TOKEN not in coins:

    print("\nRequested token:")
    print(TOKEN)

    raise Exception(
        "Requested token was not found in API response.\n"
        "See the list of returned keys above."
    )

# =====================================================
# Extract prices
# =====================================================

prices = coins[TOKEN]["prices"]

if len(prices) == 0:
    raise Exception("Price list is empty.")

df = pd.DataFrame(prices)

df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

df = df.sort_values("timestamp")

# =====================================================
# Summary
# =====================================================

print("\n")
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print("Symbol :", coins[TOKEN].get("symbol"))

print("Decimals :", coins[TOKEN].get("decimals"))

print("Confidence :", coins[TOKEN].get("confidence"))

print("Number of observations :", len(df))

print("First date :", df["datetime"].min())

print("Last date :", df["datetime"].max())

print("Minimum price :", df["price"].min())

print("Maximum price :", df["price"].max())

print("Average price :", df["price"].mean())

# =====================================================
# Time intervals
# =====================================================

diffs = df["timestamp"].diff().dropna()

print("\nUnique time intervals:")

for d in np.sort(diffs.unique()):
    print(f"{int(d)} seconds  -->  {pd.to_timedelta(int(d), unit='s')}")

# =====================================================
# First rows
# =====================================================

print("\nFirst observations")

print(df.head())

print("\nLast observations")

print(df.tail())
