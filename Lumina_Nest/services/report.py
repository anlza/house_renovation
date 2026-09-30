"""Small dependency-free PDF report builder for project summaries."""

from datetime import date


def _escape(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _line(text, x, y, size=10, bold=False, color="0 0 0"):
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf {color} rg 1 0 0 1 {x} {y} Tm ({_escape(text)}) Tj ET"


def create_project_pdf(report, breakdown, status, difference, recommended_quality, suggestions):
    """Create a clean one-page PDF using only the Python standard library."""
    lines = [
        _line("LUMINA NEST", 48, 790, 21, True, "0.08 0.15 0.30"),
        _line("Renovation planning report", 48, 768, 11, False, "0.35 0.40 0.48"),
        "0.12 0.47 0.86 RG 48 754 m 547 754 l S",
        _line(f"Prepared on: {date.today().strftime('%d %B %Y')}", 48, 735, 9, False, "0.35 0.40 0.48"),
        _line("PROJECT DETAILS", 48, 704, 12, True, "0.08 0.15 0.30"),
    ]
    project_rows = [
        ("User", report.get("User", "Account holder")), ("House details", report.get("House Details", "Project details")),
        ("Renovation type", report["Renovation Type"]), ("Location", report["Location"]),
        ("Available budget", f"INR {report['Available Budget']:,.0f}"),
        ("Estimated duration", f"{report['Estimated Duration (Days)']} days"),
    ]
    y = 682
    for label, value in project_rows:
        lines.extend([_line(label, 54, y, 10, True), _line(value, 245, y, 10)])
        y -= 23
    lines.append(_line("ESTIMATED COST BREAKDOWN", 48, 573, 12, True, "0.08 0.15 0.30"))
    y = 551
    for label, amount in breakdown.items():
        lines.extend([_line(label, 54, y), _line(f"INR {amount:,.0f}", 420, y, 10, True)])
        y -= 22
    lines.extend([
        "0.75 G 48 438 m 547 438 l S",
        _line("TOTAL ESTIMATED BUDGET", 54, 417, 12, True, "0.08 0.15 0.30"),
        _line(f"INR {report['Total Cost']:,.0f}", 410, 417, 12, True, "0.08 0.15 0.30"),
        _line(f"Expected range: INR {report['Total Cost']*.90:,.0f} - INR {report['Total Cost']*1.10:,.0f}", 54, 396, 9),
        _line("BUDGET CHECK", 48, 372, 12, True, "0.08 0.15 0.30"),
    ])
    message = (f"Within budget: you may have INR {difference:,.0f} remaining."
               if status == "Within Budget" else f"Over budget by INR {difference:,.0f}. Consider the suggested material options.")
    lines.extend([
        _line(status, 54, 348, 12, True, "0.08 0.45 0.20" if status == "Within Budget" else "0.72 0.13 0.13"),
        _line(message, 54, 326),
        _line("RECOMMENDED MATERIAL PLAN", 48, 290, 12, True, "0.08 0.15 0.30"),
        _line(f"Suggested quality: {recommended_quality}", 54, 268, 10, True),
        _line("PROJECT TIPS", 48, 230, 12, True, "0.08 0.15 0.30"),
        _line("Preliminary estimate only: site conditions, market prices, contractor charges and availability may vary.", 48, 74, 8, False, "0.35 0.40 0.48"),
    ])
    tip_y = 208
    for suggestion in suggestions[:3]:
        action = suggestion[0] if isinstance(suggestion, tuple) else suggestion
        lines.append(_line(f"- {action}", 54, tip_y, 9))
        tip_y -= 18
    # A concise visual cost page makes the report easier to scan in a client meeting.
    chart_lines = [
        _line("LUMINA NEST", 48, 790, 21, True, "0.08 0.15 0.30"),
        _line("Cost snapshot", 48, 768, 11, False, "0.35 0.40 0.48"),
        "0.12 0.47 0.86 RG 48 754 m 547 754 l S",
        _line("ESTIMATED COST VISUAL", 48, 714, 13, True, "0.08 0.15 0.30"),
        _line("Each bar shows its share of the total estimate.", 48, 694, 10, False, "0.35 0.40 0.48"),
    ]
    chart_items = [
        ("Renovation work", report["Renovation Cost"]),
        ("Labour", report["Labour Cost"]),
        ("Transportation", report["Transportation Cost"]),
    ]
    largest = max(amount for _, amount in chart_items) or 1
    y = 630
    for label, amount in chart_items:
        width = max(8, round(360 * amount / largest))
        chart_lines.append(_line(label, 48, y + 20, 10, True, "0.12 0.18 0.29"))
        chart_lines.append(_line(f"INR {amount:,.0f}", 430, y + 20, 10, True, "0.12 0.18 0.29"))
        chart_lines.append(f"0.12 0.47 0.86 rg 48 {y} {width} 14 re f")
        y -= 85
    chart_lines.extend([
        _line("BUDGET DECISION", 48, 318, 13, True, "0.08 0.15 0.30"),
        _line(status, 48, 293, 12, True, "0.08 0.45 0.20" if status == "Within Budget" else "0.72 0.13 0.13"),
        _line(f"Total estimated budget: INR {report['Total Cost']:,.0f}", 48, 270, 11),
        _line(f"Available budget: INR {report['Available Budget']:,.0f}", 48, 250, 11),
        _line("Prepared by Lumina Nest · Confirm final rates with local contractors.", 48, 74, 9, False, "0.35 0.40 0.48"),
    ])
    stream = "\n".join(lines).encode("latin-1", "replace")
    chart_stream = "\n".join(chart_lines).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 7 0 R /F2 8 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 7 0 R /F2 8 0 R >> >> /Contents 6 0 R >>",
        b"<< /Length " + str(len(chart_stream)).encode() + b" >>\nstream\n" + chart_stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)
