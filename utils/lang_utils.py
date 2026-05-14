from configs.i18n_config import DEFAULT_LANG


def get_lang() -> str:
    """Get current UI language from Streamlit session state, fallback to DEFAULT_LANG."""
    try:
        import streamlit as st
        return st.session_state.get("lang", DEFAULT_LANG)
    except Exception:
        return DEFAULT_LANG
