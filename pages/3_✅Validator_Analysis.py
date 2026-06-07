import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Validator Analysis",
    page_icon="🛡️",
    layout="wide"
)

# =====================================================
# TITLE + DESCRIPTION
# =====================================================

st.title("🛡️ Validator Analysis")

st.markdown(
    """
### What is Uptime?
Uptime represents how often a validator is included in consensus snapshots.
Higher uptime means better reliability, fewer missed blocks, and stronger network participation.
"""
)

st.info(
    "Data is sourced from Axelar validator uptime snapshots."
)

# =====================================================
# SIDEBAR
# =====================================================
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
# LOAD DATA
# =====================================================

@st.cache_data(ttl=300)
def load_uptime():

    url = "https://api.axelarscan.io/validator/searchUptimes"

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    data = r.json().get("data", [])

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Safe timestamp conversion
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()]
    df = df[df["timestamp"] > 0]

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        errors="coerce"
    )

    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp")

    return df


df = load_uptime()

if df.empty:
    st.error("No validator uptime data available.")
    st.stop()

# =====================================================
# VALIDATOR STATS
# =====================================================

all_validators = sorted({v for lst in df["validators"] for v in lst})

total_snapshots = len(df)

records = []

for v in all_validators:

    appearances = df["validators"].apply(lambda x: v in x).sum()
    misses = total_snapshots - appearances

    uptime = (appearances / total_snapshots * 100) if total_snapshots else 0

    records.append({
        "validator": v,
        "appearances": appearances,
        "misses": misses,
        "uptime": uptime
    })

stats_df = pd.DataFrame(records)

# =====================================================
# METRICS BASE VALUES
# =====================================================

active_df = df.copy()
active_df["active_count"] = active_df["validators"].apply(len)

avg_active = active_df["active_count"].mean()

best_uptime = stats_df["uptime"].max()
worst_uptime = stats_df["uptime"].min()
avg_uptime = stats_df["uptime"].mean()

# =====================================================
# KPI FUNCTION (ARC STYLE TOOLTIP)
# =====================================================

def kpi(label, description):
    return f"{label}", description

# =====================================================
# KPI ROW
# =====================================================

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    label, help_text = kpi("Validators", "Total unique validators observed in snapshots")
    st.metric(label, f"{len(stats_df):,}", help=help_text)

with col2:
    label, help_text = kpi("Snapshots", "Number of block snapshots analyzed")
    st.metric(label, f"{total_snapshots:,}", help=help_text)

with col3:
    label, help_text = kpi("Avg Active", "Average number of validators active per snapshot")
    st.metric(label, f"{avg_active:.1f}", help=help_text)

with col4:
    label, help_text = kpi("Best Uptime", "Highest uptime among all validators")
    st.metric(label, f"{best_uptime:.2f}%", help=help_text)

with col5:
    label, help_text = kpi("Worst Uptime", "Lowest uptime among all validators")
    st.metric(label, f"{worst_uptime:.2f}%", help=help_text)

with col6:
    label, help_text = kpi("Average Uptime", "Average uptime across all validators")
    st.metric(label, f"{avg_uptime:.2f}%", help=help_text)

st.divider()

# =====================================================
# CHARTS ROW 1
# =====================================================

col1, col2 = st.columns(2)

with col1:

    fig = px.line(
        active_df,
        x="timestamp",
        y="active_count",
        title="Active Validators Over Time"
    )

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

with col2:

    fig = px.histogram(
        stats_df,
        x="uptime",
        nbins=25,
        title="Validator Uptime Distribution"
    )

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ROW 2 (NETWORK HEALTH + MISSES)
# =====================================================

col1, col2 = st.columns(2)

with col1:

    health_df = active_df.copy()

    max_active = health_df["active_count"].max()

    health_df["health_score"] = (
        health_df["active_count"] / max_active * 100
        if max_active else 0
    )

    fig = px.area(
        health_df,
        x="timestamp",
        y="health_score",
        title="Network Health Score (%)"
    )

    fig.update_layout(height=450)

    st.plotly_chart(fig, use_container_width=True)

with col2:

    top_miss = stats_df.sort_values("misses", ascending=False).head(20)

    fig = px.bar(
        top_miss,
        x="misses",
        y="validator",
        orientation="h",
        title="Top 20 Validators by Miss Count"
    )

    fig.update_layout(height=450)

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# RANKING TABLE
# =====================================================

st.subheader("Validator Ranking")

ranking = stats_df.sort_values("uptime", ascending=False).reset_index(drop=True)
ranking.index += 1

st.dataframe(ranking, use_container_width=True, height=600)

# ===========================================================================Part II=========================================================================
# =====================================================
# PROPOSED BLOCKS ANALYSIS (NEW API)
# =====================================================

PROPOSED_BLOCKS_API = "https://api.axelarscan.io/validator/searchProposedBlocks"

@st.cache_data(ttl=300)
def load_proposed_blocks():

    r = requests.get(PROPOSED_BLOCKS_API, timeout=60)
    r.raise_for_status()

    data = r.json().get("data", [])

    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp")

    return df


