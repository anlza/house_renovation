from datetime import datetime

import streamlit as st


def show():
    st.markdown("<div class='app-kicker'>Lumina Nest · Your renovation companion</div>", unsafe_allow_html=True)
    st.title("Make every renovation decision feel clearer")
    st.markdown(
        "<section class='app-hero'><h2>Plan first. Build with confidence.</h2>"
        "<p>Turn your renovation idea into a clear plan—with practical quantities, transparent costs, route-aware delivery and a budget you can discuss with confidence.</p></section>",
        unsafe_allow_html=True,
    )
    username = st.session_state.get("username", "User")
    full_name = st.session_state.get("full_name", username.title())
    greeting = st.session_state.get("login_greeting", f"Welcome back, {full_name} 👋")
    left, right = st.columns([3, 1])
    with left:
        st.subheader(greeting)
        st.caption("A few thoughtful details are all it takes to turn your property information into a practical renovation plan.")
    with right:
        st.metric("Today", datetime.now().strftime("%d %b %Y"))

    st.markdown("<div class='section-title'><span>✦</span> Start here</div><p class='section-note'>Create a plan, revisit an estimate, or take a quick tour of the workflow.</p>", unsafe_allow_html=True)
    first, second, third = st.columns(3)
    with first:
        if st.button("✨ Create a new estimate", type="primary", width='stretch'):
            st.session_state.flow_step = 1
            st.session_state.project = {}
            st.session_state.prediction_result = None
            st.session_state.pop("live_project_location", None)
            st.session_state.pop("project_site_location", None)
            st.session_state.pop("project_site_confirmed", None)
            st.session_state.page = "prediction"
            st.rerun()
    with second:
        if st.button("▣ View my estimate", width='stretch'):
            st.session_state.page = "results"
            st.rerun()
    with third:
        if st.button("◌ How it works", width='stretch'):
            st.info("Choose the work you need, add the measurements that matter, then explore your cost, materials, timeline and next best steps.")

    st.markdown("<div class='section-title'><span>◈</span> Your planning toolkit</div><p class='section-note'>Everything you need to move from an idea to a well-informed contractor conversation.</p>", unsafe_allow_html=True)
    one, two, three = st.columns(3)
    one.metric("Cost clarity", "Transparent budget")
    two.metric("Timeline", "Plan with time")
    three.metric("Saved plans", "Pick up anytime")
