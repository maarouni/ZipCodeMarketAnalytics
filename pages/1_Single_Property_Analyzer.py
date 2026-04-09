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

sys.path.insert(0, str(Path(__file__).parent.parent))
from calc_engine import calculate_metrics
from pdf_single import generate_pdf, generate_ai_verdict
from pdf_single_agent import generate_pdf as generate_agent_pdf

st.set_page_config(page_title="Single Property Analyzer", layout="wide")
st.title("🏡 Single Property Analyzer")
st.markdown("Analyze the investment potential of a specific property.")

ZHVI_FILE = Path("raw_data/zillow_full_cache.csv")
ZORI_FILE = Path("raw_data/zori_cache.csv")
ZHVI_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv?t=1770952790"
import requests

@st.cache_data(show_spinner="Loading market data — first load takes ~10 seconds...")
def load_zillow():
    ZHVI_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ZHVI_FILE.exists():
        r = requests.get(ZHVI_URL, stream=True)
        with open(ZHVI_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    if not ZORI_FILE.exists():
        r = requests.get(ZORI_URL, stream=True)
        with open(ZORI_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
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

st.sidebar.header("🏡 Property Information")
street_address = st.sidebar.text_input("Street Address *", placeholder="123 Oak St, Danville CA 94526")

zip_from_address = extract_zip(street_address) if street_address else None
zhvi_price, zori_rent, mkt_city, mkt_state = None, None, "", ""

if zip_from_address:
    zhvi_price, zori_rent, mkt_city, mkt_state = get_market_data(zhvi_df, zori_df, zip_from_address)
    if mkt_city:
        st.sidebar.success(f"📍 {mkt_city}, {mkt_state} {zip_from_address}")
        if zhvi_price:
            st.sidebar.caption(f"Market median (Zillow ZHVI): ${zhvi_price:,}")
    else:
        st.sidebar.warning(f"ZIP {zip_from_address} not found in Zillow data")
elif street_address:
    st.sidebar.warning("Include ZIP code in address to load market data")

purchase_price = st.sidebar.number_input(
    "Purchase Price ($)",
    min_value=10000,
    value=zhvi_price if zhvi_price else 500000,
    step=1000,
    help="Enter the actual listing/purchase price"
)

if zhvi_price and purchase_price != zhvi_price:
    diff_pct = ((purchase_price - zhvi_price) / zhvi_price) * 100
    direction = "above" if diff_pct > 0 else "below"
    st.sidebar.caption(f"This price is **{abs(diff_pct):.1f}% {direction}** the {mkt_city} median of ${zhvi_price:,}")

if zori_rent:
    rent_min = int(zori_rent * 0.70)
    rent_max = int(zori_rent * 1.30)
    st.sidebar.markdown("**Monthly Rent ($)**")
    st.sidebar.caption(f"Zillow ZORI estimate: ${zori_rent:,}/mo — adjust ±30% for your property")
    monthly_rent = st.sidebar.slider("Drag to adjust rent", min_value=rent_min, max_value=rent_max, value=zori_rent, step=50)
else:
    monthly_rent = st.sidebar.number_input("Expected Monthly Rent ($)", min_value=0, value=2000, step=100)

monthly_expenses = st.sidebar.number_input(
    "Monthly Expenses ($: property tax + insurance + miscellaneous)",
    min_value=0, value=800, step=50,
    help="Property tax + insurance + maintenance + HOA"
)

st.sidebar.header("💰 Financing & Growth")
down_payment_pct = st.sidebar.slider("Down Payment (%)", 0, 100, 20)
mortgage_rate = st.sidebar.slider("Mortgage Rate (%)", 0.0, 15.0, 6.5, step=0.1)
mortgage_term = st.sidebar.number_input("Mortgage Term (years)", min_value=1, value=30)
vacancy_rate = st.sidebar.slider("Vacancy Rate (%)", 0, 100, 5)
appreciation_rate = st.sidebar.slider("Annual Appreciation Rate (%)", 0, 10, 3)
rent_growth_rate = st.sidebar.slider("Annual Rent Growth Rate (%)", 0, 10, 3)
time_horizon = st.sidebar.slider("Investment Time Horizon (Years)", 1, 30, 10)

metrics = calculate_metrics(
    purchase_price, monthly_rent, down_payment_pct,
    mortgage_rate, mortgage_term,
    monthly_expenses, vacancy_rate, appreciation_rate,
    rent_growth_rate, time_horizon
)

property_data = {
    "street_address": street_address or "Not provided",
    "zip_code": zip_from_address or "",
    "purchase_price": purchase_price,
    "monthly_rent": monthly_rent,
    "monthly_expenses": monthly_expenses,
    "down_payment_pct": down_payment_pct,
    "mortgage_rate": mortgage_rate,
    "mortgage_term": mortgage_term,
    "vacancy_rate": vacancy_rate,
    "appreciation_rate": appreciation_rate,
    "rent_growth_rate": rent_growth_rate,
    "time_horizon": time_horizon
}

improvements_list = []
summary_text, grade = generate_ai_verdict(metrics)

tab1, tab2, tab3 = st.tabs(["Deal Analyzer", "Insights", "Agent Report"])

# ===================================================================
# TAB 1 — DEAL ANALYZER
# ===================================================================
with tab1:
    if not street_address:
        st.info("Enter a street address with ZIP code in the sidebar to begin analysis.")

    pdf_bytes = generate_pdf(property_data, metrics, summary_text)

    st.subheader("📈 Long-Term Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("IRR (Operational) (%)", f"{metrics.get('IRR (Operational) (%)', 0):.2f}")
    col2.metric("IRR (Total incl. Sale) (%)", f"{metrics.get('IRR (Total incl. Sale) (%)', 0):.2f}")
    col3.metric("Equity Multiple", f"{metrics.get('equity_multiple', 0):.2f}")

    st.subheader("📈 Multi-Year Cash Flow Projection")
    years = list(range(1, time_horizon + 1))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(years, metrics["Multi-Year Cash Flow"], marker='o', label="Multi-Year Cash Flow ($)")
    ax.plot(years, metrics["Annual Rents $ (by year)"], marker='s', linestyle='--', label="Projected Rent ($)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Projected Cash Flow / Rent ($)")
    ax.grid(True)
    ax2 = ax.twinx()
    ax2.plot(years, metrics["Annual ROI % (by year)"], color='green', marker='^', label="ROI (%)")
    ax2.set_ylabel("ROI (%)", color='green')
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left")
    ax.set_title("Multi-Year Projected Cash Flow & ROI")
    col_chart, col_pad = st.columns([3, 1])
    with col_chart:
        st.pyplot(fig, use_container_width=True)

    st.markdown("---")

    try:
        with open("Investment_Metrics_User_Guide.pdf", "rb") as f:
            st.download_button(
                label="📘 Download User Manual (PDF)",
                data=f,
                file_name="Investment_Metrics_User_Guide.pdf",
                mime="application/pdf",
                key="user_manual"
            )
    except FileNotFoundError:
        st.warning("📄 User Manual PDF not found in project folder.")

    if pdf_bytes:
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"deal_analysis_{zip_from_address or 'report'}.pdf",
            mime="application/pdf"
        )

    st.markdown("### 📨 Email This Report")
    recipient_email = st.text_input("Enter email address to send the report", placeholder="you@example.com")
    if st.button("Send Email Report") and recipient_email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
            st.error("❌ Please enter a valid email address.")
        else:
            try:
                msg = EmailMessage()
                msg["Subject"] = "Your Real Estate Evaluation Report"
                msg["From"] = os.getenv("EMAIL_USER")
                msg["To"] = recipient_email
                msg.set_content("Please find attached your real estate evaluation report.")
                pdf_bytes.seek(0)
                msg.add_attachment(pdf_bytes.read(), maintype='application', subtype='pdf', filename="real_estate_report.pdf")
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
        improvements_df = st.data_editor(initial_data, num_rows="dynamic", use_container_width=True, key="improvements_editor")
        improvements_df["Amount ($)"] = pd.to_numeric(improvements_df["Amount ($)"], errors="coerce")
        improvements_df["Rent Uplift ($/mo)"] = pd.to_numeric(improvements_df["Rent Uplift ($/mo)"], errors="coerce")

        def compute_uplift(row):
            if pd.notna(row["Rent Uplift ($/mo)"]):
                return row["Rent Uplift ($/mo)"]
            if pd.isna(row["Amount ($)"]) or row["Amount ($)"] <= 0:
                return 0
            return round(row["Amount ($)"] / 65)

        improvements_df["Rent Uplift ($/mo)"] = improvements_df.apply(compute_uplift, axis=1)
        improvements_df["Annual Uplift ($)"] = improvements_df["Rent Uplift ($/mo)"] * 12
        improvements_df["ROI (%)"] = (improvements_df["Annual Uplift ($)"] / improvements_df["Amount ($)"]) * 100
        valid_df = improvements_df.dropna(subset=["Amount ($)"])
        valid_df = valid_df[valid_df["Amount ($)"] > 0]
        improvements_list = [] if valid_df.empty else valid_df.to_dict(orient="records")
        total_cost = valid_df["Amount ($)"].sum() if not valid_df.empty else 0
        weighted_roi = ((valid_df["Amount ($)"] * valid_df["ROI (%)"]).sum() / total_cost if total_cost > 0 else 0)
        st.success(f"📊 Weighted ROI from Capital Improvements: {weighted_roi:.2f}% (based on ${total_cost:,.0f} spent)")

# ===================================================================
# TAB 2 — INSIGHTS
# ===================================================================
with tab2:
    st.markdown("### 📊 Insights Dashboard")

    annual_cash_flows = metrics["Multi-Year Cash Flow"]
    break_even = next((i for i, v in enumerate(annual_cash_flows, start=1) if v > 0), None)
    if break_even:
        st.success(f"📅 Break-Even achieved in **Year {break_even}** ( Expected based on Rent increases, Expenses and fixed Mortgage.)")
    else:
        st.warning("❗ This property does not break even within the selected time horizon.")

    st.markdown("### 🥧 Where Does the Rent Go?")
    st.subheader("📊 Annual Income Allocation")

    effective_rent = monthly_rent * (1 - vacancy_rate / 100.0)
    annual_rent = effective_rent * 12
    annual_expenses = monthly_expenses * 12
    annual_mortgage = metrics.get("Monthly Mortgage ($)", 0) * 12
    annual_cash_flow = annual_rent - annual_expenses - annual_mortgage

    labels = ["Operating Expenses", "Mortgage", "Cash Flow"]
    values = [max(annual_expenses, 0), max(annual_mortgage, 0), max(annual_cash_flow, 0)]
    value_labels = [f"${annual_expenses:,.0f}", f"${annual_mortgage:,.0f}", f"${annual_cash_flow:,.0f}"]

    fig_exp, ax_exp = plt.subplots(figsize=(5, 5))
    wedges, texts, autotexts = ax_exp.pie(values, labels=None, autopct="%1.1f%%", pctdistance=0.75, startangle=90)
    for i, w in enumerate(wedges):
        ang = (w.theta2 + w.theta1) / 2
        x = 1.25 * np.cos(np.deg2rad(ang))
        y = 1.25 * np.sin(np.deg2rad(ang))
        ax_exp.text(x, y, f"{value_labels[i]}\n{labels[i]}", ha="center", va="center", fontsize=11, fontweight="bold")
    ax_exp.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.1), frameon=False, ncol=3)
    ax_exp.axis("equal")
    col_chart, col_pad = st.columns([2, 2])
    with col_chart:
        st.pyplot(fig_exp, use_container_width=True)

    st.markdown("""
### 📝 Interpretation
- **Operating Expenses** — property tax, insurance, maintenance, HOA
- **Mortgage** — annual principal + interest payments
- **Cash Flow** — annual proceeds after all costs

_All slices shown as % of **annual** income — aligned with investor metrics._
""")

    st.subheader("🍩 Net Cap Rate Efficiency Donut")
    st.markdown('<div style="font-size:18px; font-weight:500; margin-top:-10px;">Shows how efficiently the property produces income <em>after expenses and reserves</em>.</div>', unsafe_allow_html=True)

    NOI = max(annual_rent - annual_expenses, 0)
    reserves = max(0.05 * annual_rent, 0)
    net_noi = max(NOI - reserves, 0)
    net_cap_rate = (net_noi / purchase_price * 100) if purchase_price > 0 else 0
    non_income_portion = max(purchase_price - net_noi, 0)

    labels_cap = ["Net Operating Income (after reserves)", "Non-Income-Producing Portion"]
    values_cap = [net_noi, non_income_portion]

    if sum(values_cap) == 0:
        st.warning("⚠️ Net Cap Rate cannot be computed — values are zero.")
    else:
        fig_cap, ax_cap = plt.subplots(figsize=(5, 5))
        wedges, _ = ax_cap.pie(values_cap, wedgeprops=dict(width=0.35), startangle=90)
        ax_cap.text(0, 0.05, f"{net_cap_rate:.2f}%", ha="center", va="center", fontsize=20, fontweight="bold")
        ax_cap.text(0, -0.12, "earned from your property", ha="center", va="center", fontsize=11, color="gray")
        ax_cap.axis("equal")
        col_chart, col_pad = st.columns([2, 2])
        with col_chart:
            st.pyplot(fig_cap, use_container_width=True)
        st.markdown(f"""
📘 **Meaning:** **{net_cap_rate:.2f}%** of your property's value actually comes back
to you as *yearly income after expenses and reserves.*

- Net NOI: **${net_noi:,.0f}**
- Reserves (5% of rent): **${reserves:,.0f}**

➡️ **This tells you how efficiently this property turns its value into real income.**
""")

