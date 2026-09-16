import streamlit as st


def show_landing():
    """Clean, spacious landing screen for the Lumina Nest presentation demo."""
    landing_html = """
<section class="ln-landing">
  <div class="ln-brand-row">
    <div class="ln-brand"><span class="ln-house">🏠</span><span>Lumina Nest</span></div>
    <div class="ln-tag">AI-Powered House Renovation Budget Planner</div>
  </div>
  <div class="ln-hero-card">
    <div class="ln-hero-copy">
      <div class="ln-eyebrow">PLAN · ESTIMATE · RENOVATE</div>
      <h1>Make your home<br><em>feel like home.</em></h1>
      <p class="ln-lead">Plan your renovation with a clear budget, smart material choices,
      realistic transport costs and an AI-powered timeline — all in one place.</p>
      <div class="ln-actions">
        <div class="ln-action-primary">Start planning <span>→</span></div>
        <div class="ln-action-secondary">Already planning? <strong>Sign in</strong></div>
      </div>
      <div class="ln-features">
        <div><span>₹</span><b>Cost prediction</b><small>Know your budget early</small></div>
        <div><span>⌂</span><b>Material planning</b><small>Quantity &amp; quality insights</small></div>
        <div><span>↗</span><b>Transport estimate</b><small>Supplier to work site</small></div>
      </div>
    </div>
    <div class="ln-hero-image">
      <div class="ln-image-label"><span>✦</span> Your renovation journey starts here</div>
    </div>
  </div>
  <div class="ln-bottom-note">
    <span>🏡</span> Build better homes&nbsp;&nbsp;·&nbsp;&nbsp;Plan smarter&nbsp;&nbsp;·&nbsp;&nbsp;Live brighter.
  </div>
</section>
"""
    st.markdown(landing_html, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        if st.button("Start planning  →", type="primary", width="stretch", key="landing_login"):
            st.session_state.auth_page = "register"
            st.rerun()
    with c2:
        if st.button("Already have an account?  Sign in", width="stretch", key="landing_signin"):
            st.session_state.auth_page = "login"
            st.rerun()
