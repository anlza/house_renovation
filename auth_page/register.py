from pathlib import Path

import streamlit as st

import auth


def load_css():
    css = Path("static/css/style.css")
    if css.exists():
        st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def show_register():
    load_css()
    st.markdown("<div class='auth-brand'><h1>Lumina Nest</h1><p>AI-powered home renovation planner</p></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.container(border=True):
            st.subheader("✨ Create your account")
            st.caption("Save estimates and return to your project decisions anytime.")
            full_name = st.text_input("Full name", placeholder="Enter your full name", key="reg_fullname")
            username = st.text_input("Username", placeholder="Choose a username", key="reg_username")
            password = st.text_input("Password", type="password", placeholder="Create a password", key="reg_password")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm your password", key="reg_confirm")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create account", type="primary", use_container_width=True, key="create_account_btn"):
                if not full_name.strip():
                    st.error("Please enter your full name.")
                elif not username.strip():
                    st.error("Please enter a username.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = auth.register_user(username=username, full_name=full_name, password=password)
                    if success:
                        st.success("Registration successful. Please sign in to continue.")
                        st.session_state.username = username
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(message)
            st.divider()
            if st.button("Back to sign in", use_container_width=True, key="goto_login"):
                st.session_state.auth_page = "login"
                st.rerun()
