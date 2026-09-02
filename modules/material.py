"""Material comparison and decision-support views."""

import re
import pandas as pd
import plotly.express as px
import streamlit as st

from services.recommendations import MATERIAL_OPTIONS, MATERIAL_LIFESPAN_NOTES, suggested_quality


def _normalise_material(name):
    if not name:
        return None
    return "Tiles" if name == "Tile" else str(name)


def _available(material_names):
    names = [_normalise_material(name) for name in (material_names or [])]
    return list(dict.fromkeys(name for name in names if name in MATERIAL_OPTIONS))


def _rate_value(rate):
    match = re.search(r"\d+(?:\.\d+)?", str(rate).replace(",", ""))
    return float(match.group()) if match else 0.0


def show_comparison(selected_quality, budget_status, difference, material_names=None):
    available = _available(material_names)
    st.subheader("Compare required material options")
    st.caption("Only materials actually included in the selected renovation are shown.")

    if not available:
        st.info("Material comparison will appear after the estimate identifies the renovation-specific materials.")
        return

    material = st.selectbox("Material to compare", available, key="comparison_material")
    options = MATERIAL_OPTIONS[material]
    chart_rows = pd.DataFrame([
        {"Quality": q, "Reference market rate (INR)": _rate_value(rate), "Brand / supplier": brand}
        for q, (brand, rate, _) in options.items()
    ])
    chart = px.bar(
        chart_rows, x="Quality", y="Reference market rate (INR)", color="Quality",
        text="Reference market rate (INR)", hover_data={"Brand / supplier": True},
    )
    chart.update_layout(showlegend=False, height=260, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

    rows = []
    for q, (brand, rate, life) in options.items():
        rows.append({
            "Quality": q,
            "Brand / supplier": brand,
            "Reference market rate": rate,
            "Typical service life": life,
            "Decision": "Current estimate" if q == selected_quality else "Alternative",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.info(f"**Planning note for {material}:** {MATERIAL_LIFESPAN_NOTES.get(material, 'Typical planning range only.')}")
    st.caption("Reference market rates are planning values, not live quotations. Confirm local supplier price and product availability before purchase.")


def show_recommendation(selected_quality, budget_status, difference, material_details=None):
    recommended = suggested_quality(selected_quality, budget_status, difference)
    details = material_details or []
    current_cost = sum(float(item.get("Estimated material cost (INR)", 0) or 0) for item in details)

    st.subheader("Recommended material plan")
    a, b, c = st.columns(3)
    a.metric("Estimate quality used", selected_quality)
    b.metric("Suggested alternative", recommended)
    c.metric("Recommended material categories", len(details))

    if recommended != selected_quality:
        st.info(
            f"The current estimate remains based on your selected **{selected_quality}** quality. "
            f"**{recommended}** is shown only as an alternative for comparison; it does not silently change the total cost."
        )
    else:
        st.caption("The current estimate and the recommendation use the same selected quality level.")

    rows = []
    for item in details:
        material = _normalise_material(item.get("Material"))
        if material not in MATERIAL_OPTIONS:
            continue
        brand, rate, life = MATERIAL_OPTIONS[material][selected_quality]
        alt_brand, alt_rate, _ = MATERIAL_OPTIONS[material][recommended]
        rows.append({
            "Material": material,
            "Used for": item.get("Why included", "Required renovation work"),
            "Estimate brand / supplier": item.get("Recommended brand / company", brand),
            "Quality used": selected_quality,
            "Rate used for estimate": item.get("Reference market rate", rate),
            "Estimated cost (INR)": round(float(item.get("Estimated material cost (INR)", 0) or 0)),
            "Typical service life": life,
            "Alternative": f"{recommended}: {alt_brand} ({alt_rate})" if recommended != selected_quality else "Current plan",
        })

    if rows:
        st.subheader("Materials required for your selected work")
        st.dataframe(
            pd.DataFrame(rows).style.format({"Estimated cost (INR)": "INR {:,.0f}"}),
            hide_index=True, use_container_width=True,
        )
        st.caption(
            "The rate shown in this table is the same planning rate used to calculate the displayed quantity and material cost. "
            "Service-life ranges are planning estimates, not warranties."
        )
    else:
        st.info("No matching material information is available.")

    if budget_status == "Over Budget":
        st.warning(f"The project is INR {difference:,.0f} above budget. Compare alternatives, but do not reduce safety-critical work solely to meet the budget.")
    else:
        reserve = max(0, difference)
        st.success(f"Budget reserve: INR {reserve:,.0f}. Keep a contingency before choosing upgrades.")


def show(selected_quality, budget_status, difference):
    show_recommendation(selected_quality, budget_status, difference)