prop_df = load_proposed_blocks()

if not prop_df.empty:

    # =====================================================
    # TIME RANGE INFO
    # =====================================================

    st.subheader("📦 Proposed Blocks Overview")

    start_time = prop_df["timestamp"].min()
    end_time = prop_df["timestamp"].max()

    st.info(
        f"""
        📅 Data Time Range:
        From **{start_time}**  
        To **{end_time}**  
        Total span: **{(end_time - start_time).days} days**
        """
    )

    # =====================================================
    # KPI CALCULATIONS
    # =====================================================

    total_blocks = len(prop_df)
    unique_proposers = prop_df["proposer"].nunique()

    proposer_counts = (
        prop_df["proposer"]
        .value_counts()
        .reset_index()
    )

    proposer_counts.columns = ["proposer", "blocks"]

    top_proposer_share = (
        proposer_counts["blocks"].iloc[0] / total_blocks * 100
        if total_blocks else 0
    )

    avg_block_time = (
        prop_df["timestamp"]
        .diff()
        .mean()
    )

    # =====================================================
    # KPI ROW
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Blocks",
            f"{total_blocks:,}",
            help="Total number of proposed blocks in selected timeframe"
        )

    with col2:
        st.metric(
            "Unique Proposers",
            f"{unique_proposers:,}",
            help="Number of validators that proposed at least one block"
        )

    with col3:
        st.metric(
            "Avg Block Time",
            f"{avg_block_time.total_seconds():.2f} sec" if pd.notna(avg_block_time) else "N/A",
            help="Average time difference between consecutive blocks"
        )

    with col4:
        st.metric(
            "Top Proposer Share",
            f"{top_proposer_share:.2f}%",
            help="Share of blocks produced by top validator"
        )

    st.divider()

    # =====================================================
    # CHART 1: TOP PROPOSERS
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            proposer_counts.head(20),
            x="blocks",
            y="proposer",
            orientation="h",
            title="Top 20 Validators by Blocks Proposed"
        )

        fig.update_layout(height=600)

        st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # CHART 2: PIE DISTRIBUTION
    # =====================================================

    with col2:

        top10 = proposer_counts.head(10)

        fig = px.pie(
            top10,
            names="proposer",
            values="blocks",
            title="Block Proposer Share (Top 10)"
        )

        st.plotly_chart(fig, use_container_width=True)

# ===========================================================================Part III=======================================================================
# =====================================================
# HEARTBEATS ANALYSIS (NEW API)
# =====================================================

HEARTBEATS_API = "https://api.axelarscan.io/validator/searchHeartbeats"

@st.cache_data(ttl=300)
def load_heartbeats():

    r = requests.get(HEARTBEATS_API, timeout=60)
    r.raise_for_status()

    data = r.json().get("data", [])

    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()]

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp")

    return df


hb_df = load_heartbeats()

if not hb_df.empty:

    # =====================================================
    # TIME RANGE
    # =====================================================

    st.subheader("💓 Validator Heartbeats Overview")

    start_time = hb_df["timestamp"].min()
    end_time = hb_df["timestamp"].max()

    total_span = end_time - start_time

    st.info(
        f"""
📅 Heartbeat Data Range:
From **{start_time}**  
To **{end_time}**  
Total span: **{total_span.days} days**
        """
    )

    st.markdown(
    """
#### What is Heartbeats❓
Heartbeats are periodic messages sent by validators to indicate that they are active and online in the network.
Each validator sends a dedicated heartbeat transaction at specific intervals, which includes their signature and identifier. 
This transaction is recorded on the blockchain and shows that the validator is still available and operational.
If these messages are not sent or are interrupted, the network may consider the validator offline and potentially exclude it from participating in consensus.
"""
)

    # =====================================================
    # KPI CALCULATIONS
    # =====================================================

    total_heartbeats = len(hb_df)
    unique_senders = hb_df["sender"].nunique()

    sender_counts = (
        hb_df["sender"]
        .value_counts()
        .reset_index()
    )

    sender_counts.columns = ["sender", "heartbeats"]

    avg_heartbeat_per_sender = (
        total_heartbeats / unique_senders
        if unique_senders else 0
    )

    # time delta between heartbeats
    hb_df_sorted = hb_df.sort_values("timestamp")
    avg_heartbeat_interval = hb_df_sorted["timestamp"].diff().mean()

    # =====================================================
    # KPI ROW
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Heartbeats",
            f"{total_heartbeats:,}",
            help="Total number of heartbeat transactions submitted by validators"
        )

    with col2:
        st.metric(
            "Unique Validators",
            f"{unique_senders:,}",
            help="Number of validators that submitted at least one heartbeat"
        )

    with col3:
        st.metric(
            "Avg Heartbeats / Validator",
            f"{avg_heartbeat_per_sender:.2f}",
            help="Average heartbeat submissions per validator"
        )

    with col4:
        st.metric(
            "Avg Heartbeat Interval",
            f"{avg_heartbeat_interval.total_seconds():.2f} sec" if pd.notna(avg_heartbeat_interval) else "N/A",
            help="Average time between consecutive heartbeat submissions"
        )

    st.divider()

    # =====================================================
    # TABLE
    # =====================================================

    st.subheader("📋 Validator Heartbeat Ranking")

    st.dataframe(
        sender_counts,
        use_container_width=True,
        height=100
    )

