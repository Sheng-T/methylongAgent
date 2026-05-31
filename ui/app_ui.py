import sys
import os
import warnings

warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime

from agent_graph.graph import create_agent_graph
from storage.session_store import get_session_store
from storage.file_manager import get_file_manager
from configs.runtime_config import DEFAULT_USERS
from configs.app_config import APP_DISPLAY, APP_PASCAL
from utils.i18n import _
from utils.file_server import start_file_server, is_running as _fs_running
from configs.runtime_config import FILE_SERVER_PORT

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
start_file_server(fm.root, FILE_SERVER_PORT)

# ── File server keepalive — prevents idle tunnel from closing ─────────────────
if _fs_running():
    import streamlit.components.v1 as _c
    _c.html(f"""<script>
    (function(){{
      function _ping(){{
        try{{var h=window.top.location.hostname||'localhost';
             var pr=window.top.location.protocol||'http:';}}
        catch(e){{var h='localhost';var pr='http:';}}
        fetch(pr+'//'+h+':{FILE_SERVER_PORT}/ping',{{mode:'no-cors',cache:'no-store'}}).catch(function(){{}});
      }}
      _ping();
      setInterval(_ping, 25000);
    }})();
    </script>""", height=0)

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
    "pending_user_choice":       None,
    "pending_mode_label":        None,
    "mode_selector_epoch":       0,
    "last_mode":                 None,
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

# ── Execution flow (runs before input widgets so its output appears above them) ─
run_first_segment(app, store, fm, user_uid, current_session_id, current_session)
render_prereq_reviewer(app)
run_prereq_review_segment(app, store, fm, user_uid, current_session_id)
render_review(app)
run_second_segment(app, store, fm, user_uid, current_session_id)

# ── Mode selector + chat input (always rendered last → always near the bottom) ─
# pills use an epoch-based key so each submit starts a fresh widget.
_lang = st.session_state.get("lang", "zh_CN")
_mode_opts = (
    ["🔄 Auto", "🔬 Run Workflow", "💬 Q&A"]
    if _lang == "en_US" else
    ["🔄 自动", "🔬 执行流水线", "💬 问答"]
)
_mode_to_choice = {_mode_opts[0]: None, _mode_opts[1]: "workflow", _mode_opts[2]: "answer"}

_agent_busy = (
    bool(st.session_state.get("_agent_bg_result")) or
    bool(st.session_state.get("pending_prompt"))   or
    bool(st.session_state.get("waiting_review"))   or
    bool(st.session_state.get("waiting_prereq_review"))
)
_epoch   = st.session_state.mode_selector_epoch
_default = st.session_state.get("last_mode") or _mode_opts[0]
if _default not in _mode_opts:
    _default = _mode_opts[0]

_selected_mode = st.pills(
    "mode", _mode_opts,
    selection_mode="single",
    default=_default,
    key=f"input_mode_selector_{_epoch}",
    label_visibility="collapsed",
    disabled=_agent_busy,
)
if _selected_mode is None:
    _selected_mode = _default

_chat_disabled = bool(st.session_state.get("_agent_bg_result"))
if prompt := st.chat_input(_("Enter your analysis instruction..."), disabled=_chat_disabled):
    st.session_state.pending_prompt          = prompt
    st.session_state.pending_user_choice     = _mode_to_choice[_selected_mode]
    st.session_state.pending_mode_label      = _selected_mode
    st.session_state.last_mode               = _selected_mode
    st.session_state.mode_selector_epoch    += 1
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
    st.session_state.prereq_cached_issues    = None
    st.session_state.prereq_edited_files     = None
    st.session_state.pop("_agent_done_result", None)
    for _k in ("_agent_bg_result", "_agent_bg_thread", "_agent_thinking", "_agent_log_buf"):
        st.session_state.pop(_k, None)
    st.rerun()
