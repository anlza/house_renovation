import streamlit as st
import textwrap
import auth


def show_login():
    st.markdown(
        textwrap.dedent("""
        <div class='auth-brand'>
          <h1>🏠 Lumina Nest</h1>
          <p>AI-powered house renovation budget planner</p>
        </div>
        """),
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        st.markdown(
            textwrap.dedent("""
            <div class='auth-visual'>
              <div><b>SMARTER RENOVATION. BRIGHTER FUTURE.</b></div>
              <div>
                <h2>Welcome back to your renovation journey.</h2>
                <p>Pick up your saved plans, review estimates and continue making decisions for your home.</p>
              </div>
              <div class='auth-points'>
                <div class='auth-point'>✓ Saved estimates</div>
                <div class='auth-point'>✓ Cost breakdown</div>
                <div class='auth-point'>✓ Material insights</div>
                <div class='auth-point'>✓ Project history</div>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            st.subheader("Welcome back")
            st.caption("Sign in to continue planning your renovation.")
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            if st.button("Sign in →", type="primary", width="stretch", key="login_btn"):
                ok, first_login = auth.verify_login_with_status(username, password)
                if ok:
                    full_name = auth.get_full_name(username)
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.full_name = full_name
                    st.session_state.login_greeting = f"Hi, {full_name} 👋" if first_login else f"Welcome back, {full_name} 👋"
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Forgot password?", width="stretch", key="forgot_btn"):
                    st.session_state.auth_page = "forgot"
                    st.rerun()
            with c2:
                if st.button("Create account", width="stretch", key="register_btn"):
                    st.session_state.auth_page = "register"
                    st.rerun()
    st.markdown("<p class='auth-note'>Your renovation data stays organised in one planning workspace.</p>", unsafe_allow_html=True)
