import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime

from agent_graph.graph import create_agent_graph
from storage.session_store import get_session_store
from storage.file_manager import get_file_manager
from configs.runtime_config import DEFAULT_USERS
from configs.app_config import APP_DISPLAY, APP_PASCAL
from utils.i18n import _

from ui.login   import render_login
from ui.sidebar import render_sidebar, switch_session
from ui.chat    import (
    render_history,
    run_first_segment,
    render_prereq_reviewer, run_prereq_review_segment,
    render_review, run_second_segment,
)

# streamlit run ui/app_ui.py --server.address 0.0.0.0 --server.port 8501
st.set_page_config(page_title=APP_DISPLAY, page_icon="🧬", layout="wide")

store = get_session_store()
if "default_users_seeded" not in st.session_state:
    store.seed_default_users(DEFAULT_USERS)
    st.session_state.default_users_seeded = True

# ── Login ─────────────────────────────────────────────────────────────────────
render_login(store)

user_id  = st.session_state.user_id
user_uid = st.session_state.get("user_uid") or store.get_user_uid(user_id)
fm       = get_file_manager()

# ── Initialize session (first visit or after user switch) ─────────────────────
if not st.session_state.get("current_session_id"):
    sessions = store.get_user_sessions(user_id)
    if sessions:
        switch_session(store, sessions[0]["session_id"])
    else:
        new_sess = store.create_session(
            user_id,
            name=f"{_('Session')} {datetime.now().strftime('%m-%d %H:%M')}",
        )
        switch_session(store, new_sess["session_id"])

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar(store, fm, user_id, user_uid)

# ── Main area ─────────────────────────────────────────────────────────────────
st.title(f"🧬 {APP_DISPLAY}")
st.markdown("---")

current_session_id = st.session_state.current_session_id
current_session    = store.get_session(current_session_id)
current_messages   = store.get_messages(current_session_id)


@st.cache_resource
def load_agent():
    from configs.path_config import OTHER_PATH
    return create_agent_graph(
        APP_PASCAL,
        is_save_graph_image=True,
        graph_image_filename=OTHER_PATH["graph_image"],
    )


with st.spinner(_("Loading model...")):
    app = load_agent()

render_history(current_messages)

# ── Initialise execution state ────────────────────────────────────────────────
defaults = {
    "pending_prompt":            None,
    "ui_mode":                   None,
    "waiting_for_mode":          False,
    "waiting_review":            False,
    "pending_commands":          [],
    "resume_decision":           None,
    "review_feedback":           "",
    "thinking_process":          [],
    "review_submitted":          False,
    "confirming_execute":        False,
    "current_run_dir":           None,
    "waiting_prereq_review":     False,
    "prereq_review_submitted":   False,
    "prereq_cached_files":       None,
    "prereq_edited_files":       None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Chat input (disabled while background task is running) ────────────────────
_task_running = bool(st.session_state.get("_agent_bg_result"))
if prompt := st.chat_input(_("Enter your analysis instruction..."), disabled=_task_running):
    st.session_state.pending_prompt          = prompt
    st.session_state.ui_mode                 = None
    st.session_state.waiting_for_mode        = False
    st.session_state.waiting_review          = False
    st.session_state.resume_decision         = None
    st.session_state.review_submitted        = False
    st.session_state.confirming_execute      = False
    st.session_state.thinking_process        = []
    st.session_state.waiting_prereq_review   = False
    st.session_state.prereq_review_submitted = False
    st.session_state.prereq_cached_files     = None
    st.session_state.prereq_edited_files     = None
    st.session_state.pop("_agent_done_result", None)
    st.rerun()

# ── Execution flow ─────────────────────────────────────────────────────────────
run_first_segment(app, store, fm, user_uid, current_session_id, current_session)
render_prereq_reviewer(app)
run_prereq_review_segment(app, store, fm, user_uid, current_session_id)
render_review(app)
run_second_segment(app, store, fm, user_uid, current_session_id)
