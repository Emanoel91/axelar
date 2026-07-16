import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta, timezone

# -----------------------------
# Configuration
# -----------------------------

API_URL = "https://api.axelarscan.io/gmp/GMPTopUsers"

st.set_page_config(
    page_title="Axelar Daily Users",
    layout="wide"
)

st.title("📈 Axelar Daily Active Users")

# -----------------------------
# Sidebar
# -----------------------------

today = datetime.now(timezone.utc).date()

default_start = today - timedelta(days=60)

start_date = st.sidebar.date_input(
    "Start Date",
    default_start
)

end_date = st.sidebar.date_input(
    "End Date",
    today
)

# -----------------------------
# Function
# -----------------------------

@st.cache_data(show_spinner=False)
def get_daily_users(start_date, end_date):

    rows = []

    current = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    last = datetime.combine(
        end_date,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    progress = st.progress(0)

    total_days = (last-current).days + 1

    day_index = 0

    while current <= last:

        from_time = int(current.timestamp())

        to_time = int(
            (current + timedelta(days=1)).timestamp()
        ) - 1

        params = {
            "fromTime": from_time,
            "toTime": to_time
        }

        try:

            response = requests.get(
                API_URL,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            data = response.json().get("data", [])

            users = len(data)

            total_txs = sum(
                item.get("num_txs", 0)
                for item in data
            )

            total_volume = sum(
                item.get("volume", 0)
                for item in data
            )

        except Exception:

            users = 0
            total_txs = 0
            total_volume = 0

        rows.append({
            "Date": current.date(),
            "Users": users,
            "Transactions": total_txs,
            "Volume": total_volume
        })

        day_index += 1
        progress.progress(day_index / total_days)

        current += timedelta(days=1)

    progress.empty()

    return pd.DataFrame(rows)

# -----------------------------
# Load data
# -----------------------------

with st.spinner("Loading data from AxelarScan..."):

    df = get_daily_users(start_date, end_date)

# -----------------------------
# Metrics
# -----------------------------

c1, c2, c3 = st.columns(3)

c1.metric(
    "Total Users",
    f"{df.Users.sum():,}"
)

c2.metric(
    "Average Daily Users",
    f"{df.Users.mean():.1f}"
)

c3.metric(
    "Max Daily Users",
    f"{df.Users.max():,}"
)

st.divider()

# -----------------------------
# Daily Users Chart
# -----------------------------

fig = px.bar(
    df,
    x="Date",
    y="Users",
    title="Daily Active Users"
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Users",
    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# -----------------------------
# Table
# -----------------------------

st.subheader("Daily Data")

st.dataframe(
    df,
    use_container_width=True
)

# -----------------------------
# Download
# -----------------------------

csv = df.to_csv(index=False).encode()

st.download_button(
    "Download CSV",
    csv,
    "daily_users.csv",
    "text/csv"
)
