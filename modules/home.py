from datetime import datetime

import streamlit as st


def show():
    st.markdown("<div class='app-kicker'>Lumina Nest · Project planning workspace</div>", unsafe_allow_html=True)
    st.title("Plan your renovation with confidence")
    st.markdown(
        "<section class='app-hero'><h2>Clear estimates. Better decisions.</h2>"
        "<p>Build a tailored renovation plan, understand the main cost drivers, and make confident budget decisions before you speak with a contractor.</p></section>",
        unsafe_allow_html=True,
    )
    username = st.session_state.get("username", "User")
    full_name = st.session_state.get("full_name", username.title())
    greeting = st.session_state.get("login_greeting", f"Welcome back, {full_name} 👋")
    left, right = st.columns([3, 1])
    with left:
        st.subheader(greeting)
        st.caption("Start a project in a few steps. We will turn your property details into a practical planning estimate.")
    with right:
        st.metric("Today", datetime.now().strftime("%d %b %Y"))

    st.subheader("Quick actions")
    st.markdown("<p class='section-note'>Start a new plan, return to a result, or review the simple workflow.</p>", unsafe_allow_html=True)
    first, second, third = st.columns(3)
    with first:
        if st.button("Create new estimate", type="primary", use_container_width=True):
            st.session_state.flow_step = 1
            st.session_state.project = {}
            st.session_state.prediction_result = None
            st.session_state.pop("live_project_location", None)
            st.session_state.pop("project_site_location", None)
            st.session_state.pop("project_site_confirmed", None)
            st.session_state.page = "prediction"
            st.rerun()
    with second:
        if st.button("View estimate summary", use_container_width=True):
            st.session_state.page = "results"
            st.rerun()
    with third:
        if st.button("How it works", use_container_width=True):
            st.info("Choose the renovation type, answer a short set of relevant questions, then review your estimate, materials, timeline and recommended next steps.")

    st.subheader("Your planning toolkit")
    st.markdown("<p class='section-note'>Everything needed to move from an initial idea to a well-informed contractor conversation.</p>", unsafe_allow_html=True)
    one, two, three = st.columns(3)
    one.metric("Cost clarity", "Budget breakdown")
    two.metric("Timeline", "Estimated duration")
    three.metric("Saved plans", "Return anytime")
