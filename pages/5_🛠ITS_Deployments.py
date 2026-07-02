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
st.title("🛠 ITS Token Deployments")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

st.markdown("""
<style>
.card {
    background: linear-gradient(135deg, #ddefd4, #1e293b);
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    color: #ffffff;
    font-size: 16px;
    line-height: 1.8;
    border: 1px solid rgba(255,255,255,0.08);
}

.card a {
    color: #38bdf8;
    font-weight: 600;
    text-decoration: none;
    border-bottom: 1px dashed #38bdf8;
    transition: 0.2s;
}

.card a:hover {
    color: #0ea5e9;
    border-bottom: 1px solid #0ea5e9;
}
</style>

<div class="card">
    For token deployments using Interchain Token Service (ITS), you can visit 
    <a href="https://interchain.axelar.dev/" target="_blank">here</a>
    .
</div>
""", unsafe_allow_html=True)
# ------ SIDEBAR ---------

st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px; # -- MOVE LEFT
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


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_deployments():

    session = requests.Session()

    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    session.mount("https://", HTTPAdapter(max_retries=retry))

    response = session.get(API_URL, timeout=60)
    response.raise_for_status()

    return response.json()["data"]


try:

    # Load data (cached)
    data = load_deployments()

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
    df = (
        df.sort_values(by="timestamp", ascending=False)
          .drop(columns=["timestamp"])
    )

    # Display Date
    df["Deployment Date"] = df["Deployment Date"].dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    st.subheader("📃Deployed Tokens Sorted by Deployment Time")

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

# =====================================================
# TOKEN DEPLOYMENTS CHART
# =====================================================

st.markdown("##### Please select your desired time range:")
col1, col2, col3 = st.columns([1,1,2])

with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["Month", "Week", "Day"],
        index=0
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        value=pd.Timestamp("2024-01-01").date()
    )

with col3:
    end_date = st.date_input(
        "End Date",
        value=pd.Timestamp.utcnow().date()
    )

# -----------------------------------------------------
# Prepare dataframe
# -----------------------------------------------------
st.subheader("Token Deployments Over Time")
chart_df = pd.DataFrame(data)

chart_df["Deployment Date"] = pd.to_datetime(
    chart_df["timestamp"],
    unit="s",
    utc=True
).dt.tz_localize(None)

# Filter dates
chart_df = chart_df[
    (chart_df["Deployment Date"] >= pd.Timestamp(start_date))
    &
    (chart_df["Deployment Date"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))
]

# Grouping
if timeframe == "Day":

    chart_df["Period"] = chart_df["Deployment Date"].dt.strftime("%Y-%m-%d")

elif timeframe == "Week":

    chart_df["Period"] = (
        chart_df["Deployment Date"]
        .dt.to_period("W")
        .astype(str)
    )

else:

    chart_df["Period"] = (
        chart_df["Deployment Date"]
        .dt.strftime("%Y-%m")
    )

# Count unique Token IDs
deployments = (
    chart_df
    .groupby("Period")["tokenID"]
    .nunique()
    .reset_index(name="Deployments")
)

# Plot
fig = px.bar(
    deployments,
    x="Period",
    y="Deployments",
    text="Deployments"
)

fig.update_layout(

    template="plotly_dark",

    height=450,

    xaxis_title="",

    yaxis_title="Unique Token Deployments",

    margin=dict(
        l=20,
        r=20,
        t=20,
        b=20
    ),

    showlegend=False
)

fig.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig,
    use_container_width=True
)
# =====================================================
# KPI CARDS
# =====================================================

# Total Deployments
total_deployments = len(chart_df)

# Total Unique Tokens
total_unique_tokens = chart_df["tokenID"].nunique()

# Active Chains
active_chains = chart_df["chain"].nunique()

# Average Chains per Token
avg_chains_per_token = (
    chart_df
    .groupby("tokenID")["chain"]
    .nunique()
    .mean()
)

if pd.isna(avg_chains_per_token):
    avg_chains_per_token = 0

# Latest Deployment 
if len(chart_df) > 0:
    latest_deployment = (
        chart_df["Deployment Date"]
        .max()
        .strftime("%Y-%m-%d")
    )
else:
    latest_deployment = "-"


# =====================================================
# Deployments (Last 30 Days)
# =====================================================

all_df = pd.DataFrame(data)

all_df["Deployment Date"] = pd.to_datetime(
    all_df["timestamp"],
    unit="s",
    utc=True
).dt.tz_localize(None)

today = pd.Timestamp.utcnow().tz_localize(None)
last_30_days = today - pd.Timedelta(days=30)

deployments_30d = (
    all_df[
        all_df["Deployment Date"] >= last_30_days
    ]["tokenID"]
    .nunique()
)


# =====================================================
# SHOW KPIs
# =====================================================

