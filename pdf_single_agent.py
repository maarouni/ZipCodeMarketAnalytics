from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def fmt_money(v):
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "N/A"

def fmt_pct(v):
    try:
        return f"{float(v):,.2f}%"
    except (TypeError, ValueError):
        return "N/A"


# ==========================================================
#  DYNAMIC NARRATIVE ENGINE FOR AGENT PDF
# ==========================================================

def generate_dynamic_executive_summary(metrics):
    cashflow = metrics.get("First Year Cash Flow ($)", 0)
    coc = metrics.get("Cash-on-Cash Return (%)", 0)
    roi = metrics.get("Final Year ROI (%)", 0)
    grade = metrics.get("Grade", "C")

    # Interpret performance tiers
    strong_cf = cashflow > 0
    premium_roi = roi >= 12
    moderate_cf = -100 < cashflow < 0

    # Start narrative
    summary = ""

    # CASH FLOW ANALYSIS
    if strong_cf:
        summary += (
            "This investment demonstrates positive and stable cash flow, indicating "
            "healthy income performance even under conservative operating assumptions. "
        )
    elif moderate_cf:
        summary += (
            "The investment presents slightly negative cash flow in the early years, "
            "but the deficit is narrow enough that modest rent growth or expense "
            "optimization can bring the property into positive territory. "
        )
    else:
        summary += (
            "Current projections indicate negative cash flow, suggesting higher "
            "leverage sensitivity or an elevated expense profile. This position may "
            "still suit appreciation-focused buyers or long-term investors. "
        )

    # ROI ANALYSIS
    if premium_roi:
        summary += (
            "The long-term return outlook is notably strong, signaling above-average value "
            "growth relative to the purchase price. "
        )
    elif roi >= 7:
        summary += (
            "The expected long-term return appears well-balanced, combining predictable income "
            "with steady appreciation potential. "
        )
    else:
        summary += (
            "The long-term return outlook is softer, meaning future appreciation is likely to be "
            "the primary driver of value rather than monthly income. "
        )
    # RISK & GRADE INTERPRETATION
    grade_map = {
        "A": (
            "low-risk, high-quality opportunity suitable for both conservative and "
            "growth-oriented buyers."
        ),
        "B": (
            "strong overall profile with balanced risk and reward characteristics."
        ),
        "C": (
            "moderate performance typical of mid-market investment properties."
        ),
        "D": (
            "property with higher monthly costs relative to income, making it more "
            "sensitive to financing terms and timing, and potentially better suited "
            "for buyers with a longer hold horizon or lifestyle priorities beyond cash flow."
        ),
        "F": (
            "scenario where monthly costs exceed projected income in the early years. "
            "Best suited for buyers prioritizing long-term equity growth, future value, "
            "or lifestyle considerations."
        ),
    }

    #summary +=  (f" Overall, this property represents a {grade_map.get(grade, 'moderate investment profile.')}"


    #}

    summary += (
        f" Overall, this property represents a "
        f"{grade_map.get(grade, 'moderate investment profile.')}"
    )             
                 

    return summary.strip()


def generate_dynamic_agent_perspective(metrics):
    cashflow = metrics.get("First Year Cash Flow ($)", 0)
    roi = metrics.get("Final Year ROI (%)", 0)
    grade = metrics.get("Grade", "C")

    text = ""

    # PERFORMANCE POSITIONING
    if cashflow > 0:
        text += (
            "Based on the current assumptions, this property projects positive cash flow, "
            "which can support a more income-oriented strategy from day one. "
        )
    elif cashflow > -150:
        text += (
            "Based on the current assumptions, this property is close to break-even cash flow. "
            "That typically means the outcome depends more on time horizon, rent growth, and cost control "
            "than immediate monthly income. "
        )
    else:
        text += (
            "Based on the current assumptions, this property starts cash-flow negative, "
            "so the outcome is more dependent on long-term appreciation and rent growth than near-term income. "
        )

    # RETURN PROFILE (client - facing)
    if roi >= 12:
        text += (
            "The ROI profile is especially compelling for long-horizon investors seeking "
            "predictable compounding returns. "
        )
    elif roi >= 7:
        text += (
            "With balanced ROI performance, this deal is appropriate for clients looking "
            "to strengthen their portfolio with steady, inflation-resilient returns. "
        )
    else:
        text += (
            "Given the softer ROI, this property may work best as a land-banking or "
            "appreciation-driven position rather than a cash-flow engine. "
        )

    # GRADE INTERPRETATION
    if grade in ("A", "B"):
        text += (
            " Overall, the risk/return profile appears relatively favorable compared to many comparable scenarios."
        )
    elif grade in ("C", "D"):
        text += (
            " Overall, the risk/return profile looks mixed, so it may be worth reviewing assumptions like rent, expenses, and financing."
        )
    else:
        text += (
            " Overall, this scenario appears higher-risk under the current assumptions, so it may be worth stress-testing rent, expenses, and financing inputs."
        )

    return text.strip()


