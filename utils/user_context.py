"""
Thread-local storage: pass current user's session directory info during LangGraph execution.

Usage:
  # UI layer (call before app.stream())
  from utils.user_context import set_session_context
  set_session_context(uid, session_id, session_dir)

  # Tool layer (in build_command_for_call etc.)
  from utils.user_context import get_session_dir, get_or_create_run_dir
  user_dir = get_session_dir()   # returns user session dir, or None if not set
"""
import os
import threading
from datetime import datetime

_local = threading.local()


def set_session_context(uid: int, session_id: str, session_dir: str):
    """Set the current thread's user session context."""
    _local.uid = uid
    _local.session_id = session_id
    _local.session_dir = session_dir
    _local.run_dir = None  # reset run_dir for each new request


def get_session_dir() -> str | None:
    """Return the session directory bound to the current thread, or None."""
    return getattr(_local, "session_dir", None)


def get_uid() -> int | None:
    return getattr(_local, "uid", None)


def get_session_id() -> str | None:
    return getattr(_local, "session_id", None)


def get_run_dir() -> str | None:
    """Return the run directory created for this request (None if not yet created)."""
    return getattr(_local, "run_dir", None)


def get_or_create_run_dir() -> str | None:
    """
    Create (or reuse) a run directory under the user's session directory.
    Format: run_{session_id[:8]}_{YYYYmmdd_HHMMSS}
    Returns None if no session context is set.
    """
    session_dir = get_session_dir()
    if not session_dir:
        return None

    if getattr(_local, "run_dir", None):
        return _local.run_dir

    session_id = getattr(_local, "session_id", "unknown")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"run_{session_id[:8]}_{ts}"
    run_dir = os.path.join(session_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)
    _local.run_dir = run_dir
    return run_dir
