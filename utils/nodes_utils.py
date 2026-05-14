import os
from typing import List, Dict

from configs import DATA_PATH
from tools.methylong.command_builder import build_methylong_command
from utils.user_context import get_session_dir, get_or_create_run_dir


def format_history(history: List[Dict[str, str]]) -> str:
    """Convert history list to LLM-readable text."""
    if not history:
        return "None"
    return "\n".join([f"[{msg['role']}]: {msg['content']}" for msg in history])


def build_command_for_call(call: dict, is_workflow: bool = False) -> str:
    """Build a shell command string from a tool call dict."""
    # Pre-built commands from deterministic step builders — return directly.
    if "_prebuilt_cmd" in call:
        return call["_prebuilt_cmd"]

    tool_name = call["tool_name"]
    tool_args = call["tool_args"]

    session_dir = get_session_dir()
    run_dir = get_or_create_run_dir() if session_dir else None

    if is_workflow:
        wf_data_path = dict(DATA_PATH.get("workflow", {}))
        if session_dir:
            wf_data_path["base_data_dir"] = session_dir
        if run_dir:
            wf_data_path["out_dir"] = run_dir
            wf_data_path["work_dir"] = os.path.join(run_dir, "work")
        return build_methylong_command(tool_args.get("kwargs", tool_args), wf_data_path)

    # Fallback for any non-workflow call
    kwargs = tool_args.get("kwargs", tool_args) if isinstance(tool_args, dict) else {}
    parts = [tool_name]
    for k, v in kwargs.items():
        if v:
            parts.append(f"--{k} {v}")
    return " ".join(parts)