def generate_dynamic_improvement_commentary(improvement_cost, improvement_rent_impact, metrics):
    if improvement_cost <= 0 or improvement_rent_impact <= 0:
        return "No improvement scenario provided."

    # Evaluate improvement ROI
    annual_lift = improvement_rent_impact * 12
    payback = improvement_cost / annual_lift  # years

    text = (
        f"The proposed upgrade requires an investment of ${improvement_cost:,.0f} "
        f"and yields an estimated rent increase of ${improvement_rent_impact:,.0f} per month. "
    )

    if payback <= 3:
        text += (
            f"This produces a strong payback period of approximately {payback:.1f} years, "
            "making it a high-value enhancement for both ROI and long-term cash flow. "
        )
    elif payback <= 5:
        text += (
            f"The resulting payback period of roughly {payback:.1f} years positions this "
            "upgrade as a reasonable mid-term value-add opportunity. "
        )
    else:
        text += (
            f"With a payback period near {payback:.1f} years, this upgrade is best suited "
            "for buyers prioritizing long-term appreciation rather than short-term income gains. "
        )

    roi = metrics.get("Expected Annual Return", None)
    if roi is not None:
        try:
            text += (
                f" Relative to the property's projected {float(roi):.1f}% long-term ROI, "
                "this improvement can shift the investment profile meaningfully for value-add buyers."
            )
        except (TypeError, ValueError):
            # If roi is not numeric, just skip that sentence
            pass

    return text.strip()