row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    st.metric(
        "Total Deployments",
        f"{total_deployments:,}"
    )

with row1_col2:
    st.metric(
        "Total Unique Tokens",
        f"{total_unique_tokens:,}"
    )

with row1_col3:
    st.metric(
        "Active Chains",
        active_chains
    )


row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    st.metric(
        "Average Chains / Token",
        f"{avg_chains_per_token:.2f}"
    )

with row2_col2:
    st.metric(
        "Latest Deployment",
        latest_deployment
    )

with row2_col3:
    st.metric(
        "Deployments (Last 30 Days)",
        f"{deployments_30d:,}"
    )
# =====================================================
# STACKED BAR CHARTS
# =====================================================

stack_df = chart_df.copy()

stack_df = stack_df.drop_duplicates(
    subset=["tokenID", "chain"]
)

if timeframe == "Day":

    stack_df["Period"] = stack_df["Deployment Date"].dt.strftime("%Y-%m-%d")

elif timeframe == "Week":

    stack_df["Period"] = (
        stack_df["Deployment Date"]
        .dt.to_period("W")
        .astype(str)
    )

else:

    stack_df["Period"] = (
        stack_df["Deployment Date"]
        .dt.strftime("%Y-%m")
    )

stack_summary = (
    stack_df
    .groupby(["Period", "chain"])["tokenID"]
    .nunique()
    .reset_index(name="Deployments")
)

col1, col2 = st.columns(2)

# ----------------------------------------------------
# Stacked Bar Chart
# ----------------------------------------------------

