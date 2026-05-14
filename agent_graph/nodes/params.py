"""
Parameter generator node — builds tool_calls for nfcore methylong workflow.
"""
import os

from agent_graph.state import AgentState
from utils.llm_utils import get_llm_instance
from utils.user_context import get_or_create_run_dir, get_session_dir
from utils.ui_logger import ui_print


def generate_tool_params_node(state: AgentState) -> AgentState:
    """
    Build the methylong tool_calls list.
    For the nfcore workflow, this directly builds the structured call dict
    with the samplesheet path and outdir.
    """
    user_feedback  = state.get("user_feedback", "")
    pre_files      = state.get("pre_files", [])
    selected_workflow = state.get("selected_workflow", "methylong")

    if user_feedback:
        state["user_feedback"] = ""

    ui_print(f"\n[Param Generator] Configuring parameters for methylong (nfcore)...")

    run_dir = get_or_create_run_dir()

    # Locate or re-write the samplesheet in run_dir
    input_path = ""
    if pre_files and run_dir:
        pf = pre_files[0]
        safe_name = os.path.basename(pf["filename"])
        dest = os.path.join(run_dir, safe_name)
        if not os.path.exists(dest):
            with open(dest, "w", encoding="utf-8") as _f:
                _f.write(pf["content"])
            ui_print(f"[Param Generator] Wrote samplesheet to run_dir: {dest}")
        input_path = dest
    elif pre_files:
        # Fallback: write to session_dir
        session_dir = get_session_dir()
        if session_dir:
            pf = pre_files[0]
            safe_name = os.path.basename(pf["filename"])
            dest = os.path.join(session_dir, safe_name)
            with open(dest, "w", encoding="utf-8") as _f:
                _f.write(pf["content"])
            input_path = dest

    tool_call = {
        "tool_name": selected_workflow,
        "tool_args": {
            "kwargs": {
                "pipeline": selected_workflow,
                "input":    input_path,
                "outdir":   "results",
            }
        }
    }

    ui_print(f"[Param Generator] pipeline={selected_workflow}, input={input_path}")
    state["tool_calls"] = [tool_call]
    return state