# ===================================================================
# TAB 3 — AGENT REPORT
# ===================================================================
with tab3:
    st.subheader("📄 Agent-Branded Property Report")
    st.markdown("Generate a **client-ready PDF** with your name, brokerage, and personalized notes.")

    st.markdown("### 👤 Agent Information")
    agent_name = st.text_input("Agent Name")
    brokerage_name = st.text_input("Brokerage Name")
    client_name = st.text_input("Client Name")
    agent_notes = st.text_area("Notes for Client")

    agent_pdf_bytes = generate_agent_pdf(
        property_data=property_data,
        metrics=metrics,
        summary_text=summary_text,
        agent_name=agent_name or "Agent",
        brokerage_name=brokerage_name or "Your Brokerage",
        client_name=client_name or "Client",
        agent_notes=agent_notes or "",
        improvements_list=improvements_list
    )

    if agent_pdf_bytes:
        st.download_button("📄 Download Agent PDF", data=agent_pdf_bytes,
            file_name="agent_property_report.pdf", mime="application/pdf", key="download_agent_pdf")
    else:
        st.error("⚠️ Agent PDF generation failed.")

    st.markdown("### 📨 Email This Client-Branded Report")
    agent_email = st.text_input("Enter email address to send the report", placeholder="client@example.com")
    if st.button("Send Agent-Branded PDF") and agent_email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", agent_email):
            st.error("❌ Please enter a valid email address.")
        else:
            try:
                msg = EmailMessage()
                msg["Subject"] = "Your Personalized Real Estate Report"
                msg["From"] = os.getenv("EMAIL_USER")
                msg["To"] = agent_email
                msg.set_content(f"Hi {client_name},\n\nPlease find attached your personalized real estate investment report.\nLet me know if you'd like to walk through the numbers together.\n\nBest,\n{agent_name}")
                agent_pdf_bytes.seek(0)
                msg.add_attachment(agent_pdf_bytes.read(), maintype='application', subtype='pdf', filename="client_real_estate_report.pdf")
                with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                    smtp.starttls()
                    smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                    smtp.send_message(msg)
                st.success(f"✅ Client-Branded Report sent to {agent_email}!")
            except Exception as e:
                st.error(f"❌ Failed to send email: {e}")