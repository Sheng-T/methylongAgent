"""
Chat main area: message display / execution / prereq review / command review.
"""
import os
import threading
from datetime import datetime

import streamlit as st
from configs.app_config import APP_SNAKE
from utils.i18n import _
from utils.lang_utils import get_lang
from utils.user_context import get_run_dir, set_session_context

try:
    from utils.ui_logger import flush_logs, clear_logs
except ImportError:
    def flush_logs(): return []
    def clear_logs(): pass


# ── Log rendering ──────────────────────────────────────────────────────────────

_LOG_INTERNAL_PREFIXES = (
    "[ToolExecutor]",
    "[Executor] Running",
    "[Wrapper]",
    "[CmdBuilder]",
    "[Param Generator]",
    "[Review]",
    "[PrereqGenerator]",
    "[RAG",
    "[Chat]",
    "[Router]",
)


def render_log(log: str):
    stripped = log.strip()
    if not stripped:
        return
    for prefix in _LOG_INTERNAL_PREFIXES:
        if stripped.startswith(prefix):
            return

    lower = stripped.lower()
    if "✓" in stripped or "succeeded" in lower or "success" in lower:
        st.success(stripped)
    elif "✗" in stripped or "failed" in lower or "error" in lower:
        st.error(stripped)
    elif "warning" in lower:
        st.warning(stripped)
    else:
        st.text(stripped)


def stream_events(event_iter, thinking_process: list) -> str:
    full_response = ""

    def _flush():
        flush_logs()

    for event in event_iter:
        _flush()
        node_name = list(event.keys())[0]
        thinking_process.append(f"📍 **{node_name}**")
        st.markdown(f"📍 `{node_name}`")
        _flush()
        if isinstance(event.get(node_name), dict):
            for key, val in event[node_name].items():
                if key not in {"final_answer", "answer", "response", "output", "result"}:
                    if isinstance(val, (str, int, float)) and len(str(val)) < 200:
                        thinking_process.append(f"  - {key}: {val}")
        for _, node_data in event.items():
            if isinstance(node_data, dict):
                for field in ("final_answer", "answer", "response", "output", "result"):
                    if node_data.get(field):
                        full_response = node_data[field]
        _flush()
    return full_response


def render_final(full_response: str, thinking_process: list,
                 analysis_images: list | None = None,
                 workflow_result_zip: str = ""):
    if thinking_process:
        with st.expander(_("🧠 View thinking process"), expanded=False):
            st.markdown("\n".join(thinking_process))
    st.markdown(full_response if full_response else _("✅ Task completed"))

    if analysis_images:
        st.markdown("---")
        st.markdown(_("**📊 Analyze charts**"))
        summary_imgs = [p for p in analysis_images if "summary" in os.path.basename(p)]
        show_imgs    = [p for p in (summary_imgs if summary_imgs else analysis_images) if os.path.isfile(p)]

        cols = st.columns(min(len(show_imgs), 2)) if show_imgs else []
        for i, img_path in enumerate(show_imgs):
            with cols[i % 2]:
                st.image(img_path, use_container_width=True)
                with open(img_path, "rb") as f:
                    st.download_button(
                        label=f"⬇ {os.path.basename(img_path)}",
                        data=f,
                        file_name=os.path.basename(img_path),
                        mime="image/png",
                        key=f"dl_{img_path}",
                    )

    if full_response or analysis_images or workflow_result_zip:
        lang = get_lang()
        report_text = full_response or ""
        _key_suffix = str(len(report_text))

        st.markdown("---")

        if workflow_result_zip and os.path.isfile(workflow_result_zip):
            zip_label = "⬇ Download Results (.zip)" if lang == "en_US" else "⬇ 下载结果压缩包 (.zip)"
            zip_fname = os.path.basename(workflow_result_zip)
            with open(workflow_result_zip, "rb") as zf:
                st.download_button(
                    label=zip_label,
                    data=zf,
                    file_name=zip_fname,
                    mime="application/zip",
                    key=f"zip_{_key_suffix}",
                    use_container_width=True,
                )

        col_md, col_pdf = st.columns(2)
        with col_md:
            md_label = "⬇ Download Report (.md)" if lang == "en_US" else "⬇ 下载报告 (.md)"
            md_fname = f"{APP_SNAKE}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            st.download_button(
                label=md_label,
                data=report_text.encode("utf-8"),
                file_name=md_fname,
                mime="text/markdown",
                key=f"md_{_key_suffix}",
                use_container_width=True,
            )

        with col_pdf:
            try:
                from utils.pdf_exporter import generate_report_pdf
                pdf_bytes = generate_report_pdf(report_text, analysis_images or [], lang)
                pdf_label = "⬇ Download Report (.pdf)" if lang == "en_US" else "⬇ 下载报告 (.pdf)"
                pdf_fname = f"{APP_SNAKE}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.download_button(
                    label=pdf_label,
                    data=pdf_bytes,
                    file_name=pdf_fname,
                    mime="application/pdf",
                    key=f"pdf_{_key_suffix}",
                    use_container_width=True,
                )
            except ImportError:
                st.caption("PDF unavailable — run `pip install fpdf2`" if lang == "en_US"
                           else "PDF 不可用，请执行 `pip install fpdf2`")
            except Exception as e:
                st.caption(f"PDF error: {e}")