# ==============================================
#  MAIN PDF GENERATOR (NO ICONS)
# ==============================================
def generate_pdf(
    property_data: dict,
    metrics: dict,
    summary_text: str,
    agent_name: str,
    brokerage_name: str,
    client_name: str,
    agent_notes: str = "",
    improvements_list=None,
):
    print("🔥 USING pdf_single_agent.py (dynamic, icon-free version)")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Styles
    title_style = ParagraphStyle(
        "TitleLarge",
        parent=styles["Normal"],
        fontSize=20,
        alignment=1,
        textColor=colors.HexColor("#003366"),
        spaceAfter=6,
    )

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Normal"],
        fontSize=10,
        alignment=1,
        textColor=colors.black,
        spaceAfter=12,
    )

    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading3"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#003366"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    disclaimer_style = ParagraphStyle(
        "Disc",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.black,  # black disclaimer text
        leading=12,
        spaceBefore=8,
    )

    # ---------------------------------------
    # TITLE + HEADER
    # ---------------------------------------
    elements.append(Paragraph("Property Investment Overview", title_style))
    elements.append(Spacer(1, 4))

    today = datetime.now().strftime("%B %d, %Y")

    # Optional address line from property_data
    address_line = ""
    street = property_data.get("street_address") or property_data.get("address")
    zip_code = property_data.get("zip_code") or property_data.get("zip")
    if street or zip_code:
        parts = [street or "", zip_code or ""]
        address_line = " | ".join([p for p in parts if p])

    header_html = ""
    if address_line:
        header_html += f"<b>{address_line}</b><br/>"

    header_html += f"""
    Prepared for: <b>{client_name}</b><br/>
    Prepared by: <b>{agent_name}</b><br/>
    Brokerage: <b>{brokerage_name}</b><br/>
    Date: {today}
    """

    elements.append(Paragraph(header_html, header_style))

    # ---------------------------------------
    # EXECUTIVE SUMMARY (DYNAMIC)
    # ---------------------------------------
    elements.append(Paragraph("Executive Deal Summary", section_style))

    dynamic_summary = generate_dynamic_executive_summary(metrics)
    elements.append(Paragraph(dynamic_summary, body_style))
    elements.append(Spacer(1, 12))

    grade = metrics.get("Grade", "N/A")
    desc_map = {
        "A": "Excellent long-term income and appreciation potential.",
        "B": "Strong investment with solid cash flow and moderate risk.",
        "C": "Modest performance with tighter margins.",
        "D": (
            "Higher monthly costs relative to income make this property more sensitive "
        "to financing terms and timing. It may be better suited for buyers with a "
        "longer hold horizon or lifestyle priorities beyond cash flow."
        ),    
        "F": (
            "The monthly cost is significantly above the projected income, so this "
        "property is best suited for buyers focused on long-term ownership and "
        "equity growth."
        ),
    }
    suit = desc_map.get(grade, "General suitability assessment.")

    elements.append(Paragraph(f"<b>Overall Investment Suitability:</b> {suit}", body_style))
    elements.append(Spacer(1, 6))

    # ---------------------------------------
    # KEY DECISION METRICS
    # ---------------------------------------
    elements.append(Paragraph("Key Decision Metrics", section_style))

    annual_rents = metrics.get("Annual Rents $ (by year)", [])

    # Year X follows the horizon slider because Annual Rents is year-by-year
    if isinstance(annual_rents, list) and len(annual_rents) > 0:
        year_x = len(annual_rents)
        projected_monthly_rent = annual_rents[-1] / 12
    else:
        year_x = None
        projected_monthly_rent = None

    # Pull CURRENT rent from property_data (must match what Streamlit passes in)
    current_rent = (
        property_data.get("expected_monthly_rent")
        or property_data.get("monthly_rent")
        or property_data.get("rent")
    )
    try:
        current_rent = float(current_rent) if current_rent is not None else None
    except (TypeError, ValueError):
        current_rent = None
    fallback_year_x = property_data.get("time_horizon")
    try:
        fallback_year_x = int(fallback_year_x) if fallback_year_x is not None else None
    except (TypeError, ValueError):
        fallback_year_x = None

    year_x = year_x or fallback_year_x  # reuse the year_x you computed above if present

    monthly_cash_flow = metrics.get("First Year Cash Flow ($)", None)
    final_year_roi = metrics.get("Final Year ROI (%)", None)
    coc = metrics.get("Cash-on-Cash Return (%)", None)

    curated = [
        ("Monthly Cash Flow ($)", fmt_money(monthly_cash_flow)),  # ✅ $ label
        (f"Expected Return (%) — by Year {year_x}" if year_x else "Expected Return (%)",
         fmt_pct(final_year_roi)),  # ✅ % label + Year X
        ("Monthly Cost vs Monthly Rent (%)", fmt_pct(coc)),  # ✅ % label (even if name is imperfect)
        ("Investment Grade", grade),

        ("Current Rent Assumption (Today)",
         f"${current_rent:,.0f}" if current_rent is not None else "N/A"),

        (f"Estimated Rent in Year {year_x}" if year_x else "Estimated Rent (End of Period)",
         f"${projected_monthly_rent:,.0f}" if projected_monthly_rent is not None else "N/A"),
    ]
    table_data = [["Metric", "Value"]] + [[k, str(v)] for k, v in curated]
    table = Table(table_data, colWidths=[230, 230])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------
    # AGENT PERSPECTIVE (DYNAMIC WITH OVERRIDE)
    # ---------------------------------------
    elements.append(Paragraph("Client Perspective", section_style))

    # Always use dynamic agent perspective — ignore agent notes entirely
    agent_text = generate_dynamic_agent_perspective(metrics)
    elements.append(Paragraph(agent_text, body_style))
    
    # ---------------------------------------
    # OPTIONAL IMPROVEMENTS (MULTI-ROW TABLE + DYNAMIC COMMENT)
    # ---------------------------------------
    if improvements_list and len(improvements_list) > 0:

        elements.append(Paragraph("Optional Improvement Scenarios", section_style))

        # Build table header
        table_data = [["Upgrade", "Cost", "Est. Monthly Rent Impact"]]

        # Add one row per improvement
        for imp in improvements_list:
            name = str(imp.get("Description", ""))
            cost = float(imp.get("Amount ($)", 0) or 0)

            # Preserve 65× rule
            est_rent = round(cost / 65) if cost > 0 else 0

            table_data.append([
                name,
                f"${cost:,.0f}",
                f"+${est_rent:,.0f}",
            ])

        improv_table = Table(table_data, colWidths=[170, 110, 160])
        improv_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))

        elements.append(improv_table)
        elements.append(Spacer(1, 8))

        # Combine commentary
        commentary_parts = []
        for imp in improvements_list:
            cost = float(imp.get("Amount ($)", 0) or 0)
            est_rent = round(cost / 65) if cost > 0 else 0

            commentary_parts.append(
                generate_dynamic_improvement_commentary(cost, est_rent, metrics)
            )

        final_comment = " ".join(commentary_parts)
        elements.append(Paragraph(final_comment, body_style))
        elements.append(Spacer(1, 8))
    
    # ---------------------------------------
    # DISCLAIMER (SHORT, 1 LINE, NO EMOJI)
    # ---------------------------------------
    elements.append(Spacer(1, -4))  # subtle pull-up fix
    disclaimer_block = KeepTogether([
        Paragraph("Disclaimer", section_style),
        Paragraph("Estimates only — actual results may vary.", disclaimer_style),
    ])
    elements.append(disclaimer_block)

    # ---------------------------------------
    # BUILD PDF
    # ---------------------------------------
    doc.build(elements)
    buffer.seek(0)
    return buffer


# Compatibility alias
generate_pdf_report = generate_pdf
