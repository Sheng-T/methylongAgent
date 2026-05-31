"""
Parameter generator node — builds tool_calls for nfcore methylong workflow.
"""
import json
import os
import re

from agent_graph.state import AgentState
from agent_graph.prompts.prompts import build_params_prompt
from utils.llm_utils import get_llm_instance, invoke_json
from utils.rag_utils import rag_search
from utils.user_context import get_or_create_run_dir, get_session_dir
from utils.ui_logger import ui_print

_ARGS_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "static", "methylong", "methylong_args.json"
)


_SPEC_EXCLUDE = {"input", "outdir", "profile", "config",
                  "dorado_model", "dorado_modification_model"}


def _filter_by_param_name(raw: dict, user_input: str) -> dict:
    """
    Keep only params whose name (or a meaningful part of it) literally appears
    in the user's message. This is a deterministic check — no LLM involved.
    'ont', '5mc', 'bam' etc. are too generic; we require the param token itself.
    """
    # normalise: remove hyphens/underscores, lowercase
    def _norm(s: str) -> str:
        return re.sub(r"[-_]", "", s.lower())

    user_norm  = _norm(user_input)
    # also keep original lowercase for exact substring match
    user_lower = user_input.lower()

    # short tokens that are too generic to count as evidence
    _GENERIC = {"ont", "bam", "bed", "vcf", "ref", "no", "use",
                "run", "true", "false", "all", "none", "auto",
                "pacbio", "nanopore", "sample", "file", "data"}

    result: dict = {}
    for param, entry in raw.items():
        value = entry.get("value") if isinstance(entry, dict) else entry

        param_norm = _norm(param)
        # split param into meaningful tokens (e.g. "no_trim" → ["no","trim"])
        tokens = [t for t in re.split(r"[-_]", param.lower()) if t not in _GENERIC and len(t) > 2]

        # accept if normalised param name OR any meaningful token found in user input
        found = param_norm in user_norm or any(t in user_lower for t in tokens)
        if found:
            ui_print(f"[Param Generator] KEPT   {param!r} = {value!r}")
            result[param] = value
        else:
            ui_print(f"[Param Generator] DROPPED {param!r}: name not mentioned by user")

    return result


def _load_args_spec() -> str:
    """Return optional params spec (system params excluded) for the LLM prompt."""
    try:
        with open(_ARGS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        kwargs = data.get("args", {}).get("kwargs", {})
        lines = [f"--{k}: {v}" for k, v in kwargs.items() if k not in _SPEC_EXCLUDE]
        return "\n".join(lines)
    except Exception:
        return "(args spec unavailable)"


def _select_optional_params(user_input: str) -> dict:
    """Ask the LLM (with RAG context) which optional params to set."""
    args_spec = _load_args_spec()

    rag_context = ""
    try:
        result = rag_search(user_input, top_k=3)
        if result:
            rag_context = result
            ui_print("[Param Generator] RAG context retrieved for param selection")
    except Exception as e:
        ui_print(f"[Param Generator] RAG search failed ({e}), using LLM only")

    from utils.lang_utils import get_lang
    lang = get_lang()
    prompt = build_params_prompt(user_input, args_spec, rag_context, lang)

    llm = get_llm_instance(is_planner=True)
    try:
        raw = invoke_json(llm, prompt)
        if not isinstance(raw, dict):
            return {}
        ui_print(f"[Param Generator] LLM raw output: {raw}")
        return _filter_by_param_name(raw, user_input)
    except Exception as e:
        ui_print(f"[Param Generator] LLM param selection failed ({e}), using defaults")
        return {}


def generate_tool_params_node(state: AgentState) -> AgentState:
    """
    Build the methylong tool_calls list with LLM-selected optional parameters.
    """
    user_feedback     = state.get("user_feedback", "")
    pre_files         = state.get("pre_files", [])
    selected_workflow = state.get("selected_workflow", "methylong")
    user_input        = state.get("input", "")

    if user_feedback:
        state["user_feedback"] = ""

    ui_print(f"\n[Param Generator] Configuring parameters for methylong (nfcore)...")

    run_dir = get_or_create_run_dir()

    # Locate or write the samplesheet
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
        # run_dir not available — create one now so we don't pollute session_dir
        session_dir = get_session_dir()
        if session_dir:
            run_dir = get_or_create_run_dir()
        if run_dir:
            pf = pre_files[0]
            safe_name = os.path.basename(pf["filename"])
            dest = os.path.join(run_dir, safe_name)
            with open(dest, "w", encoding="utf-8") as _f:
                _f.write(pf["content"])
            input_path = dest

    # Ask LLM (with RAG) for optional params
    llm_params = _select_optional_params(user_input)

    # Validate against whitelist
    from tools.methylong.validator import validate_optional_params
    valid_optional, warnings = validate_optional_params(llm_params)
    for w in warnings:
        ui_print(f"[Param Generator] WARNING: {w}")

    # Assemble kwargs: required base + validated optional
    kwargs = {
        "pipeline": selected_workflow,
        "input":    input_path,
        "outdir":   "results",
    }
    kwargs.update(valid_optional)

    tool_call = {
        "tool_name": selected_workflow,
        "tool_args": {"kwargs": kwargs},
    }

    ui_print(f"[Param Generator] pipeline={selected_workflow}, input={input_path}")
    if valid_optional:
        ui_print(f"[Param Generator] Optional params: {valid_optional}")

    state["tool_calls"] = [tool_call]
    return state
