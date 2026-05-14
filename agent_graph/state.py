from typing import TypedDict, List, Dict

EMPTY_STATE = {
    "tool_calls":        [],
    "tool_output":       [],
    "rag_suggestion":    {},
    "user_feedback":     "",
    "final_answer":      "",
    "next_node":         "",
    "selected_workflow": "methylong",
    "workflow_type":     "nfcore",
    "pending_commands":  [],
    "pre_files":         [],
    "run_dir":           "",
    "analysis_images":   [],
    "workflow_result_zip": "",
    "user_choice":       None,
}


class AgentState(TypedDict):
    """Core state passed between graph nodes."""

    input: str
    user_choice: str | None

    tool_calls: List[Dict]
    tool_output: List[str]
    rag_suggestion: dict
    user_feedback: str
    final_answer: str
    chat_history: List[Dict[str, str]]
    next_node: str

    # Workflow state — always methylong/nfcore in this agent
    workflow_type: str       # always "nfcore"
    selected_workflow: str   # always "methylong"

    pending_commands: List[str]
    pre_files: List[Dict]
    run_dir: str
    analysis_images: List[str]
    workflow_result_zip: str
