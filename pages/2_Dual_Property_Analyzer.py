import streamlit as st
import os
import sys
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from email.message import EmailMessage
import smtplib
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from calc_engine import calculate_metrics
from pdf_dual import generate_pdf, generate_comparison_pdf_table_style, generate_ai_verdict

load_dotenv()
st.set_page_config(page_title="Dual Property Analyzer", layout="wide")
st.title("⚖️ Dual Property Analyzer")
st.markdown("Compare two investment properties side-by-side to optimize ROI, cash flow, and equity growth.")

# ---------------------------------------------------------
# Load Zillow Data
# ---------------------------------------------------------
ZHVI_FILE = Path("raw_data/zillow_full_cache.csv")
ZORI_FILE = Path("raw_data/zori_cache.csv")

@st.cache_data(show_spinner=False)
def load_zillow():
    zhvi = pd.read_csv(ZHVI_FILE, dtype={"RegionName": str})
    zori = pd.read_csv(ZORI_FILE, dtype={"RegionName": str})
    return zhvi, zori

def extract_zip(address):
    match = re.search(r'\b(\d{5})\b', address)
    return match.group(1) if match else None

def get_market_data(zhvi_df, zori_df, zipcode):
    price, rent, city, state = None, None, "", ""
    zhvi_row = zhvi_df[zhvi_df["RegionName"] == zipcode]
    zori_row = zori_df[zori_df["RegionName"] == zipcode]
    if not zhvi_row.empty:
        dcols = [c for c in zhvi_df.columns if c.startswith("20")]
        vals = zhvi_row.iloc[0][dcols].dropna()
        if not vals.empty:
            price = int(round(float(vals.iloc[-1])))
        city = zhvi_row.iloc[0].get("City", "")
        state = zhvi_row.iloc[0].get("State", "")
    if not zori_row.empty:
        dcols = [c for c in zori_df.columns if c.startswith("20")]
        vals = zori_row.iloc[0][dcols].dropna()
        if not vals.empty:
            rent = int(round(float(vals.iloc[-1])))
    return price, rent, city, state

zhvi_df, zori_df = load_zillow()

# ---------------------------------------------------------
# Sidebar — Shared Inputs
# ---------------------------------------------------------
st.sidebar.markdown("## 🧾 Shared Financial Inputs")
st.sidebar.caption("These settings apply to both Property A and Property B")
st.sidebar.subheader("📍 Property Information")

address_a = st.sidebar.text_input("Address (Property A) *", placeholder="123 Oak St, Danville CA 94526")
address_b = st.sidebar.text_input("Address (Property B) *", placeholder="456 Elm St, San Ramon CA 94583")

zip_a = extract_zip(address_a) if address_a else None
zip_b = extract_zip(address_b) if address_b else None

zhvi_a, zori_a, city_a, state_a = get_market_data(zhvi_df, zori_df, zip_a) if zip_a else (None, None, "", "")
zhvi_b, zori_b, city_b, state_b = get_market_data(zhvi_df, zori_df, zip_b) if zip_b else (None, None, "", "")

if city_a:
    st.sidebar.success(f"Property A: {city_a}, {state_a} {zip_a}")
    if zhvi_a:
        st.sidebar.caption(f"Market median: ${zhvi_a:,}")
if city_b:
    st.sidebar.success(f"Property B: {city_b}, {state_b} {zip_b}")
    if zhvi_b:
        st.sidebar.caption(f"Market median: ${zhvi_b:,}")

st.sidebar.subheader("💰 Financing & Growth")
mortgage_rate = st.sidebar.slider("Mortgage Rate (%)", 0.0, 15.0, 5.5, 0.1)
mortgage_term = st.sidebar.slider("Mortgage Term (years)", 5, 40, 30)
vacancy_rate = st.sidebar.slider("Vacancy Rate (%)", 0.0, 20.0, 5.0, 0.5)

# ---------------------------------------------------------
# Main — Two Column Inputs
# ---------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Property A")
    if address_a and not zip_a:
        st.warning("Include ZIP code in Property A address")

    purchase_price_a = st.number_input("Purchase Price A ($)",
        value=zhvi_a if zhvi_a else 500000, step=1000, key="ppa")
    if zhvi_a and purchase_price_a != zhvi_a:
        diff = ((purchase_price_a - zhvi_a) / zhvi_a) * 100
        st.caption(f"{abs(diff):.1f}% {'above' if diff > 0 else 'below'} {city_a} median of ${zhvi_a:,}")

    down_payment_pct_a = st.slider("Down Payment A (%)", 0.0, 100.0, 20.0, 1.0, key="dpa")

    if zori_a:
        st.markdown(f"**Monthly Rent A** — Zillow estimate: ${zori_a:,}/mo")
        rent_a = st.slider("Adjust rent A", int(zori_a*0.8), int(zori_a*1.2), zori_a, 50, key="renta")
    else:
        rent_a = st.number_input("Monthly Rent A ($)", value=2000, step=100, key="renta")

    monthly_expenses_a = st.number_input("Monthly Expenses A ($)", value=800, key="expa")
    appreciation_rate_a = st.slider("Annual Appreciation A (%)", 0.0, 10.0, 3.0, 0.1, key="appa")
    rent_growth_rate_a = st.slider("Annual Rent Growth A (%)", 0.0, 10.0, 2.0, 0.1, key="rga")
    time_horizon_a = st.slider("Time Horizon A (Years)", 1, 30, 10, key="tha")