def get_final_from_state(current_state) -> str:
    for field in ("final_answer", "answer", "response", "output", "result"):
        val = current_state.values.get(field)
        if val:
            return val
    return ""


# ── History ────────────────────────────────────────────────────────────────────

def _render_history_downloads(meta: dict, content: str):
    """Restore download buttons for a past assistant message using saved metadata."""
    lang = get_lang()
    key_base = str(hash(content))[:8]

    zip_path = meta.get("zip_path", "")
    if zip_path and os.path.isfile(zip_path):
        zip_label = "⬇ Download Results (.zip)" if lang == "en_US" else "⬇ 下载结果压缩包 (.zip)"
        with open(zip_path, "rb") as zf:
            st.download_button(
                label=zip_label,
                data=zf,
                file_name=os.path.basename(zip_path),
                mime="application/zip",
                key=f"hist_zip_{key_base}",
                use_container_width=True,
            )

    col_md, col_pdf = st.columns(2)
    md_label  = "⬇ Download Report (.md)"  if lang == "en_US" else "⬇ 下载报告 (.md)"
    pdf_label = "⬇ Download Report (.pdf)" if lang == "en_US" else "⬇ 下载报告 (.pdf)"
    md_fname  = f"{APP_SNAKE}_report.md"
    pdf_fname = f"{APP_SNAKE}_report.pdf"
    with col_md:
        st.download_button(
            label=md_label,
            data=content.encode("utf-8"),
            file_name=md_fname,
            mime="text/markdown",
            key=f"hist_md_{key_base}",
            use_container_width=True,
        )
    with col_pdf:
        try:
            from utils.pdf_exporter import generate_report_pdf
            analysis_images = [p for p in (meta.get("analysis_images") or []) if os.path.isfile(p)]
            pdf_bytes = generate_report_pdf(content, analysis_images, lang)
            st.download_button(
                label=pdf_label,
                data=pdf_bytes,
                file_name=pdf_fname,
                mime="application/pdf",
                key=f"hist_pdf_{key_base}",
                use_container_width=True,
            )
        except Exception:
            pass


def render_history(messages: list):
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            thinking = message.get("thinking", "")
            if thinking and thinking.strip():
                with st.expander(_("🧠 View thinking process"), expanded=False):
                    st.markdown(thinking)
            meta = message.get("metadata") or {}
            if meta.get("zip_path") or meta.get("analysis_images"):
                _render_history_downloads(meta, message["content"])


# ── Prereq reviewer ────────────────────────────────────────────────────────────

def render_prereq_reviewer(app):
    """Render editable samplesheet UI when graph is paused before human_prereq_reviewer."""
    if not st.session_state.get("waiting_prereq_review"):
        return

    if not st.session_state.get("prereq_cached_files"):
        config = {"configurable": {"thread_id": st.session_state.get("thread_id", "")}}
        current_state = app.get_state(config)
        st.session_state.prereq_cached_files = current_state.values.get("pre_files", [])

    pre_files = st.session_state.prereq_cached_files or []
    lang = get_lang()

    with st.chat_message("assistant"):
        if lang == "en_US":
            st.markdown("### 📄 Review Sample Sheet")
            st.markdown(
                "The system has auto-generated the samplesheet below. "
                "Please verify that **file paths** (BAM, reference, etc.) are correct before continuing.  \n"
                "You can **edit the content directly** if needed."
            )
        else:
            st.markdown("### 📄 请确认样本表")
            st.markdown(
                "系统已根据上传文件自动生成以下样本表，如有需要可**直接编辑**下方内容，"
                "确认 **文件路径**（BAM、参考基因组等）无误后再继续。"
            )

        submitted = st.session_state.get("prereq_review_submitted", False)
        edited_files = []
        for pf in pre_files:
            st.markdown(f"**`{pf['filename']}`**")
            edited_content = st.text_area(
                label=pf["filename"],
                value=pf["content"],
                height=200,
                key=f"prereq_edit_{pf['filename']}",
                label_visibility="collapsed",
                disabled=submitted,
            )
            edited_files.append({"filename": pf["filename"], "content": edited_content})

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ Confirm & Continue" if lang == "en_US" else "✅ 确认继续",
                use_container_width=True, disabled=submitted,
            ):
                st.session_state.prereq_edited_files = edited_files
                st.session_state.prereq_review_submitted = True
                st.session_state.waiting_prereq_review = False
                st.session_state.pop("prereq_cached_files", None)
                st.rerun()
        with col2:
            if st.button(
                _("❌ Cancel"),
                use_container_width=True, disabled=submitted,
            ):
                st.session_state.prereq_review_submitted = True
                st.session_state.prereq_review_cancelled = True
                st.session_state.waiting_prereq_review = False
                st.session_state.pop("prereq_cached_files", None)
                st.rerun()


