"""
Router node: classifies intent and resets session state for new requests.
Routes to: "workflow", "answer", or "irrelevant".
"""
import json
import re

from agent_graph.state import AgentState, EMPTY_STATE
from agent_graph.prompts.prompts import build_router_prompt
from utils.llm_utils import get_llm_instance
from utils.lang_utils import get_lang
from utils.nodes_utils import format_history
from utils.ui_logger import ui_print


def reset_and_route_node(state: AgentState) -> dict:
    """Reset session state and classify the user's intent."""
    # Reset transient fields for a fresh run
    updates = {k: v for k, v in EMPTY_STATE.items()}
    updates["input"]            = state.get("input", "")
    updates["chat_history"]     = state.get("chat_history", [])
    updates["user_choice"]      = state.get("user_choice")
    updates["selected_workflow"] = "methylong"
    updates["workflow_type"]    = "nfcore"

    return updates


def classify_intent_route(state: AgentState) -> str:
    """
    Determine routing from router node.
    Returns: "route_to_workflow" | "route_to_answer" | "route_to_irrelevant"
    """
    user_choice = state.get("user_choice")
    user_input  = state.get("input", "").strip().lower()
    lang        = get_lang()

    # FASTQ is not a supported input — intercept regardless of user_choice
    fastq_kw = ["fastq", ".fq", "fq.gz", "fastq.gz"]
    if any(kw in user_input for kw in fastq_kw):
        ui_print("[Router] FASTQ input detected → routing to answer for format explanation")
        return "route_to_answer"

    # PacBio + Dorado is an invalid combination — Dorado is ONT-only
    pacbio_kw = ["pacbio", "hifi", "pb"]
    dorado_kw = ["dorado"]
    if any(k in user_input for k in pacbio_kw) and any(k in user_input for k in dorado_kw):
        ui_print("[Router] PacBio + Dorado combination detected → routing to answer for explanation")
        return "route_to_answer"

    # Explicit mode from UI
    if user_choice == "workflow":
        ui_print("[Router] User selected workflow mode directly")
        return "route_to_workflow"
    if user_choice == "answer":
        ui_print("[Router] User selected answer mode directly")
        return "route_to_answer"
    if user_choice in ("auto", None):
        pass  # fall through to LLM classification

    # Quick keyword heuristics — only unambiguous execution signals
    workflow_kw = [
        "bam", "pod5", "samplesheet", "样本表",
        "nextflow run", "run pipeline", "运行流水线", "运行pipeline",
        "run methylong", "run the methylong", "analyze my", "analyse my",
        "run the pipeline", "start the pipeline", "launch the pipeline",
        "跑流水线", "跑methylong", "分析我的",
    ]
    if any(kw in user_input for kw in workflow_kw):
        ui_print("[Router] Keyword match → workflow")
        return "route_to_workflow"

    # LLM classification
    try:
        history_str = format_history(state.get("chat_history", []))
        llm = get_llm_instance(is_planner=True)
        prompt = build_router_prompt(lang).format(
            input=state.get("input", ""),
            history=history_str,
        )
        raw = llm.invoke(prompt)
        content = raw if isinstance(raw, str) else raw.content
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        # extract JSON object from possible markdown fences or surrounding text
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m:
            content = m.group(0)
        parsed = json.loads(content)
        intent = parsed.get("intent", "answer")
        ui_print(f"[Router] LLM intent: {intent} — {parsed.get('reason', '')}")
        if intent == "workflow":
            return "route_to_workflow"
        elif intent == "irrelevant":
            return "route_to_irrelevant"
        else:
            return "route_to_answer"
    except Exception as e:
        ui_print(f"[Router] Classification failed ({e}), defaulting to answer")
        return "route_to_answer"
