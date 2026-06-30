import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="ITS Deployments",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>

.block-container{
    padding-top:2rem;
    padding-bottom:2rem;
}

[data-testid="metric-container"]{
    background:linear-gradient(145deg,#1c1c1c,#111111);
    border:1px solid rgba(255,255,255,0.05);
    padding:20px;
    border-radius:18px;
    box-shadow:0 4px 15px rgba(0,0,0,0.25);
    transition:0.25s ease;
}

[data-testid="metric-container"]:hover{
    transform:translateY(-4px);
    border:1px solid rgba(0,255,100,.35);
}

[data-testid="metric-container"] label{
    color:#9f9f9f !important;
    font-size:15px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"]{
    color:white;
    font-size:32px;
}

</style>
""", unsafe_allow_html=True)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================================================
# ITS TOKEN DEPLOYMENTS TABLE
# =====================================================

API_URL = "https://api.axelarscan.io/gmp/getITSTokenDeployments"

try:

    # Create Session
    session = requests.Session()

    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    session.mount("https://", HTTPAdapter(max_retries=retry))

    # Request
    response = session.get(API_URL, timeout=60)
    response.raise_for_status()

    data = response.json()["data"]

    # Create DataFrame
    df = pd.DataFrame(data)

    # Convert Timestamp
    df["Deployment Date"] = pd.to_datetime(
        df["timestamp"],
        unit="s",
        utc=True
    )

    # Rename columns
    df.rename(columns={
        "chain": "Chain",
        "symbol": "Symbol",
        "name": "Name",
        "tokenID": "Token_ID"
    }, inplace=True)

    # Keep required columns
    df = df[
        [
            "Deployment Date",
            "Chain",
            "Symbol",
            "Name",
            "Token_ID",
            "timestamp"
        ]
    ]

    # Sort by newest
    df = df.sort_values(
        by="timestamp",
        ascending=False
    ).drop(columns=["timestamp"])

    # Display Date
    df["Deployment Date"] = df["Deployment Date"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    st.subheader("ITS Token Deployments")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=700,
        column_config={
            "Deployment Date": st.column_config.TextColumn(
                "Deployment Date",
                width="medium"
            ),
            "Chain": st.column_config.TextColumn(
                "Chain",
                width="small"
            ),
            "Symbol": st.column_config.TextColumn(
                "Symbol",
                width="small"
            ),
            "Name": st.column_config.TextColumn(
                "Name",
                width="medium"
            ),
            "Token_ID": st.column_config.TextColumn(
                "Token ID",
                width="large"
            ),
        }
    )

except Exception as e:
    st.error(f"Error loading deployment data: {e}")