# ── Command review ────────────────────────────────────────────────────────────

def render_review(app):
    if not st.session_state.waiting_review:
        return

    with st.chat_message("assistant"):
        last_error = st.session_state.pop("last_exec_error", None)
        if last_error:
            st.error(f"### ❌ {_('Last run failed — commands have been auto-corrected')}")
            with st.expander(_("View error details"), expanded=True):
                st.code(last_error, language="text")
            st.markdown(f"**{_('Review the corrected commands below and confirm to re-run:')}**")
        else:
            st.markdown(f"### 📋 {_('Pending commands — please confirm')}")

        pre_files = app.get_state(
            {"configurable": {"thread_id": st.session_state.get("thread_id", "")}}
        ).values.get("pre_files", [])
        if pre_files:
            st.markdown(f"**📄 {_('Pre-requisite files')}**")
            for pf in pre_files:
                with st.expander(f"`{pf['filename']}`", expanded=True):
                    st.code(pf["content"], language="csv")

        if st.session_state.pending_commands:
            st.markdown(f"**💻 {_('Commands to execute')}**")
            for i, cmd in enumerate(st.session_state.pending_commands, 1):
                st.markdown(f"**{_('Step')} {i}**")
                st.code(cmd, language="bash")
        else:
            st.info(_("Command list is empty — check parameter generation"))

        st.markdown("---")
        submitted  = st.session_state.review_submitted
        confirming = st.session_state.get("confirming_execute", False)

        if submitted:
            decision = st.session_state.get("resume_decision")
            if decision == "cancel":
                st.warning(_("🚫 Cancelling..."))
            elif decision == "modify":
                st.info(_("🔄 Regenerating commands..."))
            else:
                st.info(_("⏳ Submitted — task is running, please wait..."))

        st.text_input(_("🔧 Revision notes (fill in before submitting)"),
                      key="review_feedback", disabled=submitted)
        col1, col2, col3 = st.columns(3)
        with col1:
            if not confirming:
                if st.button(_("✅ Confirm & Run"),
                             use_container_width=True, disabled=submitted):
                    st.session_state.confirming_execute = True
                    st.rerun()
            else:
                st.warning(_("⚠️ This will run on the server immediately. Are you sure?"))
                yes_col, no_col = st.columns(2)
                with yes_col:
                    if st.button(_("▶ Yes, run it"),
                                 use_container_width=True, type="primary",
                                 disabled=submitted):
                        st.session_state.confirming_execute = False
                        st.session_state.review_submitted   = True
                        st.session_state.resume_decision    = "execute"
                        st.rerun()
                with no_col:
                    if st.button(_("← Let me check again"),
                                 use_container_width=True, disabled=submitted):
                        st.session_state.confirming_execute = False
                        st.rerun()
        with col2:
            if st.button(_("❌ Cancel"),
                         use_container_width=True,
                         disabled=submitted or confirming):
                st.session_state.review_submitted = True
                st.session_state.resume_decision  = "cancel"
                st.rerun()
        with col3:
            if st.button(_("💬 Submit Revision"),
                         use_container_width=True,
                         disabled=submitted or confirming):
                if st.session_state.review_feedback.strip():
                    st.session_state.review_submitted = True
                    st.session_state.resume_decision  = "modify"
                    st.rerun()
                else:
                    st.warning(_("Please fill in revision notes first"))


# ── First execution segment ────────────────────────────────────────────────────

