import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from st_aggrid import AgGrid, GridOptionsBuilder
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

    # -----------------------------
    # Requests Session + Retry
    # -----------------------------
    session = requests.Session()

    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry)
    )

    response = session.get(API_URL, timeout=60)
    response.raise_for_status()

    data = response.json()["data"]

    # -----------------------------
    # DataFrame
    # -----------------------------
    df = pd.DataFrame(data)

    # Convert timestamp
    df["Deployment Date"] = pd.to_datetime(
        df["timestamp"],
        unit="s",
        utc=True
    )

    # Rename columns
    df = df.rename(columns={
        "chain": "Chain",
        "symbol": "Symbol",
        "name": "Name",
        "tokenID": "Token_ID"
    })

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

    # Sort newest first
    df = df.sort_values(
        by="timestamp",
        ascending=False
    )

    # Remove helper column
    df = df.drop(columns=["timestamp"])

    # Format date
    df["Deployment Date"] = df["Deployment Date"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    # -----------------------------
    # Title
    # -----------------------------
    st.subheader("ITS Token Deployments")

    # -----------------------------
    # AGGRID
    # -----------------------------
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        floatingFilter=True,
    )

    gb.configure_pagination(
        paginationAutoPageSize=False,
        paginationPageSize=20,
    )

    gb.configure_grid_options(
        animateRows=True
    )

    # Column widths
    gb.configure_column(
        "Deployment Date",
        width=170
    )

    gb.configure_column(
        "Chain",
        width=110
    )

    gb.configure_column(
        "Symbol",
        width=110
    )

    gb.configure_column(
        "Name",
        width=220
    )

    gb.configure_column(
        "Token_ID",
        width=500
    )

    gridOptions = gb.build()

    AgGrid(
        df,
        gridOptions=gridOptions,
        height=700,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        allow_unsafe_jscode=True,
    )

except Exception as e:
    st.error(f"Error loading deployment data: {e}")
