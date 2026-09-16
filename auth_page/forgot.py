import streamlit as st
import textwrap
import auth


def show_forgot():
    st.markdown(
        textwrap.dedent("""
        <div class='auth-brand'>
          <h1>🏠 Lumina Nest</h1>
          <p>Reset your account securely</p>
        </div>
        """),
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        st.markdown(
            textwrap.dedent("""
            <div class='auth-visual'>
              <div><b>ACCOUNT RECOVERY</b></div>
              <div>
                <h2>Get back to your renovation plans.</h2>
                <p>Use the verification flow to choose a new password and return to your planning workspace.</p>
              </div>
              <div class='auth-points'>
                <div class='auth-point'>✓ One-time code</div>
                <div class='auth-point'>✓ 15-minute expiry</div>
                <div class='auth-point'>✓ New password</div>
                <div class='auth-point'>✓ Continue planning</div>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            st.subheader("Reset your password")
            st.caption("Verify a one-time code before choosing a new password.")
            username = st.text_input("Username", placeholder="Enter your username", key="forgot_username")
            code = st.text_input("Verification code", placeholder="6-digit code", key="forgot_code")
            new_password = st.text_input("New password", type="password", placeholder="Enter new password", key="forgot_new_password")
            confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm new password", key="forgot_confirm_password")
            if st.button("Send verification code", width="stretch", key="send_reset_code"):
                ok, message, demo_code = auth.begin_password_reset(username)
                if ok:
                    st.session_state.reset_demo_code = demo_code
                    st.success(message)
                    st.info(f"Demo delivery code: {demo_code}. In production, connect this step to your email/SMS provider.")
                else:
                    st.success(message)
            if st.button("Verify and update password →", type="primary", width="stretch", key="update_password_btn"):
                if not username.strip():
                    st.error("Please enter your username.")
                elif len(new_password) < 8:
                    st.error("Password must contain at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = auth.complete_password_reset(username, code, new_password)
                    if success:
                        st.success("Password updated successfully.")
                        st.session_state.username = username
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(message)
            st.divider()
            if st.button("← Back to sign in", width="stretch", key="back_to_login_btn"):
                st.session_state.auth_page = "login"
                st.rerun()
