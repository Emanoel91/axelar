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
from datetime import datetime
import numpy as np

# -----------------------------
# تنظیمات
# -----------------------------
TOKEN = "ethereum:0x467719ad09025fcc6cf6f8311755809d45a5e5f3"
BASE_URL = "https://coins.llama.fi/chart"

# از سال 2015 شروع می‌کنیم تا مطمئن باشیم همه داده‌ها را می‌گیریم
START = int(datetime(2015, 1, 1).timestamp())

# -----------------------------
# دریافت داده
# -----------------------------
url = f"{BASE_URL}/{TOKEN}"

params = {
    "start": START,
    "period": "1d"
}

response = requests.get(url, params=params)
response.raise_for_status()

data = response.json()

prices = data["coins"][TOKEN]["prices"]

df = pd.DataFrame(prices)

df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

print("=" * 60)
print("Token:", TOKEN)
print("=" * 60)

# -----------------------------
# اطلاعات کلی
# -----------------------------
print(f"Number of data points : {len(df)}")

print(f"First timestamp       : {df['datetime'].min()}")

print(f"Last timestamp        : {df['datetime'].max()}")

print(f"Min price             : {df['price'].min():.6f}")

print(f"Max price             : {df['price'].max():.6f}")

# -----------------------------
# بررسی فاصله زمانی
# -----------------------------
df = df.sort_values("timestamp")

diffs = df["timestamp"].diff().dropna()

unique_diffs = np.sort(diffs.unique())

print("\nUnique time intervals (seconds):")

print(unique_diffs)

print("\nUnique time intervals (human readable):")

for d in unique_diffs:
    print(f"{int(d):>8} sec = {pd.to_timedelta(int(d), unit='s')}")

# -----------------------------
# تست periodهای مختلف
# -----------------------------
print("\n")
print("=" * 60)
print("Testing supported periods")
print("=" * 60)

periods = [
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "12h",
    "1d",
    "7d",
    "1w"
]

for period in periods:

    try:

        params = {
            "start": START,
            "period": period,
            "span": 10
        }

        r = requests.get(url, params=params)

        if r.status_code != 200:
            print(f"{period:>5} --> ERROR ({r.status_code})")
            continue

        js = r.json()

        p = js["coins"][TOKEN]["prices"]

        print(f"{period:>5} --> OK ({len(p)} points)")

    except Exception as e:
        print(f"{period:>5} --> FAILED ({e})")
