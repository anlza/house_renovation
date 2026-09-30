"""Plain-language material comparison and renovation guidance.

The catalogue contains planning reference products/rates. It is intentionally
separate from the ML feature prices: the ML model predicts the overall cost,
while this catalogue makes the renovation-specific material allocation
transparent and internally consistent.
"""

MATERIAL_OPTIONS = {
    "Cement": {
        "Economy": ("ACC Cement", "INR 380 / 50 kg bag", "50-70+ years"),
        "Standard": ("UltraTech Cement", "INR 420 / 50 kg bag", "60-80+ years"),
        "Premium": ("UltraTech OPC 53", "INR 470 / 50 kg bag", "75-100+ years"),
    },
    "Steel": {
        "Economy": ("Kamdhenu TMT", "INR 62 / kg", "40-50+ years"),
        "Standard": ("TATA TMT", "INR 70 / kg", "50-70+ years"),
        "Premium": ("JSW Neosteel", "INR 78 / kg", "60-75+ years"),
    },
    "Sand": {
        "Economy": ("Local screened construction sand", "INR 48 / cubic ft", "Permanent base material"),
        "Standard": ("Verified washed construction sand", "INR 55 / cubic ft", "Permanent base material"),
        "Premium": ("Graded washed construction sand", "INR 65 / cubic ft", "Permanent base material"),
    },
    "Brick": {
        "Economy": ("Local clay brick supplier", "INR 8 / piece", "50+ years"),
        "Standard": ("Machine-made clay brick supplier", "INR 10 / piece", "50+ years"),
        "Premium": ("High-strength facing brick supplier", "INR 14 / piece", "75+ years"),
    },
    "Paint": {
        "Economy": ("Berger WeatherCoat", "INR 290 / litre", "4-5 years"),
        "Standard": ("Asian Paints Apex", "INR 340 / litre", "6-8 years"),
        "Premium": ("Asian Paints Royale", "INR 520 / litre", "8-10 years"),
    },
    "Primer": {
        "Economy": ("Berger Bison Primer", "INR 180 / litre", "Matches paint cycle"),
        "Standard": ("Asian Paints SmartCare Primer", "INR 230 / litre", "Matches paint cycle"),
        "Premium": ("Asian Paints Premium Primer", "INR 320 / litre", "Matches paint cycle"),
    },
    "Putty": {
        "Economy": ("JK Wall Putty", "INR 28 / kg", "Matches repainting cycle"),
        "Standard": ("Birla White WallCare Putty", "INR 35 / kg", "Matches repainting cycle"),
        "Premium": ("Premium acrylic wall putty", "INR 48 / kg", "Matches repainting cycle"),
    },
    "Tiles": {
        "Economy": ("Somany Tiles", "INR 55 / sq ft", "10-15 years"),
        "Standard": ("Kajaria Tiles", "INR 85 / sq ft", "15-25 years"),
        "Premium": ("Kajaria Premium", "INR 140 / sq ft", "25-40+ years"),
    },
    "Tile Adhesive": {
        "Economy": ("MYK Laticrete Economy", "INR 18 / kg", "15-20 years"),
        "Standard": ("Roff New Construction", "INR 24 / kg", "20-25 years"),
        "Premium": ("MYK Laticrete Premium", "INR 32 / kg", "25+ years"),
    },
    "Wood": {
        "Economy": ("Greenply Plywood", "INR 85 / sq ft", "8-15 years"),
        "Standard": ("CenturyPly", "INR 120 / sq ft", "15-25 years"),
        "Premium": ("Greenlam", "INR 175 / sq ft", "25-40+ years"),
    },
    "Countertop": {
        "Economy": ("Local granite fabricator", "INR 180 / sq ft", "20-30 years"),
        "Standard": ("Branded granite/quartz supplier", "INR 300 / sq ft", "25-40 years"),
        "Premium": ("Premium quartz supplier", "INR 550 / sq ft", "30-50 years"),
    },
    "Waterproofing": {
        "Economy": ("Dr. Fixit basic system", "INR 85 / sq ft", "5-8 years"),
        "Standard": ("Asian Paints SmartCare", "INR 120 / sq ft", "8-12 years"),
        "Premium": ("Fosroc premium system", "INR 180 / sq ft", "12-15 years"),
    },
    "Electrical Cable": {
        "Economy": ("Finolex cable", "INR 55 / metre", "20-25 years"),
        "Standard": ("Polycab cable", "INR 70 / metre", "25-30 years"),
        "Premium": ("Havells cable", "INR 90 / metre", "30+ years"),
    },
    "Switches & Sockets": {
        "Economy": ("Anchor Roma", "INR 180 / point", "8-12 years"),
        "Standard": ("Legrand", "INR 260 / point", "12-18 years"),
        "Premium": ("Schneider Electric", "INR 380 / point", "15-20 years"),
    },
    "MCB & Conduit": {
        "Economy": ("Anchor protection system", "INR 220 / point", "10-15 years"),
        "Standard": ("L&T protection system", "INR 320 / point", "15-20 years"),
        "Premium": ("Schneider protection system", "INR 450 / point", "20+ years"),
    },
    "PVC/CPVC Pipes": {
        "Economy": ("Supreme pipes", "INR 85 / metre", "20-25 years"),
        "Standard": ("Astral pipes", "INR 120 / metre", "25-35 years"),
        "Premium": ("Ashirvad premium pipes", "INR 160 / metre", "30-40 years"),
    },
    "Plumbing Fittings": {
        "Economy": ("Local ISI fittings", "INR 180 / point", "8-12 years"),
        "Standard": ("Jaquar fittings", "INR 320 / point", "12-18 years"),
        "Premium": ("Kohler fittings", "INR 520 / point", "15-20 years"),
    },
    "Sanitary Fixtures": {
        "Economy": ("Cera", "INR 3,500 / set", "10-15 years"),
        "Standard": ("Hindware", "INR 6,000 / set", "15-20 years"),
        "Premium": ("Kohler", "INR 12,000 / set", "20+ years"),
    },
}

