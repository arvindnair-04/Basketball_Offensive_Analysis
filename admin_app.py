from __future__ import annotations

import streamlit as st

from admin_auth import (
    authenticate_admin,
    clear_admin_session,
    initialize_admin_database,
    initialize_admin_session,
    is_admin_logged_in,
    set_admin_session,
)
from usage_tracking import initialize_usage_tracking
from ui import inject_theme

st.set_page_config(
    page_title="Basketball Scouting · Admin",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_usage_tracking()
initialize_admin_database()
initialize_admin_session()
inject_theme()


def admin_login_page() -> None:
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown(
            """
            <div style="text-align:center;padding-top:4rem;">
              <div style="font-size:3.5rem;">🔐</div>
              <h1>Admin Analytics</h1>
              <p>Separate administrator access for product-usage analytics.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("admin_login_form"):
            username = st.text_input("Admin username")
            password = st.text_input("Admin password", type="password")
            submitted = st.form_submit_button("Log in as administrator", type="primary", use_container_width=True)
        if submitted:
            if authenticate_admin(username, password):
                set_admin_session(username)
                st.rerun()
            else:
                st.error("Incorrect administrator username or password.")
        st.caption("This login is separate from all scout/user accounts.")


def admin_logout() -> None:
    clear_admin_session()
    st.rerun()


if not is_admin_logged_in():
    admin_login_page()
else:
    with st.sidebar:
        st.markdown("## 🔐 Administration")
        st.write(f"Signed in as **{st.session_state.admin_username}**")
        st.caption("Product usage analytics")
        st.divider()
        if st.button("Log out of admin", use_container_width=True):
            admin_logout()
    admin_page = st.Page("pages/admin_analytics.py", title="Admin Analytics", icon=":material/analytics:", default=True)
    st.navigation([admin_page]).run()
