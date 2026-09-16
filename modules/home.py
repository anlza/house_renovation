from datetime import datetime

import streamlit as st


def show():
    username = st.session_state.get("username", "User")
    full_name = st.session_state.get("full_name", username.title())
    greeting = st.session_state.get("login_greeting", f"Welcome back, {full_name} 👋")

    st.markdown("<div class='app-kicker'>🏠 Lumina Nest · Your renovation workspace</div>", unsafe_allow_html=True)
    st.markdown(
        "<section class='app-hero'><div class='eyebrow' style='color:#b7df79!important;'>PLAN · ESTIMATE · RENOVATE</div>"
        "<h2>Make your renovation decisions feel simpler.</h2>"
        "<p>From your work-site and material supplier to cost, transport and timeline — Lumina Nest brings the whole plan together.</p></section>",
        unsafe_allow_html=True,
    )

    st.subheader(greeting)
    st.caption("Choose a starting point. The planner will only ask for information relevant to your renovation.")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✦  Create new estimate", type="primary", width="stretch"):
            st.session_state.flow_step = 1
            st.session_state.project = {}
            st.session_state.prediction_result = None
            st.session_state.pop("live_project_location", None)
            st.session_state.pop("project_site_location", None)
            st.session_state.pop("project_site_confirmed", None)
            st.session_state.page = "prediction"
            st.rerun()
    with c2:
        if st.button("▣  View latest estimate", width="stretch"):
            st.session_state.page = "results"
            st.rerun()
    with c3:
        if st.button("◌  See how it works", width="stretch"):
            st.info("Choose renovation → add real measurements → confirm work and supplier locations → set budget → run AI prediction → review cost, materials, transport and recommendations.")

    st.markdown("<div class='section-title'><span>◈</span> Your planning toolkit</div>"
                "<p class='section-note'>Everything important after the prediction is organised into focused views.</p>", unsafe_allow_html=True)

    cols = st.columns(4)
    cards = [
        ("✦", "AI cost prediction", "Estimate renovation cost and duration from your project inputs."),
        ("₹", "Transparent costs", "See materials, labour, transport, charges and contingency separately."),
        ("↔", "Route-aware transport", "Use the supplier-to-work-site route to estimate delivery cost."),
        ("▤", "Planning insights", "Review material choices, timeline, budget health and next steps."),
    ]
    for col, (icon, title, text) in zip(cols, cards):
        with col:
            st.markdown(f"<div class='insight-card'><div class='icon'>{icon}</div><div class='title'>{title}</div><div class='text'>{text}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'><span>✓</span> A simple 5-step journey</div>", unsafe_allow_html=True)
    steps = ["Choose work", "House details", "Requirements", "Locations", "Budget + AI"]
    cols = st.columns(5)
    for i, (col, label) in enumerate(zip(cols, steps), 1):
        with col:
            st.markdown(f"<div class='insight-card' style='min-height:82px'><div style='font-size:.7rem;color:#6c8c74;font-weight:800;'>STEP {i}</div><div class='title'>{label}</div></div>", unsafe_allow_html=True)