def run_first_segment(app, store, fm, user_uid, current_session_id, current_session):
    """Run the graph until an interrupt point, then update session state."""
    if not (st.session_state.pending_prompt and
            not st.session_state.waiting_review and
            not st.session_state.get("waiting_prereq_review")):
        return

    prompt    = st.session_state.pending_prompt
    thread_id = current_session["thread_id"]
    st.session_state.thread_id = thread_id
    config = {"configurable": {"thread_id": thread_id}}

    st.session_state.pending_prompt   = None
    st.session_state.waiting_for_mode = False

    store.append_message(current_session_id, "user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        thinking_process = []
        clear_logs()
        set_session_context(user_uid, current_session_id,
                            fm.session_dir(user_uid, current_session_id))

        with st.status(_("🔄 Agent running..."), expanded=True) as status:
            full_response = stream_events(
                app.stream({"input": prompt, "user_choice": None}, config=config),
                thinking_process,
            )

        current_state = app.get_state(config)

        if "human_prereq_reviewer" in current_state.next:
            pre_files = current_state.values.get("pre_files") or []
            if not pre_files:
                status.update(label=_("❌ Failed"), state="error")
                st.error(_("Samplesheet generation failed — please upload your BAM/pod5 files first, then describe the analysis."))
            else:
                st.session_state.waiting_prereq_review   = True
                st.session_state.prereq_review_submitted = False
                st.session_state.thinking_process        = thinking_process
                st.session_state.prereq_cached_files     = pre_files
                status.update(label=_("⏸️ Awaiting samplesheet confirmation"), state="running")
        elif "executor" in current_state.next:
            st.session_state.pending_commands = current_state.values.get("pending_commands", [])
            st.session_state.waiting_review   = True
            st.session_state.review_submitted = False
            st.session_state.thinking_process = thinking_process
            st.session_state.current_run_dir  = get_run_dir()
            status.update(label=_("⏸️ Awaiting confirmation"), state="running")
        else:
            status.update(label=_("✅ Completed"), state="complete")
            if not full_response:
                full_response = get_final_from_state(current_state)
            _imgs = current_state.values.get("analysis_images", [])
            _zip  = current_state.values.get("workflow_result_zip", "")
            render_final(full_response, thinking_process, _imgs, _zip)
            store.append_message(
                current_session_id, "assistant",
                full_response if full_response else _("✅ Task completed"),
                "\n".join(thinking_process),
                metadata={"zip_path": _zip, "analysis_images": _imgs} if _zip or _imgs else None,
            )

    if st.session_state.waiting_review or st.session_state.get("waiting_prereq_review"):
        st.rerun()


# ── Prereq review resume segment ───────────────────────────────────────────────

def run_prereq_review_segment(app, store, fm, user_uid, current_session_id):
    """Resume after user confirms/edits the samplesheet."""
    if not (st.session_state.get("prereq_review_submitted") and
            st.session_state.get("thread_id")):
        return

    st.session_state.prereq_review_submitted = False
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    if st.session_state.pop("prereq_review_cancelled", False):
        app.update_state(config, {"next_node": "end_node"}, as_node="human_prereq_reviewer")
        st.info(_("✅ Task cancelled"))
        return

    edited_files = st.session_state.pop("prereq_edited_files", [])
    if edited_files:
        app.update_state(config, {"pre_files": edited_files}, as_node="human_prereq_reviewer")

    with st.chat_message("assistant"):
        thinking_process = st.session_state.get("thinking_process") or []
        clear_logs()
        set_session_context(user_uid, current_session_id,
                            fm.session_dir(user_uid, current_session_id))

        with st.status(_("🔄 Agent running..."), expanded=True) as status:
            full_response = stream_events(app.stream(None, config=config), thinking_process)

        current_state = app.get_state(config)

        if "executor" in current_state.next:
            st.session_state.pending_commands  = current_state.values.get("pending_commands", [])
            st.session_state.waiting_review    = True
            st.session_state.review_submitted  = False
            st.session_state.thinking_process  = thinking_process
            st.session_state.current_run_dir   = get_run_dir()
            status.update(label=_("⏸️ Awaiting confirmation"), state="running")
            st.rerun()
        else:
            status.update(label=_("✅ Completed"), state="complete")
            if not full_response:
                full_response = get_final_from_state(current_state)
            _imgs = current_state.values.get("analysis_images", [])
            _zip  = current_state.values.get("workflow_result_zip", "")
            render_final(full_response, thinking_process, _imgs, _zip)
            store.append_message(
                current_session_id, "assistant",
                full_response if full_response else _("✅ Task completed"),
                "\n".join(thinking_process),
                metadata={"zip_path": _zip, "analysis_images": _imgs} if _zip or _imgs else None,
            )
            st.session_state.thinking_process = []


# ── Second execution segment (background thread) ───────────────────────────────

class _AgentResult:
    def __init__(self):
        self.events: list = []
        self.done: bool   = False
        self.error        = None


def _run_agent_in_background(app, config, result: _AgentResult,
                             user_uid: int, current_session_id: str,
                             session_dir: str):
    try:
        set_session_context(user_uid, current_session_id, session_dir)
        for event in app.stream(None, config=config):
            result.events.append(event)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        result.error = f"{type(e).__name__}: {e}\n\n{tb}"
    finally:
        result.done = True


def run_second_segment(app, store, fm, user_uid, current_session_id):
    # Phase A: user just submitted a decision, start background thread
    _rd  = st.session_state.get("resume_decision")
    _tid = st.session_state.get("thread_id")
    if _rd and _tid:
        decision = st.session_state.resume_decision
        st.session_state.resume_decision = None
        st.session_state.waiting_review  = False
        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        if decision == "cancel":
            app.update_state(config, {"next_node": "end_node"}, as_node="human_reviewer")
            st.info(_("✅ Task cancelled"))
            return

        if decision == "modify":
            app.update_state(
                config,
                {"next_node": "param_generator",
                 "user_feedback": st.session_state.review_feedback},
                as_node="human_reviewer",
            )
            st.session_state.pop("review_feedback", None)

        clear_logs()
        set_session_context(user_uid, current_session_id,
                            fm.session_dir(user_uid, current_session_id))

        result = _AgentResult()
        t = threading.Thread(target=_run_agent_in_background,
                             args=(app, config, result, user_uid, current_session_id,
                                   fm.session_dir(user_uid, current_session_id)),
                             daemon=True)
        t.start()
        st.session_state._agent_bg_result  = result
        st.session_state._agent_bg_thread  = t
        st.session_state._agent_thinking   = st.session_state.thinking_process or []
        st.rerun()

    # Phase B: polling for background thread
    result: _AgentResult = st.session_state.get("_agent_bg_result")
    if result is None:
        return

    @st.fragment(run_every=5)
    def _poll_agent(app, store, current_session_id):
        result: _AgentResult = st.session_state.get("_agent_bg_result")
        if result is None:
            return

        thinking_process = st.session_state.get("_agent_thinking", [])
        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        while result.events:
            event = result.events.pop(0)
            node_name = list(event.keys())[0]
            thinking_process.append(f"📍 **{node_name}**")
        for log in flush_logs():
            st.session_state.setdefault("_agent_log_buf", []).append(log)
        st.session_state._agent_thinking = thinking_process

        log_buf = st.session_state.get("_agent_log_buf", [])
        if log_buf:
            with st.expander("📋 Execution log", expanded=True):
                st.code("\n".join(log_buf), language=None)

        if not result.done:
            st.info("⏳ Running methylong pipeline, please wait...")
            return

        for log in flush_logs():
            st.session_state.setdefault("_agent_log_buf", []).append(log)

        if result.error:
            st.error(f"Agent error: {result.error}")
            _cleanup_agent_bg_state()
            return

        current_state = app.get_state(config)

        if "param_generator" in current_state.next or "executor" in current_state.next:
            history = current_state.values.get("chat_history", [])
            last_error = None
            for msg in reversed(history):
                content = msg.get("content", "")
                if msg.get("role") == "assistant" and ("failed" in content.lower() or "失败" in content):
                    last_error = content
                    break
            st.session_state.pending_commands  = current_state.values.get("pending_commands", [])
            st.session_state.waiting_review    = True
            st.session_state.review_submitted  = False
            st.session_state.thinking_process  = thinking_process
            st.session_state.current_run_dir   = get_run_dir()
            st.session_state.last_exec_error   = last_error
            _cleanup_agent_bg_state()
            st.rerun()
        else:
            full_response = get_final_from_state(current_state)
            _imgs = current_state.values.get("analysis_images", [])
            _zip  = current_state.values.get("workflow_result_zip", "")
            store.append_message(
                current_session_id, "assistant",
                full_response if full_response else _("✅ Task completed"),
                "\n".join(thinking_process),
                metadata={"zip_path": _zip, "analysis_images": _imgs} if _zip or _imgs else None,
            )
            st.session_state.thinking_process = []
            st.session_state.pop("current_run_dir", None)
            _cleanup_agent_bg_state()
            st.rerun()

    with st.chat_message("assistant"):
        _poll_agent(app, store, current_session_id)


def _cleanup_agent_bg_state():
    for key in ("_agent_bg_result", "_agent_bg_thread", "_agent_thinking",
                "_agent_log_buf"):
        st.session_state.pop(key, None)