MATERIAL_LIFESPAN_NOTES = {
    material: "Typical planning range only; actual performance depends on product specification, installation quality, climate and maintenance."
    for material in MATERIAL_OPTIONS
}
MATERIAL_LIFESPAN_NOTES.update({
    "Cement": "Concrete service life depends mainly on mix design, workmanship, moisture control and structural maintenance.",
    "Sand": "Sand is a base material; service performance depends on the complete construction system rather than the sand alone.",
    "Paint": "Paint normally needs periodic repainting; exposure and surface preparation affect the interval.",
    "Waterproofing": "Waterproofing systems have finite service cycles and must be inspected and maintained.",
})


def suggested_quality(selected_quality, budget_status, budget_remaining=0):
    """Choose a quality tier without silently changing the current estimate."""
    if budget_status == "Within Budget" and selected_quality != "Premium" and budget_remaining >= 50_000:
        return "Premium"
    if budget_status == "Over Budget":
        return {"Premium": "Standard", "Standard": "Economy"}.get(selected_quality, "Economy")
    return selected_quality


def project_suggestions(renovation, season, budget_status, difference, duration, breakdown=None):
    suggestions = [(f"Plan for around {duration} days and keep a small buffer for site checks.",
                    "The timeline includes preparation, trade work and final finishing.")]
    if season == "Monsoon":
        suggestions.append(("Schedule waterproofing and outdoor work on dry days.",
                            "Monsoon weather can delay drying and exterior work."))
    elif renovation in {"Kitchen", "Bathroom", "Plumbing"}:
        suggestions.append(("Confirm plumbing points before finishing work starts.",
                            "Moving hidden services later creates avoidable rework."))
    else:
        suggestions.append(("Get two local contractor quotes before finalising the schedule.",
                            "Local labour rates and availability can differ from a planning estimate."))
    if budget_status == "Over Budget":
        suggestions.append((f"Reduce optional finishes first to close the INR {difference:,.0f} gap.",
                            "Finish upgrades are easier to phase than safety or essential service work."))
        if breakdown:
            largest = max(breakdown, key=breakdown.get)
            suggestions.append((f"Ask for alternatives for {largest.lower()}.",
                                f"It is the largest current cost item at INR {breakdown[largest]:,.0f}."))
    else:
        reserve = min(difference, max(5_000, round(sum(breakdown.values()) * .05))) if breakdown else difference
        suggestions.append((f"Keep INR {reserve:,.0f} of the remaining budget as a contingency.",
                            "Small site changes and supplier-price variations are common during renovation."))
    return suggestions
