from pathlib import Path

import streamlit as st

import auth


def load_css():
    css = Path("static/css/style.css")
    if css.exists():
        st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def show_forgot():
    load_css()
    st.markdown("<div class='auth-brand'><h1>Lumina Nest</h1><p>AI-powered home renovation planner</p></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.container(border=True):
            st.subheader("🔑 Reset your password")
            st.caption("Choose a new password to regain access to your account.")
            username = st.text_input("Username", placeholder="Enter your username", key="forgot_username")
            new_password = st.text_input("New password", type="password", placeholder="Enter new password", key="forgot_new_password")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm new password", key="forgot_confirm_password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Update password", type="primary", use_container_width=True, key="update_password_btn"):
                if not username.strip():
                    st.error("Please enter your username.")
                elif len(new_password) < 6:
                    st.error("Password must contain at least 6 characters.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = auth.reset_password(username, new_password)
                    if success:
                        st.success("Password updated successfully.")
                        st.session_state.username = username
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(message)
            st.divider()
            if st.button("Back to sign in", use_container_width=True, key="back_to_login_btn"):
                st.session_state.auth_page = "login"
                st.rerun()
