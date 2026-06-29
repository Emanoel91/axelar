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
import plotly.graph_objects as go

# ==================================================
# Configuration
# ==================================================

TOKEN = "ethereum:0x467719ad09025fcc6cf6f8311755809d45a5e5f3"
URL = f"https://coins.llama.fi/chart/{TOKEN}"

# شروع از 500 روز قبل
start_date = datetime.utcnow() - timedelta(days=500)
start_timestamp = int(start_date.timestamp())

params = {
    "start": start_timestamp,
    "period": "1d",
    "span": 500
}

# ==================================================
# Fetch Data
# ==================================================

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

data = response.json()

if "coins" not in data or TOKEN not in data["coins"]:
    st.error(data)
    st.stop()

prices = data["coins"][TOKEN]["prices"]

if len(prices) == 0:
    st.error("No data returned from API.")
    st.stop()

df = pd.DataFrame(prices)

df["date"] = pd.to_datetime(df["timestamp"], unit="s")
df = df.sort_values("date")

# ==================================================
# Plot
# ==================================================

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["price"],
        mode="lines",
        name="AXL",
        line=dict(width=2, color="#000000")
    )
)

fig.update_layout(
    title=dict(
        text="AXL Daily Price (Last 500 Days)",
    ),
    template="plotly_white",
    height=600,
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title="Price (USD)"
)

st.plotly_chart(fig, use_container_width=True)


# ==================================================
# AXL Price KPIs
# ==================================================

st.markdown("### 💎 AXL Price Key Performance Indicators")

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

# ==================================================
# Calculate KPIs
# ==================================================

current_price = df["price"].iloc[-1]

max_price = df["price"].max()
min_price = df["price"].min()
avg_price = df["price"].mean()

# درصد تغییر نسبت به مرجع
def pct_change(current, reference):
    return (current - reference) / reference * 100

current_vs_max = pct_change(current_price, max_price)
current_vs_min = pct_change(current_price, min_price)
current_vs_avg = pct_change(current_price, avg_price)

# بازده تاریخی
def historical_return(days):

    if len(df) <= days:
        return None

    old_price = df["price"].iloc[-(days + 1)]

    return (current_price - old_price) / old_price * 100

ret_1d = historical_return(1)
ret_7d = historical_return(7)
ret_30d = historical_return(30)

# ==================================================
# Helper for colored text
# ==================================================

def colored_percent(value):

    if value is None:
        return "-"

    color = "green" if value >= 0 else "red"

    return f":{color}[{value:.2f}%]"

# ==================================================
# Row 1
# ==================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "📈 Max Price",
        f"${max_price:.4f}"
    )

with col2:
    st.metric(
        "📉 Min Price",
        f"${min_price:.4f}"
    )

with col3:
    st.metric(
        "📊 Avg Price",
        f"${avg_price:.4f}"
    )

# ==================================================
# Row 2
# ==================================================

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("**🔻 Current vs Max**")
    st.markdown(f"## {colored_percent(current_vs_max)}")

with col5:
    st.markdown("**🔺 Current vs Min**")
    st.markdown(f"## {colored_percent(current_vs_min)}")

with col6:
    st.markdown("**⚖️ Current vs Avg**")
    st.markdown(f"## {colored_percent(current_vs_avg)}")

# ==================================================
# Row 3
# ==================================================

col7, col8, col9 = st.columns(3)

with col7:
    st.markdown("**🕒 24h Change**")
    st.markdown(f"## {colored_percent(ret_1d)}")

with col8:
    st.markdown("**📅 7d Change**")
    st.markdown(f"## {colored_percent(ret_7d)}")

with col9:
    st.markdown("**🗓️ 30d Change**")
    st.markdown(f"## {colored_percent(ret_30d)}")
