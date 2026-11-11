import pandas as pd
import plotly.express as px
import streamlit as st
import requests
import io
import os

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Master Dashboard",
    page_icon="https://axelarscan.io/logos/logo.png",
    layout="wide"
)

# ------ SIDEBAR ------

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
# --- Title ---
st.title("💰TVL Analysis")

st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Load API Data ---
@st.cache_data(ttl=3600)
def load_axelar_api():
    url = "https://api.axelarscan.io/api/getTVL"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch API data: {response.status_code}")
        return None


data = load_axelar_api()

# --- Parse API Data ---
if data and "data" in data:
    rows = []

    for asset in data["data"]:
        asset_id = asset.get("asset", "")
        price = asset.get("price", None)
        value = asset.get("value", None)
        asset_type = asset.get("assetType", "")
        abnormal = asset.get("is_abnormal_supply", False)

        tvl_data = asset.get("tvl", {})

        for chain, details in tvl_data.items():
            total_tvl = details.get("total", None)

            rows.append({
                "Asset ID": asset_id,
                "Asset Type": asset_type,
                "Chain": chain,
                "Token Symbol": details.get("contract_data", {}).get("symbol"),
                "Token Name": details.get("contract_data", {}).get("name"),
                "Contract Address": details.get("contract_data", {}).get("contract_address"),
                "Gateway Address": details.get("gateway_address", None),
                "Supply": details.get("supply", None),
                "Total TVL": total_tvl,
                "Price (USD)": price,
                "TVL (USD)": round(total_tvl * price, 0) if total_tvl and price else None,
                "Total Asset Value (USD)": value,
                "Is Abnormal?": abnormal
            })

    df = pd.DataFrame(rows)

    # --- Convert numeric columns ---
    numeric_cols = [
        "Supply",
        "Total TVL",
        "Price (USD)",
        "TVL (USD)",
        "Total Asset Value (USD)"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

else:
    st.warning("No data available from API.")


# --- Total TVL Calculation ---
unique_assets = df.drop_duplicates(subset=["Asset ID"])
total_axelar_tvl = unique_assets["Total Asset Value (USD)"].sum()


# --- AXL Price & Supply API ---
@st.cache_data(ttl=3600)
def load_axl_price_supply():
    try:
        # Price API
        price_url = "https://api.axelarscan.io/api/getTokensPrice?symbol=AXL"
        price_res = requests.get(price_url).json()
        axl_price = price_res["AXL"]["price"]

        # Supply API
        supply_url = "https://api.axelarscan.io/api/getTotalSupply"
        supply_res = requests.get(supply_url).json()
        axl_supply = float(supply_res)

        # FDV
        axl_fdv = axl_price * axl_supply

        return axl_price, axl_supply, axl_fdv

    except Exception as e:
        st.error(f"Error fetching AXL FDV data: {e}")
        return None, None, None


axl_price, axl_supply, axl_fdv = load_axl_price_supply()


# --- KPI Section ---
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"""
        <div style="background-color:#ffffff; padding:20px; border-radius:15px; text-align:center;">
            <h2 style="color:#fc9608; font-size:22px;">Total Axelar TVL (Latest update)</h2>
            <h1 style="color:#006ac9; font-size:48px;">${total_axelar_tvl:,.0f}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    if axl_fdv:
        st.markdown(
            f"""
            <div style="background-color:#ffffff; padding:20px; border-radius:15px; text-align:center;">
                <h2 style="color:#d17c00; font-size:22px;">AXL FDV (Fully Diluted Valuation)</h2>
                <h1 style="color:#ff7f50; font-size:48px;">${axl_fdv:,.0f}</h1>
                <p style="color:#444; font-size:16px;">
                    Price: ${axl_price:,.4f} | Supply: {axl_supply:,.0f}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


# -------------------------------------------------------------------
# --- Daily history (recorded once a day by scripts/record_tvl_snapshot.py) ---
HISTORY_URL = "https://raw.githubusercontent.com/Emanoel91/axelar/main/data/axelar_tvl_history.csv"
HISTORY_LOCAL = "data/axelar_tvl_history.csv"   # used when the GitHub URL cannot be read (e.g. private repo)


@st.cache_data(ttl=600)
def load_tvl_history():
    text = None
    try:
        res = requests.get(HISTORY_URL, timeout=30)
        if res.status_code == 200:
            text = res.text
    except Exception:
        pass
    if text is None and os.path.exists(HISTORY_LOCAL):
        with open(HISTORY_LOCAL, encoding="utf-8") as f:
            text = f.read()
    if text is None:
        return pd.DataFrame(columns=["date", "category", "name", "value"])

    h = pd.read_csv(io.StringIO(text))
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["value"] = pd.to_numeric(h["value"], errors="coerce")
    h = h.dropna(subset=["date", "value"])
    h = h.drop_duplicates(subset=["date", "category", "name"], keep="last")
    return h.sort_values("date").reset_index(drop=True)


history = load_tvl_history()
n_hist_days = history["date"].nunique() if not history.empty else 0

if n_hist_days < 2:
    st.info(
        f"📅 Daily history is recorded once a day and the charts over time need at least 2 recorded days. "
        f"Days recorded so far: {n_hist_days}."
    )


def show_area(category, title, color):
    d = history[history["category"] == category].sort_values("date")
    if d["date"].nunique() < 2:
        st.caption(f"{title}: waiting for at least 2 recorded days.")
        return
    fig = px.area(
        d,
        x="date",
        y="value",
        title=title,
        labels={"date": "Date", "value": "USD"},
        color_discrete_sequence=[color]
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def show_share_area(category, title, color_map=None, top_n=None, note=None):
    d = history[history["category"] == category]
    if d["date"].nunique() < 2:
        st.caption(f"{title}: waiting for at least 2 recorded days.")
        return

    pv = d.pivot_table(index="date", columns="name", values="value", aggfunc="last").fillna(0.0)
    pv.columns.name = None
    pv.index.name = "date"

    if top_n and pv.shape[1] > top_n:
        keep = list(pv.iloc[-1].sort_values(ascending=False).index[:top_n])
        other = pv.drop(columns=keep).sum(axis=1)
        pv = pv[keep].copy()
        pv["Other"] = other
        order = keep + ["Other"]
    else:
        order = list(pv.iloc[-1].sort_values(ascending=False).index)

    long_df = pv[order].reset_index().melt(id_vars="date", var_name="name", value_name="value")
    fig = px.area(
        long_df,
        x="date",
        y="value",
        color="name",
        groupnorm="percent",
        category_orders={"name": order},
        color_discrete_map=color_map,
        title=title,
        labels={"date": "Date", "value": "Share of TVL (%)", "name": ""}
    )
    fig.update_layout(yaxis_title="Share of TVL (%)")
    st.plotly_chart(fig, use_container_width=True)
    if note:
        st.caption(note)


# --- TVL & FDV Over Time ---
col1, col2 = st.columns(2)

with col1:
    show_area("total_tvl", "Total Axelar TVL Over Time", "#006ac9")

with col2:
    show_area("fdv", "AXL FDV Over Time", "#ff7f50")


# --- Prepare Asset Type Pie Chart ---
asset_type_df = unique_assets.copy()

asset_type_df["Asset Type Label"] = asset_type_df["Asset Type"].apply(
    lambda x: "ITS" if str(x).lower() == "its" else "non-ITS"
)

asset_type_summary = asset_type_df.groupby(
    "Asset Type Label",
    as_index=False
)["Total Asset Value (USD)"].sum()

fig_asset_type = px.pie(
    asset_type_summary,
    values="Total Asset Value (USD)",
    names="Asset Type Label",
    hole=0.5,
    color="Asset Type Label",
    color_discrete_map={"ITS": "#0ed145", "non-ITS": "#f8f17d"},
    title="Share of TVL by Asset Type"
)

fig_asset_type.update_traces(textposition="inside", textinfo="percent+label")
fig_asset_type.update_layout(showlegend=True)


# --- TVL per Chain ---
df["TVL (USD)"] = (df["Total TVL"] * df["Price (USD)"]).round(0)

chain_summary = df.groupby("Chain", as_index=False)["TVL (USD)"].sum()

fig_chain = px.pie(
    chain_summary,
    values="TVL (USD)",
    names="Chain",
    hole=0.5,
    title="Share of TVL by Chain"
)

fig_chain.update_traces(textposition="inside", textinfo="percent+label")
fig_chain.update_layout(showlegend=True)


# --- Display Pie Charts ---
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig_asset_type, use_container_width=True)

with col2:
    st.plotly_chart(fig_chain, use_container_width=True)


# --- Share of TVL by Asset Type Over Time ---
show_share_area(
    "asset_type",
    "Share of TVL by Asset Type Over Time",
    color_map={"ITS": "#0ed145", "non-ITS": "#f8f17d"}
)


# --- Share of TVL by Chain Over Time ---
show_share_area(
    "chain",
    "Share of TVL by Chain Over Time",
    top_n=10,
    note="Top 10 chains by their latest TVL are shown; all other chains are grouped as 'Other'."
)


# -------------------------------------------------------------------
# --- Chains API ---
@st.cache_data(ttl=3600)
def load_chains_api():
    url = "https://api.llama.fi/v2/chains"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch Chains API: {response.status_code}")
        return []


chains_data = load_chains_api()

chains_df = pd.DataFrame(chains_data)[["name", "tvl", "tokenSymbol"]]
chains_df.columns = ["Chain Name", "TVL (USD)", "Native Token Symbol"]

# Add Axelar manually
chains_df = pd.concat([
    chains_df,
    pd.DataFrame([{
        "Chain Name": "Axelar",
        "TVL (USD)": total_axelar_tvl,
        "Native Token Symbol": "AXL"
    }])
], ignore_index=True)

# Sort
chains_df = chains_df.sort_values("TVL (USD)", ascending=False).reset_index(drop=True)
chains_df.index = chains_df.index + 1

# --- Chain Ranking KPIs ---
axelar_rank = chains_df.index[chains_df["Chain Name"] == "Axelar"][0]
total_chains = len(chains_df)

# --- Chain Ranking KPIs ---

st.metric(
    label="🏆 Axelar TVL Rank",
    value=f"#{axelar_rank}",
    delta=f"Among {total_chains} tracked chains"
)

# --- Table ------------------------------------------------------
st.markdown("### ⛓TVL of Different Chains")

st.dataframe(
    chains_df.style.format({
        "TVL (USD)": "{:,.0f}"
    }),
    use_container_width=True
)


# -------------------------------------------------------------------
# --- Top 20 Chains Bar Chart ---
top_20_chains = chains_df.head(20).reset_index()


def human_format(num):
    if num >= 1e9:
        return f"{num/1e9:.1f}B"
    elif num >= 1e6:
        return f"{num/1e6:.1f}M"
    elif num >= 1e3:
        return f"{num/1e3:.1f}K"
    else:
        return str(int(num))


fig_bar = px.bar(
    top_20_chains,
    x="Chain Name",
    y="TVL (USD)",
    color="Chain Name",
    text=top_20_chains["TVL (USD)"].apply(human_format),
    title="Top 20 Chains by TVL ($USD)"
)

fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(
    xaxis_title="Chain",
    yaxis_title="$USD",
    showlegend=False,
    plot_bgcolor="white"
)

st.plotly_chart(fig_bar, use_container_width=True)
