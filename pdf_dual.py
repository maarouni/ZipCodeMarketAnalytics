
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet , ParagraphStyle
#from reportlab.pdfgen import canvas

# ✅ Keys to skip (prevent duplicates like "10yr Cash Flow")
skip_keys = {"10Yr Cash Flow", "10yr Cash Flow"}

# Optional renaming of metric keys for user-friendly PDF display
rename_keys = {
    "roi_list": "Annual ROI % (by year)",
    "10yr Rents": "Annual Rents $ (by year)",
    "Final Year ROI (%)": "Final Year ROI (%)",
    "Multi-Year Cash Flow": "Multi-Year Cash Flow",
    "Annual ROI % (by year)": "Annual ROI % (by year)",
    "Annual Rents $ (by year)": "Annual Rents $ (by year)" # placeholder in case it's passed in future
}

# ✅ Order you want in the PDF
preferred_order = [
    "Cap Rate (%)",
    "Cash-on-Cash Return (%)",
    "Final Year ROI (%)",
    "First Year Cash Flow ($)",
    "Annual Cash Flow ($)",
    "Monthly Mortgage ($)",
    "Grade",
    "Multi-Year Cash Flow",  # Force this name only
    "Annual ROI % (by year)",
    "Annual Rents $ (by year)"
]

def format_display_value(key, value):
    """Format all numbers according to the agreed rules."""
    if isinstance(value, (float, int)):
            # Rule-based rounding
        if abs(value) >= 1:
            # round to nearest integer, no decimals
            return str(int(round(value)))
        elif abs(value) > 0:
            # keep up to 2 decimals for small fractional values
            return f"{value:.2f}"
        else:
            return "0"
    return str(value)

# ✅ Define AI Verdict function BEFORE generate_pdf