else:
    st.warning("No heartbeat data available.")

# =====================================================================Part IV=================================================================
# =====================================================
# EVM POLLS ANALYSIS (UPDATED - FINAL)
# =====================================================

EVM_POLLS_API = "https://api.axelarscan.io/validator/searchEVMPolls"

@st.cache_data(ttl=300)
def load_evm_polls():

    r = requests.get(EVM_POLLS_API, timeout=60)
    r.raise_for_status()

    raw = r.json().get("data", [])

    rows = []

    for item in raw:

        for key, value in item.items():

            if isinstance(value, dict):

                rows.append({
                    "voter": value.get("voter"),
                    "vote": value.get("vote"),
                    "height": value.get("height"),
                    "type": value.get("type"),
                    "created_at": value.get("created_at"),
                    "confirmed": value.get("confirmed"),
                    "late": value.get("late"),
                })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["created_at"] = pd.to_numeric(df["created_at"], errors="coerce")
    df = df[df["created_at"].notna()]

    df["timestamp"] = pd.to_datetime(df["created_at"], unit="ms", errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df = df.sort_values("timestamp")

    return df


polls_df = load_evm_polls()

if not polls_df.empty:

    # =====================================================
    # TIME RANGE
    # =====================================================

    st.subheader("🗳️ EVM Polls Activity Overview")

    start_time = polls_df["timestamp"].min()
    end_time = polls_df["timestamp"].max()
    total_span = end_time - start_time

    st.info(
        f"""
📅 Data Time Range:
From **{start_time}**  
To **{end_time}**  
Total span: **{total_span.days} days**
        """
    )

    # =====================================================
    # KPI CALCULATIONS
    # =====================================================

    total_votes = len(polls_df)
    unique_voters = polls_df["voter"].nunique()

    vote_rate = polls_df["vote"].mean() * 100 if "vote" in polls_df else 0

    late_votes = polls_df["late"].sum() if "late" in polls_df else 0

    voter_activity = (
        polls_df["voter"]
        .value_counts()
        .reset_index()
    )

    voter_activity.columns = ["voter", "votes"]

    top_voter_share = (
        voter_activity["votes"].iloc[0] / total_votes * 100
        if total_votes else 0
    )

    # =====================================================
    # KPI ROW
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Votes",
            f"{total_votes:,}",
            help="Total number of votes submitted in EVM polls"
        )

    with col2:
        st.metric(
            "Unique Voters",
            f"{unique_voters:,}",
            help="Number of validators participating in voting"
        )

    with col3:
        st.metric(
            "Positive Vote Rate",
            f"{vote_rate:.2f}%",
            help="Share of approval votes (true)"
        )

    with col4:
        st.metric(
            "Late Votes",
            f"{late_votes:,}",
            help="Votes submitted after deadline"
        )

    st.divider()

    # =====================================================
    # CHARTS
    # =====================================================

    col1, col2 = st.columns(2)

    # -----------------------------------------------------
    # TOP VOTERS
    # -----------------------------------------------------
    with col1:

        fig = px.bar(
            voter_activity.head(20),
            x="votes",
            y="voter",
            orientation="h",
            title="Top 20 Validators by Votes"
        )

        fig.update_layout(height=550)

        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # VOTE DISTRIBUTION (FIXED)
    # -----------------------------------------------------
    with col2:

        # تعداد رأی هر voter
        voter_counts = (
            polls_df["voter"]
            .value_counts()
            .reset_index()
        )

        voter_counts.columns = ["voter", "votes"]

        # توزیع: چند validator چند رأی داده‌اند
        distribution = (
            voter_counts["votes"]
            .value_counts()
            .reset_index()
        )

        distribution.columns = ["vote_count", "num_validators"]

        distribution = distribution.sort_values("vote_count")

        fig = px.bar(
            distribution,
            x="vote_count",
            y="num_validators",
            title="Distribution of Votes per Validator",
            labels={
                "vote_count": "Number of Votes per Validator",
                "num_validators": "Number of Validators"
            }
        )

        fig.update_layout(height=550)

        st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # TIME SERIES
    # =====================================================

    st.subheader("📈 Voting Activity Over Time")

    time_df = polls_df.copy()
    time_df["date"] = time_df["timestamp"].dt.date

    daily_votes = (
        time_df.groupby("date")
        .size()
        .reset_index(name="votes")
    )

    fig = px.line(
        daily_votes,
        x="date",
        y="votes",
        title="Daily Voting Activity"
    )

    fig.update_layout(height=450)

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # TABLE
    # =====================================================

    st.subheader("📋 Voting Participation Table")

    st.dataframe(
        voter_activity,
        use_container_width=True,
        height=500
    )

else:
    st.warning("No EVM polls data available.")
