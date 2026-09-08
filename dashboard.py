from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Lumina Nest", page_icon="LN", layout="wide", initial_sidebar_state="expanded")

from auth_page.forgot import show_forgot
from auth_page.login import show_login
from auth_page.register import show_register
from modules.home import show as home_page
from modules.prediction import show as prediction_page, show_results


def _load_styles():
    css_file = Path(__file__).resolve().parent / "static" / "css" / "style.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


DEFAULTS = {"logged_in": False, "username": "", "full_name": "", "login_greeting": "", "page": "home", "auth_page": "login"}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

_load_styles()

if not st.session_state.logged_in:
    {"login": show_login, "register": show_register, "forgot": show_forgot}.get(
        st.session_state.auth_page, show_login
    )()
    st.stop()


def _navigate(label, destination, icon, reset_estimate=False):
    """Render one sidebar item, with the current page visibly selected."""
    active = st.session_state.page == destination
    if st.button(f"{icon}  {label}", type="primary" if active else "secondary", width='stretch'):
        if reset_estimate:
            st.session_state.flow_step = 1
            st.session_state.project = {}
            st.session_state.prediction_result = None
            st.session_state.pop("live_project_location", None)
            st.session_state.pop("project_site_location", None)
            st.session_state.pop("project_site_confirmed", None)
        st.session_state.page = destination
        st.rerun()

with st.sidebar:
    st.title("Lumina Nest")
    st.caption("Plan with clarity")
    st.divider()
    st.write(f"Signed in as **{st.session_state.username.title()}**")
    _navigate("Overview", "home", "◈")
    _navigate("New estimate", "prediction", "＋", reset_estimate=True)
    _navigate("My projects", "projects", "◫")
    _navigate("Expense tracking", "expenses", "◷")
    _navigate("Contractor quotes", "quotes", "⚖")
    st.caption("YOUR PLAN")
    _navigate("Estimate summary", "results", "▣")
    with st.expander("More details"):
        _navigate("Cost details", "costs", "₹")
        _navigate("Transportation", "transportation", "↔")
        _navigate("Materials", "materials", "⇄")
        _navigate("Material recommendation", "smart_materials", "✦")
        _navigate("Project guidance", "recommendations", "▤")
        _navigate("PDF report", "report", "⇩")
        _navigate("History", "history", "↺")
    st.divider()
    if st.button("Log out", width='stretch'):
        for key in list(st.session_state):
            del st.session_state[key]
        for key, value in DEFAULTS.items():
            st.session_state[key] = value
        st.rerun()

if st.session_state.page == "prediction":
    prediction_page()
elif st.session_state.page == "results":
    show_results("overview")
elif st.session_state.page == "costs":
    show_results("costs")
elif st.session_state.page == "transportation":
    show_results("transportation")
elif st.session_state.page == "materials":
    show_results("materials")
elif st.session_state.page == "smart_materials":
    show_results("smart_materials")
elif st.session_state.page == "recommendations":
    show_results("recommendations")
elif st.session_state.page == "report":
    show_results("report")
elif st.session_state.page == "history":
    show_results("history")
elif st.session_state.page == "projects":
    show_results("projects")
elif st.session_state.page == "expenses":
    show_results("expenses")
elif st.session_state.page == "quotes":
    show_results("quotes")
else:
    home_page()