def parse_numeric(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return 0.0
def generate_ai_verdict(metrics_a: dict, metrics_b: dict) -> tuple[str, str]:
    print("🗝️ Property A keys:", list(metrics_a.keys()))
    print("🗝️ Property B keys:", list(metrics_b.keys()))

    roi_a = parse_numeric(metrics_a.get("Final Year ROI (%)") or metrics_a.get("ROI (%)", 0))
    roi_b = parse_numeric(metrics_b.get("Final Year ROI (%)") or metrics_b.get("ROI (%)", 0))

    coc_a = parse_numeric(metrics_a.get("Cash-on-Cash Return (%)", 0))
    coc_b = parse_numeric(metrics_b.get("Cash-on-Cash Return (%)", 0))

    # Example combined verdict
    verdict = f"""
    📊 AI Verdict:
    • Property A → ROI: {roi_a}%, CoC: {coc_a}%
    • Property B → ROI: {roi_b}%, CoC: {coc_b}%
    """

    grade = "A" if roi_a > roi_b else "B"

    return verdict.strip(), grade

    #roi = parse_numeric(metrics.get("Final Year ROI (%)") or metrics.get("ROI (%)", 0))
    roi = parse_numeric(metrics.get("Final Year ROI (%)"))
    if roi == 0.0:
        roi = parse_numeric(metrics.get("ROI (%)", 0))
    #cash_flow = parse_numeric(metrics.get("Annual Cash Flow ($)", 0))
    coc_return = parse_numeric(metrics.get("Cash-on-Cash Return (%)", 0))

    # ✅ Use Multi-Year Cash Flow to sum total
    raw_cash_flow = metrics.get("Multi-Year Cash Flow", [])
    print("🧾 Raw cash flow data (before processing):", raw_cash_flow)

    #print("🧾 Raw cash flow data (before processing):", raw_cash_flow)  # Debug line

   # ✅ Step 1: Handle case where it's a comma-separated string
    if isinstance(raw_cash_flow, str):
        try:
            raw_cash_flow = [parse_numeric(x) for x in raw_cash_flow.split(",")]
        except:
            raw_cash_flow = []

    elif isinstance(raw_cash_flow, list):
        raw_cash_flow = [parse_numeric(x) for x in raw_cash_flow]
    else:
        raw_cash_flow = []

    cash_flow = sum(raw_cash_flow)

    print("🧾 Parsed cash flow list:", raw_cash_flow)
    print(f"🧪 Debug: ROI={roi}, CashFlow={cash_flow}, CoC Return={coc_return}")
    
    # Sample grading logic
    if roi > 200 and cash_flow > 20000 and coc_return >= 5:
        grade = "A"
        summary = "This is an A-grade investment with high returns and strong cash flow."
    elif roi > 100 and cash_flow > 10000 and coc_return >= 0:
        grade = "B"
        summary = "This is a B-grade investment with solid performance and good ROI."
    elif roi > 50 and cash_flow > 5000 and coc_return >= -5:
        grade = "C"
        summary = "This is a C-grade investment with modest returns."
    elif roi > 0 and cash_flow > 0 and coc_return >= 6:
        grade = "D"
        summary = "This is a D-grade investment with marginal upside potential."
    else:
        grade = "F"
        summary = "This is an F-grade rental with upside potential."

    return summary, grade

def generate_pdf(property_data_a, property_data_b, metrics_a, metrics_b, summary_text):
    address_a = property_data_a.get("Address A", "")
    zip_a = property_data_a.get("ZIP Code A", "")
    address_b = property_data_b.get("Address B", "")
    zip_b = property_data_b.get("ZIP Code B", "")
  # ... then use in your PDF table rows
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1
    elements.append(Paragraph("🏘️ Property Comparison Summary", title_style))
    elements.append(Spacer(1, 12))

   # Shared Property Data
    table_data = [["Metric", "Property A", "Property B"]]

   # 🏠 Add Address and ZIP Code rows at the top of the table
    table_data.append(["Address", address_a, address_b])
    table_data.append(["ZIP Code", zip_a, zip_b])
    
    keys_to_include = [
        "Cap Rate (%)", "Final Year ROI (%)", "Cash-on-Cash Return (%)",
        "First Year Cash Flow ($)", "Monthly Mortgage ($)", "Grade"
    ]

    for key in keys_to_include:
        a_val = format_display_value(key, metrics_a.get(key, "N/A"))
        b_val = format_display_value(key, metrics_b.get(key, "N/A"))
        table_data.append([key, a_val, b_val])

    table = Table(table_data, colWidths=[180, 150, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # AI Verdict
    verdict_para = Paragraph(f"💡 <b>AI Verdict:</b> {summary_text}", styles["Normal"])
    elements.append(verdict_para)
    elements.append(Spacer(1, 24))

    # ✅ Metrics for A and B, cleaned and ordered
    preferred_order = [
        "Cap Rate (%)", "Cash-on-Cash Return (%)", "Final Year ROI (%)",
        "First Year Cash Flow ($)", "Annual Cash Flow ($)",
        "Monthly Mortgage ($)", "Grade", "Multi-Year Cash Flow",
        "Annual ROI % (by year)", "Annual Rents $ (by year)"
    ]
    skip_keys = ["Grade", "AI Verdict"]

    for label, metrics in [("Property A", metrics_a), ("Property B", metrics_b)]:
        elements.append(Paragraph(f"<b>{label} Metrics:</b>", styles["Heading4"]))
        metrics_cleaned = []

        for key in preferred_order:
            if key in metrics and key not in skip_keys:
                value = metrics[key]
                if isinstance(value, list):
                    grouped = [", ".join(format_display_value(key, val) for val in value[i:i+5])
                               for i in range(0, len(value), 5)]
                    wrapped = "<br/>".join(grouped)
                    metrics_cleaned.append([key, Paragraph(wrapped, styles["Normal"])])
                elif isinstance(value, float):
                    metrics_cleaned.append([key, format_display_value(key, value)])
                elif isinstance(value, str):
                    metrics_cleaned.append([key, Paragraph(value, styles["Normal"])])
                else:
                    metrics_cleaned.append([key, value])

        table_metrics = Table(metrics_cleaned, colWidths=[200, 350])
        table_metrics.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        elements.append(table_metrics)
        elements.append(Spacer(1, 12))

    # ✅ Build and return buffer properly
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Alias for import compatibility
generate_pdf_report = generate_pdf


#### ***** Full generate_comparison_pdf()  ******

def generate_comparison_pdf(metrics_a, metrics_b):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 770, "📊 Side-by-Side Deal Comparison Report")

    y = 730
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Metric")
    c.drawString(250, y, "Property A")
    c.drawString(400, y, "Property B")
    y -= 20

    c.setFont("Helvetica", 11)
    for key in metrics_a:
        value_a = str(metrics_a.get(key, "-"))
        value_b = str(metrics_b.get(key, "-"))

        c.drawString(50, y, f"{key}")
        c.drawString(250, y, value_a)
        c.drawString(400, y, value_b)
        y -= 20

        if y < 50:  # Add a new page if needed
            c.showPage()
            y = 750
            c.setFont("Helvetica", 11)

    c.save()
    buffer.seek(0)
    return buffer

# Existing PDF generation logic...

def generate_comparison_pdf_table_style(metrics_a, metrics_b, address_a="", zip_a="", address_b="", zip_b=""):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    verdict_styles = {
        "A": ParagraphStyle('A', textColor=colors.darkgreen, fontSize=10, spaceAfter=4),
        "B": ParagraphStyle('B', textColor=colors.green, fontSize=10, spaceAfter=4),
        "C": ParagraphStyle('C', textColor=colors.orange, fontSize=10, spaceAfter=4),
        "D": ParagraphStyle('D', textColor=colors.red, fontSize=10, spaceAfter=4),
        "F": ParagraphStyle('F', textColor=colors.red, fontSize=10, spaceAfter=4),
    }

    # Title Row
    title_data = [["📊 Property Comparison Summary", "", ""]]
    title_table = Table(title_data, colWidths=[200, 150, 150])
    title_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    elements.append(title_table)

    # Comparison Table
    keys_to_compare = [
        "Cap Rate (%)",
        "Final Year ROI (%)",
        "Cash-on-Cash Return (%)",
        "First Year Cash Flow ($)",
        "Monthly Mortgage ($)",
        "Mortgage Rate (%)",            # ✅ Optional new line
        "Mortgage Term (Years)",        # ✅ Optional new line
        "Grade",
        "Multi-Year Cash Flow"  # Now handled in a single place
    ]

    table_data = [["Metric", "Property A", "Property B"]]

    
 # 🏠 Add Address and ZIP Code rows at the top of the table
    table_data.append(["Address", address_a, address_b])
    table_data.append(["ZIP Code", zip_a, zip_b])

    keys_to_include = [
        "Cap Rate (%)", "Final Year ROI (%)", "Cash-on-Cash Return (%)",
        "First Year Cash Flow ($)", "Monthly Mortgage ($)", "Grade"
    ]

    for key in keys_to_compare:
        val_a = metrics_a.get(key, "N/A")
        val_b = metrics_b.get(key, "N/A")

        # Format long lists
        if isinstance(val_a, list):
            val_a = ", ".join([str(int(x)) for x in val_a])
        elif isinstance(val_a, float):
            val_a = f"{val_a:.2f}"

        if isinstance(val_b, list):
            val_b = ", ".join([str(int(x)) for x in val_b])
        elif isinstance(val_b, float):
            val_b = f"{val_b:.2f}"

        # Use extra padding for Multi-Year Cash Flow
        if key == "Multi-Year Cash Flow":
            table_data.append([Paragraph(key, normal_style),
                               Paragraph(val_a, normal_style),
                               Paragraph(val_b, normal_style)])
        else:
            table_data.append([key, val_a, val_b])

    # Render the table
    col_widths = [200, 150, 150]
    comparison_table = Table(table_data, colWidths=col_widths)
    comparison_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
        # ✅ Center just the "Multi-Year Cash Flow" row label
    for row_index, row in enumerate(table_data):
        if row[0] == "Multi-Year Cash Flow":
            table.setStyle(TableStyle([
                ('ALIGN', (0, row_index), (0, row_index), 'CENTER'),
            ]))
    elements.append(comparison_table)
    elements.append(Spacer(1, 12))

    # Verdict Section
    grade_a = metrics_a.get("Grade", "N/A")
    grade_b = metrics_b.get("Grade", "N/A")
    verdict_text = "(AI-generated grade based on estimated ROI, cash flow, and risk factors. Informational only.)"

    verdicts = [
        Paragraph(f"■ AI Verdict for Property A:<br/><b>This is a {grade_a}-grade investment.</b>", verdict_styles.get(grade_a, normal_style)),
        Paragraph(f"■ AI Verdict for Property B:<br/><b>This is a {grade_b}-grade investment.</b>", verdict_styles.get(grade_b, normal_style)),
        Spacer(1, 6),
        Paragraph(verdict_text, ParagraphStyle('small', fontSize=10, textColor=colors.black))
    ]
    elements.extend(verdicts)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