with col2:
    st.subheader("🏘️ Property B")
    if address_b and not zip_b:
        st.warning("Include ZIP code in Property B address")

    purchase_price_b = st.number_input("Purchase Price B ($)",
        value=zhvi_b if zhvi_b else 520000, step=1000, key="ppb")
    if zhvi_b and purchase_price_b != zhvi_b:
        diff = ((purchase_price_b - zhvi_b) / zhvi_b) * 100
        st.caption(f"{abs(diff):.1f}% {'above' if diff > 0 else 'below'} {city_b} median of ${zhvi_b:,}")

    down_payment_pct_b = st.slider("Down Payment B (%)", 0.0, 100.0, 20.0, 1.0, key="dpb")

    if zori_b:
        st.markdown(f"**Monthly Rent B** — Zillow estimate: ${zori_b:,}/mo")
        rent_b = st.slider("Adjust rent B", int(zori_b*0.8), int(zori_b*1.2), zori_b, 50, key="rentb")
    else:
        rent_b = st.number_input("Monthly Rent B ($)", value=2100, step=100, key="rentb")

    monthly_expenses_b = st.number_input("Monthly Expenses B ($)", value=800, key="expb")
    appreciation_rate_b = st.slider("Annual Appreciation B (%)", 0.0, 10.0, 3.0, 0.1, key="appb")
    rent_growth_rate_b = st.slider("Annual Rent Growth B (%)", 0.0, 10.0, 2.0, 0.1, key="rgb")
    time_horizon_b = st.slider("Time Horizon B (Years)", 1, 30, 10, key="thb")

# ---------------------------------------------------------
# Calculate
# ---------------------------------------------------------
metrics_a = calculate_metrics(purchase_price_a, rent_a, down_payment_pct_a, mortgage_rate,
    mortgage_term, monthly_expenses_a, vacancy_rate, appreciation_rate_a, rent_growth_rate_a, time_horizon_a)
metrics_b = calculate_metrics(purchase_price_b, rent_b, down_payment_pct_b, mortgage_rate,
    mortgage_term, monthly_expenses_b, vacancy_rate, appreciation_rate_b, rent_growth_rate_b, time_horizon_b)

summary_text, grade = generate_ai_verdict(metrics_a, metrics_b)
metrics_a["AI Verdict"] = summary_text
metrics_a["Grade"] = grade
metrics_b["AI Verdict"] = summary_text
metrics_b["Grade"] = grade

# ---------------------------------------------------------
# Long-Term Metrics
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📈 Long-Term Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("IRR A (Operational) (%)", f"{metrics_a.get('IRR (Operational) (%)', 0):.2f}")
col2.metric("IRR A (Total incl. Sale) (%)", f"{metrics_a.get('IRR (Total incl. Sale) (%)', 0):.2f}")
col3.metric("Equity Multiple A", f"{metrics_a.get('equity_multiple', 0):.2f}")
col4, col5, col6 = st.columns(3)
col4.metric("IRR B (Operational) (%)", f"{metrics_b.get('IRR (Operational) (%)', 0):.2f}")
col5.metric("IRR B (Total incl. Sale) (%)", f"{metrics_b.get('IRR (Total incl. Sale) (%)', 0):.2f}")
col6.metric("Equity Multiple B", f"{metrics_b.get('equity_multiple', 0):.2f}")

# ---------------------------------------------------------
# Chart
# ---------------------------------------------------------
st.subheader("📈 Multi-Year ROI, Rent & Cash Flow Comparison (A vs B)")

cf_a = metrics_a.get("Multi-Year Cash Flow", [])
cf_b = metrics_b.get("Multi-Year Cash Flow", [])
rent_a_chart = metrics_a.get("Annual Rents $ (by year)", [])
rent_b_chart = metrics_b.get("Annual Rents $ (by year)", [])
roi_a = metrics_a.get("Annual ROI % (by year)", [])
roi_b = metrics_b.get("Annual ROI % (by year)", [])

years_a = list(range(1, len(cf_a) + 1))
years_b = list(range(1, len(cf_b) + 1))
years_a = years_a[:min(len(years_a), len(rent_a_chart), len(roi_a), len(cf_a))]
years_b = years_b[:min(len(years_b), len(rent_b_chart), len(roi_b), len(cf_b))]

fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(years_a, cf_a[:len(years_a)], marker='o', label="Cash Flow A ($)", color='blue')
ax1.plot(years_b, cf_b[:len(years_b)], marker='o', label="Cash Flow B ($)", color='skyblue')
ax1.plot(years_a, rent_a_chart[:len(years_a)], marker='s', linestyle='--', label="Rent A ($)", color='orange')
ax1.plot(years_b, rent_b_chart[:len(years_b)], marker='s', linestyle='--', label="Rent B ($)", color='goldenrod')
ax1.set_xlabel("Year")
ax1.set_ylabel("Cash Flow / Rent ($)")
ax1.grid(True)
ax2 = ax1.twinx()
ax2.plot(years_a, roi_a[:len(years_a)], marker='^', label="ROI A (%)", color='green')
ax2.plot(years_b, roi_b[:len(years_b)], marker='^', linestyle='--', label="ROI B (%)", color='darkgreen')
ax2.set_ylabel("ROI (%)", color='green')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
ax1.set_title("Projected Cash Flow, Rent, and ROI Over Time")
col_chart, col_pad = st.columns([3, 1])
with col_chart:
    st.pyplot(fig, use_container_width=True)

# ---------------------------------------------------------
# PDF + Email
# ---------------------------------------------------------
st.markdown("---")
comparison_pdf = generate_comparison_pdf_table_style(
    metrics_a, metrics_b,
    address_a=address_a, zip_a=zip_a or "",
    address_b=address_b, zip_b=zip_b or ""
)
try:
    with open("Investment_Metrics_User_Guide.pdf", "rb") as f:
        st.download_button(
            label="📘 Download User Manual (PDF)",
            data=f,
            file_name="Investment_Metrics_User_Guide.pdf",
            mime="application/pdf",
            key="user_manual_dual"
        )
except FileNotFoundError:
    st.warning("📄 User Manual PDF not found.")

if comparison_pdf:
    st.download_button("📄 Download Comparison PDF", data=comparison_pdf,
        file_name="comparison_report.pdf", mime="application/pdf")

st.markdown("### 📨 Email This Report")
recipient_email = st.text_input("Enter email address", placeholder="you@example.com")
if st.button("Send Email Report") and recipient_email:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        st.error("❌ Please enter a valid email address.")
    else:
        try:
            pdf_bytes = generate_pdf(
                property_data_a={"Address A": address_a, "ZIP Code A": zip_a or ""},
                property_data_b={"Address B": address_b, "ZIP Code B": zip_b or ""},
                metrics_a=metrics_a, metrics_b=metrics_b, summary_text=summary_text
            )
            msg = EmailMessage()
            msg["Subject"] = "Your Real Estate Comparison Report"
            msg["From"] = os.getenv("EMAIL_USER")
            msg["To"] = recipient_email
            msg.set_content("Please find attached your real estate comparison report.")
            pdf_bytes.seek(0)
            msg.add_attachment(pdf_bytes.read(), maintype='application', subtype='pdf', filename="comparison_report.pdf")
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                smtp.send_message(msg)
            st.success(f"✅ Report sent to {recipient_email}!")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

with st.expander("🔧 Optional Enhancements", expanded=False):
    st.subheader("🏗️ Capital Improvements Tracker")
    st.caption("Use this to record upgrades like kitchen remodels, HVAC systems, or roof replacements.")
    initial_data = pd.DataFrame({"Year": [""], "Amount ($)": [""], "Description": [""], "Rent Uplift ($/mo)": [""]})
    improvements_df = st.data_editor(initial_data, num_rows="dynamic", use_container_width=True, key="improvements_editor_dual")
    improvements_df["Amount ($)"] = pd.to_numeric(improvements_df["Amount ($)"], errors="coerce")
    improvements_df["Rent Uplift ($/mo)"] = pd.to_numeric(improvements_df["Rent Uplift ($/mo)"], errors="coerce")
    improvements_df["Annual Uplift ($)"] = improvements_df["Rent Uplift ($/mo)"] * 12
    improvements_df["ROI (%)"] = (improvements_df["Annual Uplift ($)"] / improvements_df["Amount ($)"]) * 100
    valid_df = improvements_df.dropna(subset=["Amount ($)"])
    valid_df = valid_df[valid_df["Amount ($)"] > 0]
    total_cost = valid_df["Amount ($)"].sum() if not valid_df.empty else 0
    weighted_roi = ((valid_df["Amount ($)"] * valid_df["ROI (%)"]).sum() / total_cost if total_cost > 0 else 0)
    st.success(f"📊 Weighted ROI from Capital Improvements: {weighted_roi:.2f}% (based on ${total_cost:,.0f} spent)")
