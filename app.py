import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ---------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------
@st.cache_data
def load_features():
    file_path = Path("processed_data/features_master.csv")
    if not file_path.exists():
        st.error("⚠️ features_master.csv not found. Run features.py first.")
        st.stop()
    df = pd.read_csv(file_path, dtype={"zip": str}, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

df = load_features()

# ---------------------------------------------------------
# 2. Sidebar filters
# ---------------------------------------------------------
st.sidebar.header("🔍 Filters")
zip_list = sorted(df["zip"].dropna().unique())
selected_zips = st.sidebar.multiselect("Select ZIP(s)", zip_list, default=zip_list[:3])

date_min = df["date"].min().to_pydatetime()
date_max = df["date"].max().to_pydatetime()

date_range = st.sidebar.slider(
    "Select Date Range",
    min_value=date_min,
    max_value=date_max,
    value=(date_min, date_max)
)

filtered_df = df[df["zip"].isin(selected_zips)]
filtered_df = filtered_df[(filtered_df["date"] >= date_range[0]) & (filtered_df["date"] <= date_range[1])]

# ---------------------------------------------------------
# 3. Headline metrics
# ---------------------------------------------------------
st.title("🏠 Real-World Real Estate Analytics Dashboard")
st.caption("Interactive volatility & risk visualization")

# --- Dynamically recompute rolling volatility and risk for visible window ---
# Grouped volatility (per ZIP) within the date range

grouped = filtered_df.groupby("zip")["price"]
sigma_by_zip = grouped.std() / grouped.mean()
sigma_by_zip = sigma_by_zip[sigma_by_zip.notna()]  # drop empty groups

# Average price within the range
avg_price = filtered_df["price"].mean()

# Aggregate across selected ZIPs
avg_volatility = sigma_by_zip.mean()

# Recompute risk index dynamically (you can adjust weighting)
avg_risk = (avg_volatility * 200).clip(0, 100)  # Simple normalization for visual range




col1, col2, col3 = st.columns(3)
col1.metric("💰 Average Price", f"${avg_price:,.0f}")
col2.metric("📈 Volatility (σ)", f"{avg_volatility:.2f}")
col3.metric("⚠️ Risk Index", f"{avg_risk:.1f}")

st.markdown("---")

# ---------------------------------------------------------
# 4a. Visualizations
# ---------------------------------------------------------

# Price trend
st.subheader("📊 Price Trend Over Time")
fig_price = px.line(filtered_df, x="date", y="price", color="zip", title="Quarterly Price Trend by ZIP")
st.plotly_chart(fig_price, use_container_width=True)

# ---------------------------------------------------------
# 4b. Volatility trend visualization (optional)
# ---------------------------------------------------------
st.subheader("📉 Volatility (σ) Over Time")

# If rolling volatility exists in your dataset (features_master.csv)
if "volatility" in filtered_df.columns:
    fig_vol = px.line(
        filtered_df,
        x="date",
        y="volatility",
        color="zip",
        title="Rolling Volatility (σ) by ZIP — 8-Quarter Window",
        markers=True
    )
    fig_vol.update_traces(mode="lines+markers", hovertemplate="%{x|%b %Y}: σ=%{y:.2f}")
    st.plotly_chart(fig_vol, use_container_width=True)
else:
    st.info("ℹ️ Volatility column not found in dataset. Run features.py first.")

# ---------------------------------------------------------
# 4c. Financial Volatility (σ_returns)
# ---------------------------------------------------------
st.subheader("📉 Market Stress (σ₍returns₎) Over Time")

if "volatility_returns" in filtered_df.columns:
    fig_volret = px.line(
        filtered_df,
        x="date",
        y="volatility_returns",
        color="zip",
        title="Volatility of Returns (σ₍returns₎) — Capturing Market Turbulence",
        markers=True
    )
    st.plotly_chart(fig_volret, use_container_width=True)
else:
    st.info("ℹ️ 'volatility_returns' not found. Run features.py first.")


# Volatility vs Risk
st.subheader("⚖️ Volatility vs Risk Index")
fig_scatter = px.scatter(
    filtered_df,
    x="volatility",
    y="risk_index",
    color="zip",
    hover_name="zip",
    size="price",
    title="Risk Index vs Volatility"
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Risk Index distribution
st.subheader("📉 Risk Index Distribution")
fig_bar = px.histogram(filtered_df, x="risk_index", nbins=30, title="Distribution of Risk Index")
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# 5. Footer
# ---------------------------------------------------------
st.markdown("---")
st.caption("Built with ❤️ using Streamlit, Plotly, and pandas.")
