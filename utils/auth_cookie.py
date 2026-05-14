"""
Cookie-based login persistence.
Saves/restores username across browser refreshes using extra-streamlit-components.
"""
import streamlit as st

_COOKIE_KEY = "agent_uid"
_CM_KEY     = "_auth_cookie_manager"
_EXPIRY_DAYS = 30


def get_cookie_manager():
    try:
        import extra_streamlit_components as stx
        return stx.CookieManager(key=_CM_KEY)
    except ImportError:
        return None


def save_login_cookie(user_id: str) -> None:
    from datetime import datetime, timedelta
    mgr = get_cookie_manager()
    if mgr is None:
        return
    try:
        mgr.set(_COOKIE_KEY, user_id,
                expires_at=datetime.now() + timedelta(days=_EXPIRY_DAYS))
    except Exception as e:
        print(f"[Cookie] Failed to save login cookie: {e}")


def clear_login_cookie() -> None:
    mgr = get_cookie_manager()
    if mgr is None:
        return
    try:
        mgr.delete(_COOKIE_KEY)
    except Exception:
        pass


def restore_from_cookie(store) -> bool:
    """
    Try to restore login state from cookie.
    Returns True if restored successfully.
    Must be called before st.stop() / render_login body.
    """
    if st.session_state.get("user_id"):
        return True

    mgr = get_cookie_manager()
    if mgr is None:
        return False

    try:
        saved_uid = mgr.get(cookie=_COOKIE_KEY)
    except Exception:
        return False

    if not saved_uid:
        return False

    user_uid = store.get_user_uid(saved_uid)
    if not user_uid:
        clear_login_cookie()
        return False

    st.session_state.user_id            = saved_uid
    st.session_state.user_uid           = user_uid
    st.session_state.lang               = store.get_user_lang(saved_uid)
    st.session_state.current_session_id = None
    return True
