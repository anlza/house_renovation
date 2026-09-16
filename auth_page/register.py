import streamlit as st
import textwrap
import auth


def show_register():
    st.markdown(
        textwrap.dedent("""
        <div class='auth-brand'>
          <h1>🏠 Lumina Nest</h1>
          <p>Start with a smarter renovation plan</p>
        </div>
        """),
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        st.markdown(
            textwrap.dedent("""
            <div class='auth-visual'>
              <div><b>YOUR PLAN STARTS HERE</b></div>
              <div>
                <h2>Create one place for every renovation decision.</h2>
                <p>Save estimates, compare material choices, review transportation and keep your planning history together.</p>
              </div>
              <div class='auth-points'>
                <div class='auth-point'>✦ AI prediction</div>
                <div class='auth-point'>⌂ Exact work site</div>
                <div class='auth-point'>▤ Contractor quotes</div>
                <div class='auth-point'>⇩ PDF report</div>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            st.subheader("Create your account")
            st.caption("Save your renovation plans and return to them anytime.")
            full_name = st.text_input("Full name", placeholder="Enter your full name", key="reg_fullname")
            username = st.text_input("Username", placeholder="Choose a username", key="reg_username")
            password = st.text_input("Password", type="password", placeholder="Create a password", key="reg_password")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm your password", key="reg_confirm")
            if st.button("Create account →", type="primary", width="stretch", key="create_account_btn"):
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
            if st.button("← Back to sign in", width="stretch", key="goto_login"):
                st.session_state.auth_page = "login"
                st.rerun()
    st.markdown("<p class='auth-note'>A calm interface for a complex renovation decision.</p>", unsafe_allow_html=True)