with col1:

    fig1 = px.bar(
        stack_summary,
        x="Period",
        y="Deployments",
        color="chain",
        barmode="stack",
        labels={
            "chain": "Chain",
            "Deployments": "Deployments"
        },
        title="Token Deployments by Chain"
    )

    fig1.update_layout(
        template="plotly_dark",
        height=450,
        legend_title="Chain",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

# ----------------------------------------------------
# Normalized Stacked Bar Chart
# ----------------------------------------------------

with col2:

    # Calculate percentage
    normalized = stack_summary.copy()

    normalized["Percentage"] = (
        normalized["Deployments"] /
        normalized.groupby("Period")["Deployments"].transform("sum")
    ) * 100

    fig2 = px.bar(
        normalized,
        x="Period",
        y="Percentage",
        color="chain",
        barmode="stack",
        labels={
            "chain": "Chain",
            "Percentage": "Percentage (%)"
        },
        title="Normalized Token Deployments by Chain"
    )

    fig2.update_layout(
        template="plotly_dark",
        height=450,
        legend_title="Chain",
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis=dict(
            range=[0, 100],
            ticksuffix="%"
        )
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# =====================================================
# CUMULATIVE + PIE
# =====================================================

col1, col2 = st.columns(2)

# -----------------------------------------------------
# Cumulative Deployments by Chain
# -----------------------------------------------------

with col1:

    cumulative_df = chart_df.copy()  
    cumulative_df = cumulative_df.drop_duplicates(
        subset=["tokenID", "chain"]
    )

    cumulative_df = cumulative_df.sort_values("Deployment Date")
    cumulative = (
        cumulative_df
        .groupby(["chain", "Deployment Date"])
        .size()
        .reset_index(name="Deployments")
    )

    cumulative["Cumulative"] = (
        cumulative
        .groupby("chain")["Deployments"]
        .cumsum()
    )

    fig = px.line(
        cumulative,
        x="Deployment Date",
        y="Cumulative",
        color="chain",
        title="Cumulative Token Deployments by Chain"
    )

    fig.update_layout(
        template="plotly_dark",
        height=450,
        xaxis_title="",
        yaxis_title="Cumulative Deployments",
        legend_title="Chain"
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------
# Pie Chart
# -----------------------------------------------------

with col2:

    pie_df = (
        chart_df
        .drop_duplicates(["tokenID", "chain"])
        .groupby("chain")["tokenID"]
        .nunique()
        .reset_index(name="Deployments")
        .sort_values("Deployments", ascending=False)
    )

    fig = px.pie(
        pie_df,
        values="Deployments",
        names="chain",
        hole=0.45,
        title="Share of Deployments by Chain"
    )

    fig.update_layout(
        template="plotly_dark",
        height=450
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label"
    )

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# UNIQUE TOKENS BY CHAIN
# =====================================================

unique_chain = (
    chart_df
    .drop_duplicates(["tokenID", "chain"])
    .groupby("chain")["tokenID"]
    .nunique()
    .reset_index(name="Unique Tokens")
    .sort_values("Unique Tokens", ascending=False)
)

fig = px.bar(
    unique_chain,
    x="chain",
    y="Unique Tokens",
    text="Unique Tokens",
    title="Unique Tokens Deployed by Chain"
)

fig.update_layout(
    template="plotly_dark",
    height=500,
    xaxis_title="Chain",
    yaxis_title="Unique Tokens"
)

fig.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# DISTRIBUTION OF TOKENS BY NUMBER OF CHAINS
# =====================================================

distribution = (
    chart_df
    .drop_duplicates(["tokenID", "chain"])
    .groupby("tokenID")["chain"]
    .nunique()
    .reset_index(name="Number of Chains")
)

distribution = (
    distribution
    .groupby("Number of Chains")
    .size()
    .reset_index(name="Tokens")
    .sort_values("Number of Chains")
)

distribution["Label"] = distribution["Number of Chains"].astype(str) + " Chain"

distribution.loc[
    distribution["Number of Chains"] > 1,
    "Label"
] = distribution["Number of Chains"].astype(str) + " Chains"

col1, col2 = st.columns(2)

# =====================================================
# DISTRIBUTION OF TOKENS BY NUMBER OF CHAINS
# =====================================================

distribution = (
    chart_df
    .drop_duplicates(["tokenID", "chain"])
    .groupby("tokenID")["chain"]
    .nunique()
    .reset_index(name="Chains")
)


def bucket(n):
    if n == 1:
        return "1 Chain"
    elif n == 2:
        return "2 Chains"
    elif 3 <= n <= 5:
        return "3–5 Chains"
    elif 6 <= n <= 10:
        return "6–10 Chains"
    elif 11 <= n <= 15:
        return "11–15 Chains"
    elif 16 <= n <= 20:
        return "16–20 Chains"
    else:
        return "20+ Chains"


distribution["Category"] = distribution["Chains"].apply(bucket)

bucket_order = [
    "1 Chain",
    "2 Chains",
    "3–5 Chains",
    "6–10 Chains",
    "11–15 Chains",
    "16–20 Chains",
    "20+ Chains"
]

bucket_df = (
    distribution
    .groupby("Category")
    .size()
    .reindex(bucket_order, fill_value=0)
    .reset_index(name="Tokens")
)

col1, col2 = st.columns(2)

# -----------------------------------------------------
# Donut Chart
# -----------------------------------------------------

with col1:

    fig = px.pie(
        bucket_df,
        names="Category",
        values="Tokens",
        hole=0.55,
        title="Distribution of Tokens by Number of Chains"
    )

    fig.update_layout(
        template="plotly_dark",
        height=450
    )

    fig.update_traces(
        textinfo="percent+label"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# -----------------------------------------------------
# Horizontal Bar
# -----------------------------------------------------

with col2:

    fig = px.bar(
        bucket_df.iloc[::-1],
        x="Tokens",
        y="Category",
        orientation="h",
        text="Tokens",
        title="Distribution of Tokens by Number of Chains"
    )

    fig.update_layout(
        template="plotly_dark",
        height=450,
        xaxis_title="Tokens",
        yaxis_title=""
    )

    fig.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# EXACT DISTRIBUTION
# =====================================================

exact_distribution = (
    distribution
    .groupby("Chains")
    .size()
    .reset_index(name="Tokens")
    .sort_values("Chains")
)

fig = px.bar(
    exact_distribution,
    x="Chains",
    y="Tokens",
    text="Tokens",
    title="Exact Distribution of Tokens by Number of Chains"
)

fig.update_layout(
    template="plotly_dark",
    height=500,
    xaxis_title="Number of Chains",
    yaxis_title="Number of Tokens"
)

fig.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig,
    use_container_width=True
)
# =====================================================
# ALL-TIME TOKENS BY NUMBER OF CHAINS
# (NOT AFFECTED BY DATE FILTERS)
# =====================================================

st.subheader("All-Time Tokens by Number of Chains")
st.caption("This table is not affected by the selected date range.")

all_tokens = pd.DataFrame(data)
all_tokens = all_tokens.drop_duplicates(
    subset=["tokenID", "chain"]
)
 
token_summary = (
    all_tokens
    .groupby("tokenID")
    .agg(
        Symbol=("symbol", "first"),
        Name=("name", "first"),
        Number_of_Chains=("chain", "nunique"),
        Chains=("chain", lambda x: ", ".join(sorted(x.unique())))
    )
    .reset_index()
)

token_summary.rename(
    columns={
        "tokenID": "Token_ID"
    },
    inplace=True
)

token_summary = token_summary.sort_values(
    by=["Number_of_Chains", "Symbol"],
    ascending=[False, True]
).reset_index(drop=True)

st.dataframe(
    token_summary,
    use_container_width=True,
    hide_index=True,
    height=700,
    column_config={
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
        "Number_of_Chains": st.column_config.NumberColumn(
            "Number of Chains",
            format="%d",
            width="small"
        ),
        "Chains": st.column_config.TextColumn(
            "Chains",
            width="large"
        ),
    }
)
