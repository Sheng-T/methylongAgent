"""
Review node: builds pending_commands from tool_calls and writes pre-files to disk.
"""
import os

from agent_graph.state import AgentState
from utils.nodes_utils import build_command_for_call
from utils.user_context import get_or_create_run_dir
from utils.ui_logger import ui_print


def review_execution_plan_node(state: AgentState) -> dict:
    tool_calls       = state.get("tool_calls", [])
    pre_files        = state.get("pre_files", [])
    user_feedback    = state.get("user_feedback", "")
    pending_commands = []

    if user_feedback:
        state["user_feedback"] = ""

    run_dir = get_or_create_run_dir() or ""

    # Write workflow pre-requisite files (samplesheet etc.) directly using Python
    if pre_files and run_dir:
        os.makedirs(run_dir, exist_ok=True)
        for pf in pre_files:
            dest = os.path.join(run_dir, pf["filename"])
            with open(dest, "w", encoding="utf-8") as _f:
                _f.write(pf["content"])
            ui_print(f"[Review] Pre-file written: {pf['filename']} -> {dest}")

    # Build shell commands for each tool call
    for i, call in enumerate(tool_calls):
        raw_cmd = build_command_for_call(call, is_workflow=True)
        pending_commands.append(raw_cmd)
        ui_print(f"[Review] Step {i+1}: {raw_cmd[:120]}...")

    return {
        **state,
        "pending_commands": pending_commands,
        "run_dir":          run_dir,
        "next_node":        "executor",
    }
