import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from sklearn.linear_model import LinearRegression
import numpy as np
import requests

st.set_page_config(page_title="Market Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stSidebarNav"] a {
    color: white !important;
    font-size: 15px !important;
    font-weight: 400 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: white !important;
    font-weight: 600 !important;
}
[data-testid="stSidebarNav"] li:first-child a {
    letter-spacing: 0.03em !important;
    font-size: 19px !important;
    font-weight: 700 !important;
    color: white !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🔐 PASSWORD GATE
# ---------------------------------------------------------
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "pw_error" not in st.session_state:
    st.session_state.pw_error = False

if not st.session_state.authenticated:
    st.title("🏡 RealEstate-Analytics.ai")
    st.markdown("#### Market Analytics & Deal Analyzer")
    if st.session_state.pw_error:
        st.error("❌ Incorrect password. Please try again.")
        st.session_state.pw_error = False
    password = st.text_input("🔒 Please enter access password", type="password")
    if st.button("Unlock"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.session_state.pw_error = True
            st.rerun()
    st.stop()

# ---------------------------------------------------------
ZILLOW_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
CACHE_FILE = Path("raw_data/zillow_full_cache.csv")

@st.cache_data(show_spinner="Loading Zillow data once...")
def load_full_zillow():
    if not CACHE_FILE.exists():
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(ZILLOW_URL, stream=True)
        with open(CACHE_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return pd.read_csv(CACHE_FILE, dtype={"RegionName": str})

def get_zip_data(df, zipcode):
    row = df[df["RegionName"] == zipcode]
    if row.empty:
        return None, None, None
    date_cols = [c for c in df.columns if c.startswith("20")]
    series = pd.Series(row.iloc[0][date_cols].values.astype(float), index=pd.to_datetime(date_cols))
    return series, row.iloc[0].get("City", "Unknown"), row.iloc[0].get("State", "")

def market_signal(city, state, yoy_pct):
    if yoy_pct > 5:
        temp, color = "hot seller's", "#0F6E56"
    elif yoy_pct > 1:
        temp, color = "warm seller's", "#185FA5"
    elif yoy_pct > -1:
        temp, color = "stagnating", "#854F0B"
    else:
        temp, color = "cooling buyer's", "#A32D2D"
    direction = "advance" if yoy_pct >= 0 else "decline"
    signal = f"**{city}, {state}** is a **{temp} market** with **{abs(yoy_pct):.1f}% YoY price {direction}**"
    return signal, color

st.sidebar.header("📍 Market Explorer")
zip_input = st.sidebar.text_input("Enter ZIP Code", value="94526", max_chars=5)
st.sidebar.markdown("---")
st.sidebar.header("📅 Date Range")

full_df = load_full_zillow()
zhvi, city, state = get_zip_data(full_df, zip_input.strip())

if zhvi is None:
    st.error(f"ZIP code {zip_input} not found. Try another ZIP.")
    st.stop()

st.sidebar.success(f"📍 {city}, {state}")
min_year = int(zhvi.index.year.min())
max_year = int(zhvi.index.year.max())
start_year = st.sidebar.slider("Start Year", min_year, max_year, 2015)
end_year = st.sidebar.slider("End Year", min_year, max_year, max_year)
forecast_months = st.sidebar.slider("Forecast Horizon (months)", 3, 24, 12)

filtered = zhvi[(zhvi.index.year >= start_year) & (zhvi.index.year <= end_year)]
if filtered.empty:
    st.error("No data for selected date range.")
    st.stop()

current_value = filtered.iloc[-1]
try:
    one_yr = zhvi[zhvi.index <= filtered.index[-1] - pd.DateOffset(years=1)].iloc[-1]
    yoy_change = ((current_value - one_yr) / one_yr) * 100
except:
    yoy_change = 0.0
try:
    five_yr = zhvi[zhvi.index <= filtered.index[-1] - pd.DateOffset(years=5)].iloc[-1]
    five_yr_change = ((current_value - five_yr) / five_yr) * 100
except:
    five_yr_change = 0.0

st.title(f"🏡 {city}, {state} — Market Analytics Dashboard")
st.caption(f"ZIP Code {zip_input} | Source: Zillow Research (ZHVI) | {min_year}–{max_year}")

signal_text, sig_color = market_signal(city, state, yoy_change)
st.markdown(f"""<div style="background:{sig_color}22; border-left:4px solid {sig_color};
padding:12px 16px; border-radius:6px; margin-bottom:1rem; font-size:15px;">{signal_text}</div>""",
unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Median Value", f"${current_value:,.0f}")
col2.metric("1-Year Change", f"{yoy_change:+.1f}%")
col3.metric("5-Year Change", f"{five_yr_change:+.1f}%")
col4.metric("All-Time High", f"${zhvi.max():,.0f}")
col5.metric("All-Time Low", f"${zhvi.min():,.0f}")

st.markdown("---")
st.subheader(f"📈 Median Home Value Trend — {city} {zip_input}")
fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(x=filtered.index, y=filtered.values, mode="lines",
    line=dict(color="#1D9E75", width=2), fill="tozeroy", fillcolor="rgba(29,158,117,0.1)"))
fig_trend.update_layout(yaxis_tickformat="$,.0f", hovermode="x unified", height=360, margin=dict(t=20,b=40))
st.plotly_chart(fig_trend, use_container_width=True)

st.subheader(f"🔮 Price Forecast — Next {forecast_months} Months")
train = zhvi[zhvi.index >= zhvi.index[-1] - pd.DateOffset(years=5)].dropna()
if len(train) >= 6:
    X = np.arange(len(train)).reshape(-1,1)
    model = LinearRegression().fit(X, train.values)
    fX = np.arange(len(train), len(train)+forecast_months).reshape(-1,1)
    fdates = pd.date_range(start=train.index[-1]+pd.DateOffset(months=1), periods=forecast_months, freq="MS")
    fvals = model.predict(fX)
    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(x=train.index, y=train.values, mode="lines", name="Historical", line=dict(color="#1D9E75", width=2)))
    fig_fc.add_trace(go.Scatter(x=fdates, y=fvals, mode="lines+markers", name="Forecast", line=dict(color="#378ADD", width=2, dash="dash"), marker=dict(size=4)))
    fig_fc.update_layout(yaxis_tickformat="$,.0f", hovermode="x unified", height=340, margin=dict(t=20,b=40))
    st.plotly_chart(fig_fc, use_container_width=True)
    fc_end = fvals[-1]
    fc_chg = ((fc_end - current_value) / current_value) * 100
    c1, c2 = st.columns(2)
    c1.metric(f"Projected Value in {forecast_months} months", f"${fc_end:,.0f}", f"{fc_chg:+.1f}% from today")
    c2.metric("Monthly Appreciation (trend)", f"${model.coef_[0]:,.0f}/mo")

st.markdown("---")
st.subheader("📊 Year-over-Year Price Change (%)")
annual = zhvi.resample("YE").last()
yoy = annual.pct_change().dropna() * 100
yoy = yoy[(yoy.index.year >= start_year) & (yoy.index.year <= end_year)]
if not yoy.empty:
    colors = ["#1D9E75" if v >= 0 else "#E24B4A" for v in yoy.values]
    fig_yoy = go.Figure(go.Bar(x=yoy.index.year, y=yoy.values.round(1), marker_color=colors,
        text=[f"{v:+.1f}%" for v in yoy.values], textposition="outside"))
    fig_yoy.update_layout(height=340, margin=dict(t=20,b=40), yaxis=dict(ticksuffix="%"), xaxis=dict(tickmode="linear"))
    st.plotly_chart(fig_yoy, use_container_width=True)

st.markdown("---")
st.subheader("⚠️ Market Volatility (12-Month Rolling σ)")
vol = (zhvi.rolling(12).std() / zhvi.rolling(12).mean()) * 100
vol_f = vol[(vol.index.year >= start_year) & (vol.index.year <= end_year)].dropna()
if not vol_f.empty:
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=vol_f.index, y=vol_f.values.round(2), mode="lines",
        line=dict(color="#BA7517", width=2), fill="tozeroy", fillcolor="rgba(186,117,23,0.1)"))
    fig_vol.update_layout(height=300, margin=dict(t=20,b=40), yaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")
if zip_input.strip() == "94526":
    st.subheader("🏘️ Current Market Snapshot — Danville MLS (Apr 2026)")
    st.caption("Source: Amir MLS Report | Residential")
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Listings", "83")
    c2.metric("Pending Listings", "37")
    c3.metric("Recently Sold", "70")
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg List Price (Sold)", "$2,288,710")
    c2.metric("Median List Price (Sold)", "$2,172,500")
    c3.metric("Avg Days on Market", "11 days")
    c1, c2 = st.columns(2)
    c1.metric("Price Range (Sold)", "$1.2M – $5.7M")
    c2.metric("Avg Beds/Baths", "4 bed / 2.5 bath")
    st.markdown("---")

with st.expander("📋 View Raw Monthly Data"):
    st.dataframe(pd.DataFrame({"Date": filtered.index.strftime("%Y-%m"),
        "Median Home Value ($)": filtered.values.round(0).astype(int)}), use_container_width=True)

st.caption(f"Built with Streamlit + Zillow Research | RealEstate-Analytics.ai | {city}, {state} {zip_input} | v0.2")
