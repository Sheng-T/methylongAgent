import os
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from storage.file_manager import fmt_size
from configs.i18n_config import SUPPORTED_LANGS, DEFAULT_LANG
from configs.path_config import USER_QUOTA_BYTES
from utils.i18n import _
from utils.auth_cookie import clear_login_cookie
from utils.file_server import make_download_html, is_running


def switch_session(store, session_id: str):
    """Switch to the specified session and reset execution state."""
    session = store.get_session(session_id)
    if not session:
        return
    st.session_state.current_session_id = session_id
    st.session_state.thread_id          = session["thread_id"]
    for key in ("pending_prompt", "ui_mode", "waiting_for_mode",
                "waiting_review", "pending_commands", "resume_decision",
                "review_feedback", "thinking_process", "current_run_dir",
                "review_submitted", "confirming_execute", "last_exec_error",
                "waiting_prereq_review", "prereq_review_submitted",
                "prereq_cached_files", "prereq_edited_files"):
        st.session_state.pop(key, None)


def render_sidebar(store, fm, user_id, user_uid):
    """Render the complete sidebar: user info / language / session management / file management."""
    with st.sidebar:
        # ── User info ────────────────────────────────────────────────────────
        st.markdown(f"**👤 {user_id}**")
        if st.button(_("Switch User"), use_container_width=True):
            clear_login_cookie()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.divider()

        # ── Language selector ────────────────────────────────────────────────
        lang_options  = list(SUPPORTED_LANGS.keys())
        lang_labels   = list(SUPPORTED_LANGS.values())
        current_idx   = lang_options.index(st.session_state.get("lang", DEFAULT_LANG))
        selected_label = st.selectbox(
            _("Language"), options=lang_labels, index=current_idx, key="lang_selector"
        )
        selected_lang = lang_options[lang_labels.index(selected_label)]
        if selected_lang != st.session_state.get("lang"):
            st.session_state.lang = selected_lang
            store.set_user_lang(user_id, selected_lang)
            st.rerun()

        st.divider()

        # ── Pipeline info ─────────────────────────────────────────────────────
        with st.expander("🧬 methylong Pipeline", expanded=False):
            st.markdown(
                "**nf-core/methylong** — End-to-end nanopore DNA methylation analysis.\n\n"
                "Supports: BAM / pod5 input, CpG methylation calling, "
                "haplotype phasing, and SNV calling.\n\n"
                "Input formats: `BAM`, `pod5`"
            )

        st.divider()

        # ── Session management ───────────────────────────────────────────────
        if st.button(_("➕ New Session"), use_container_width=True):
            new_sess = store.create_session(
                user_id,
                name=f"{_('Session')} {datetime.now().strftime('%m-%d %H:%M')}",
            )
            switch_session(store, new_sess["session_id"])
            st.rerun()

        st.markdown(f"**{_('Sessions')}**")
        sessions = store.get_user_sessions(user_id)
        for sess in sessions:
            is_active = sess["session_id"] == st.session_state.current_session_id
            label     = f"📌 {sess['name']}" if is_active else sess["name"]
            col_btn, col_del = st.columns([5, 1])
            with col_btn:
                if st.button(label, key=f"sess_{sess['session_id']}", use_container_width=True):
                    switch_session(store, sess["session_id"])
                    st.rerun()
            with col_del:
                if st.button("🗑", key=f"del_{sess['session_id']}"):
                    thread_id = sess.get("thread_id", "")
                    store.delete_session(sess["session_id"])
                    fm.delete_session_files(user_uid, sess["session_id"])
                    if thread_id:
                        try:
                            from storage.checkpointer import get_checkpointer
                            cp = get_checkpointer()
                            if hasattr(cp, "conn"):
                                cp.conn.execute("DELETE FROM checkpoints WHERE thread_id=?", (thread_id,))
                                cp.conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id=?", (thread_id,))
                                cp.conn.execute("DELETE FROM checkpoint_writes WHERE thread_id=?", (thread_id,))
                                cp.conn.commit()
                        except Exception:
                            pass
                    if is_active:
                        st.session_state.current_session_id = None
                    st.rerun()
            st.caption(f"  {store.message_count(sess['session_id'])} {_('messages')}")

        # ── File management ──────────────────────────────────────────────────
        st.markdown("""<style>
/* Square icon buttons in sidebar file list only */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stDownloadButton"] button,
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"] button {
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    aspect-ratio: 1 / 1 !important;
    min-height: 36px !important;
    font-size: 16px !important;
    line-height: 1 !important;
}
</style>""", unsafe_allow_html=True)
        st.divider()
        current_sid  = st.session_state.get("current_session_id", "")
        _session_dir = fm.session_dir(user_uid, current_sid) if current_sid else ""
        _lang        = st.session_state.get("lang", DEFAULT_LANG)
        _copy_help   = "复制 session 上传目录路径" if _lang != "en_US" else "Copy session upload directory path"

        _fc1, _fc2 = st.columns([4, 3])
        _fc1.markdown(f"**{_('📁 File Management')}**")
        with _fc2:
            _b1, _b2 = st.columns(2)
            with _b1:
                if st.button("🔄", key="refresh_files", help=_("Refresh file list"),
                             use_container_width=True):
                    st.rerun()
            with _b2:
                if st.button("📋", key="copy_session_path", help=_copy_help,
                             use_container_width=True):
                    st.session_state._show_session_path = not st.session_state.get("_show_session_path", False)
        if st.session_state.get("_show_session_path") and _session_dir:
            st.code(_session_dir, language=None)

        usage = fm.get_usage(user_uid)
        used  = usage["total_bytes"]
        pct   = min(used / USER_QUOTA_BYTES, 1.0) if USER_QUOTA_BYTES > 0 else 0

        breakdown   = fm.get_session_breakdown(user_uid, current_sid)
        up_sz  = fmt_size(breakdown["upload_bytes"])
        run_sz = fmt_size(breakdown["run_bytes"])

        st.progress(pct, text=f"{fmt_size(used)} / {fmt_size(USER_QUOTA_BYTES)}")
        st.caption(f"📤 {_('Uploads')}: {up_sz}    🧬 {_('Run products')}: {run_sz}")

        _upload_help = "建议大文件（>1GB）直接上传到服务器 session 目录" if _lang != "en_US" \
                       else "For large files (>1 GB), upload directly to the server session directory"
        st.caption(_upload_help)
        uploaded = st.file_uploader(
            _("Upload files to current session"),
            accept_multiple_files=True,
            key=f"uploader_{current_sid}",
            label_visibility="collapsed",
        )
        if uploaded:
            if "uploaded_file_keys" not in st.session_state:
                st.session_state.uploaded_file_keys = set()
            new_files = []
            for f in uploaded:
                file_key = f"{f.name}_{f.size}"
                if file_key not in st.session_state.uploaded_file_keys:
                    try:
                        if hasattr(f, "seek"):
                            f.seek(0)
                        size_mb = f.size / (1024 * 1024) if hasattr(f, "size") else 0
                        _spin_msg = (f"Saving {f.name} ({size_mb:.0f} MB)..."
                                     if size_mb > 100 else f"Saving {f.name}...")
                        with st.spinner(_spin_msg):
                            fm.save_file(user_uid, current_sid, f.name, f)
                        st.session_state.uploaded_file_keys.add(file_key)
                        new_files.append(f.name)
                    except Exception as e:
                        st.error(f"Upload failed ({f.name}): {e}")
            if new_files:
                st.success(f"Uploaded: {', '.join(new_files)}")
                st.rerun()

        # pending delete key: "file::<name>" | "clear_files" | "rundir::<name>" | "clear_runs"
        _pdk = f"_sb_pending_del_{current_sid}"
        _pending = st.session_state.get(_pdk, "")

        files = fm.list_session_files(user_uid, current_sid)
        if files:
            st.markdown(f"*{len(files)} {_('files')}*")
            for fi in files:
                _fkey = f"file::{fi['name']}"
                col_name, col_dl, col_del = st.columns([4, 1, 1])
                ext  = os.path.splitext(fi["name"])[1].lower()
                mime = {
                    ".zip": "application/zip",
                    ".pdf": "application/pdf",
                    ".md":  "text/markdown",
                    ".csv": "text/csv",
                    ".tsv": "text/tab-separated-values",
                    ".txt": "text/plain",
                    ".bed": "text/plain",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".html": "text/html",
                }.get(ext, "application/octet-stream")
                if _pending == _fkey:
                    col_name.caption(f"⚠️ {_('Delete')} `{fi['name']}`?")
                    if col_dl.button("✓", key=f"fdel_yes_{current_sid}_{fi['name']}",
                                     use_container_width=True):
                        fm.delete_file(user_uid, current_sid, fi["name"])
                        st.session_state.pop(_pdk, None)
                        st.rerun()
                    if col_del.button("✗", key=f"fdel_no_{current_sid}_{fi['name']}",
                                      use_container_width=True):
                        st.session_state.pop(_pdk, None)
                        st.rerun()
                else:
                    col_name.caption(f"📄 {fi['name']}  `{fmt_size(fi['size'])}`")
                    with col_dl:
                        if is_running():
                            components.html(make_download_html(fi["path"]), height=36, scrolling=False)
                        else:
                            try:
                                with open(fi["path"], "rb") as _f:
                                    st.download_button(
                                        "⬇", data=_f.read(), file_name=fi["name"], mime=mime,
                                        key=f"fdl_{current_sid}_{fi['name']}",
                                        use_container_width=True,
                                    )
                            except OSError:
                                st.write("")
                    if col_del.button("✕", key=f"fdel_{current_sid}_{fi['name']}",
                                      use_container_width=True):
                        st.session_state[_pdk] = _fkey
                        st.rerun()

            if _pending == "clear_files":
                st.warning(_("Delete all uploaded files?"))
                _cc1, _cc2 = st.columns(2)
                if _cc1.button(_("✓ Confirm"), key=f"clrfiles_yes_{current_sid}",
                               use_container_width=True):
                    fm.delete_session_files(user_uid, current_sid)
                    st.session_state.pop(f"uploaded_files_{current_sid}", None)
                    st.session_state.pop(_pdk, None)
                    st.rerun()
                if _cc2.button(_("✗ Cancel"), key=f"clrfiles_no_{current_sid}",
                               use_container_width=True):
                    st.session_state.pop(_pdk, None)
                    st.rerun()
            else:
                if st.button(_("🗑 Clear session files"), use_container_width=True):
                    st.session_state[_pdk] = "clear_files"
                    st.rerun()

        # ── Run products cleanup ──────────────────────────────────────────────
        run_dirs = breakdown["run_dirs"]
        if run_dirs:
            with st.expander(f"{_('🗑 Clean run products')}  ({run_sz})", expanded=False):
                for rd in run_dirs:
                    _rkey = f"rundir::{rd['name']}"
                    col_n, col_d = st.columns([5, 1])
                    if _pending == _rkey:
                        col_n.caption(f"⚠️ {_('Delete')} `{rd['name']}`?")
                        _rc1, _rc2 = st.columns(2)
                        if _rc1.button("✓", key=f"rddel_yes_{current_sid}_{rd['name']}",
                                       use_container_width=True):
                            import shutil, os as _os
                            rpath = _os.path.join(
                                fm.session_dir(user_uid, current_sid), rd["name"]
                            )
                            if _os.path.isdir(rpath):
                                shutil.rmtree(rpath, ignore_errors=True)
                            st.session_state.pop(_pdk, None)
                            st.rerun()
                        if _rc2.button("✗", key=f"rddel_no_{current_sid}_{rd['name']}",
                                       use_container_width=True):
                            st.session_state.pop(_pdk, None)
                            st.rerun()
                    else:
                        col_n.caption(f"📁 {rd['name']}  `{fmt_size(rd['size'])}`")
                        if col_d.button("✕", key=f"rddel_{current_sid}_{rd['name']}",
                                        use_container_width=True):
                            st.session_state[_pdk] = _rkey
                            st.rerun()

                if _pending == "clear_runs":
                    st.warning(_("Delete all run products?"))
                    _rc1, _rc2 = st.columns(2)
                    if _rc1.button(_("✓ Confirm"), key=f"clrruns_yes_{current_sid}",
                                   use_container_width=True):
                        fm.delete_session_run_dirs(user_uid, current_sid)
                        st.session_state.pop(_pdk, None)
                        st.rerun()
                    if _rc2.button(_("✗ Cancel"), key=f"clrruns_no_{current_sid}",
                                   use_container_width=True):
                        st.session_state.pop(_pdk, None)
                        st.rerun()
                else:
                    if st.button(_("🗑 Clean all run products"), use_container_width=True):
                        st.session_state[_pdk] = "clear_runs"
                        st.rerun()

        if len(usage["sessions"]) > 1:
            with st.expander(_("Storage by session")):
                for sid, sz in sorted(usage["sessions"].items(),
                                      key=lambda x: x[1], reverse=True):
                    label = f"{sid} ({_('current')})" if sid == current_sid else sid
                    st.caption(f"{label}: {fmt_size(sz)}")
