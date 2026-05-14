import os
import streamlit as st
from configs.i18n_config import DEFAULT_LANG
from configs.app_config import APP_DISPLAY, APP_SUBTITLE
from utils.auth_cookie import restore_from_cookie, save_login_cookie


def render_login(store):
    """Render login page if not authenticated, then st.stop()."""
    if restore_from_cookie(store):
        return

    if "lang" not in st.session_state:
        st.session_state.lang = DEFAULT_LANG

    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            f"""
            <div style="text-align:center;font-size:3rem">🧬</div>
            <div style="text-align:center;font-size:1.8rem;font-weight:700">{APP_DISPLAY}</div>
            <div style="text-align:center;color:#888;margin-bottom:1.2rem">{APP_SUBTITLE}</div>
            <hr style="border:none;border-top:1px solid rgba(0,0,0,0.1);margin:.8rem 0 1.4rem"/>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            uid = st.text_input("Username", placeholder="Enter your username")
            pwd = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not uid.strip() or not pwd:
                    st.error("Please enter both username and password.")
                elif not store.verify_login(uid.strip(), pwd):
                    st.error("Invalid username or password.")
                else:
                    st.session_state.user_id            = uid.strip()
                    st.session_state.user_uid           = store.get_user_uid(uid.strip())
                    st.session_state.lang               = store.get_user_lang(uid.strip())
                    st.session_state.current_session_id = None
                    save_login_cookie(uid.strip())
                    st.rerun()

        st.markdown(
            '<div style="text-align:center;color:#aaa;font-size:0.8rem;margin-top:1rem">Powered by LangGraph · Streamlit</div>',
            unsafe_allow_html=True,
        )

    st.stop()
