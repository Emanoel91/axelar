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

# =====================================================
# ITS TOKEN DEPLOYMENTS TABLE
# =====================================================

API_URL = "https://api.axelarscan.io/gmp/getITSTokenDeployments"

try:
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()

    data = response.json()["data"]

    df = pd.DataFrame(data)

    # Convert timestamp to datetime
    df["Deployment Date"] = pd.to_datetime(
        df["timestamp"],
        unit="s",
        utc=True
    ).dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Select required columns
    df = df.rename(columns={
        "chain": "Chain",
        "symbol": "Symbol",
        "name": "Name",
        "tokenID": "Token_ID"
    })

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

    # Sort by newest deployment
    df = df.sort_values("timestamp", ascending=False)

    # Remove helper column
    df = df.drop(columns=["timestamp"]).reset_index(drop=True)

    st.subheader("ITS Token Deployments")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Error loading deployment data: {e}")
