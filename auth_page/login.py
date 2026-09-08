from pathlib import Path

import streamlit as st

import auth


def load_css():
    css = Path("static/css/style.css")
    if css.exists():
        st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def show_login():
    load_css()
    st.markdown("<div class='auth-brand'><h1>Lumina Nest</h1><p>AI-powered home renovation planner</p></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.container(border=True):
            st.subheader("🔐 Sign in")
            st.caption("Access your saved renovation plans and estimates.")
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign in", type="primary", width='stretch', key="login_btn"):
                ok, first_login = auth.verify_login_with_status(username, password)
                if ok:
                    full_name = auth.get_full_name(username)
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.full_name = full_name
                    st.session_state.login_greeting = (
                        f"Hi, {full_name} 👋" if first_login else f"Welcome back, {full_name} 👋"
                    )
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Forgot password?", width='stretch', key="forgot_btn"):
                    st.session_state.auth_page = "forgot"
                    st.rerun()
            with c2:
                if st.button("Create account", width='stretch', key="register_btn"):
                    st.session_state.auth_page = "register"
                    st.rerun()
    st.markdown("<p class='auth-note'>A clearer way to plan renovation costs, materials and timelines.</p>", unsafe_allow_html=True)
