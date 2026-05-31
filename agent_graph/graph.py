"""
MethylAgent graph — focused exclusively on the methylong Nextflow pipeline.

Graph flow:
  router → [answer branch:    llm_answer → END]
          → [irrelevant branch: irrelevant → END]
          → [workflow branch: prereq_generator → human_prereq_reviewer (interrupt_before) →
                              param_generator → human_reviewer (interrupt_after) →
                              executor → summarizer → END]
"""
from langgraph.graph import END, StateGraph

from agent_graph.state import AgentState
from agent_graph.nodes.router   import reset_and_route_node, classify_intent_route
from agent_graph.nodes.prereq   import generate_prereqs_node, human_prereq_reviewer_node
from agent_graph.nodes.params   import generate_tool_params_node
from agent_graph.nodes.review   import review_execution_plan_node
from agent_graph.nodes.runner   import execute_commands_node
from agent_graph.nodes.response import (
    answer_general_question_node,
    summarize_execution_result_node,
    handle_irrelevant_request_node,
    finish_session_node,
)
from configs.app_config import APP_SNAKE


def save_graph_image(app_instance, filename=None):
    if filename is None:
        filename = f"{APP_SNAKE}_graph.txt"
    try:
        mermaid_code = app_instance.get_graph().draw_mermaid()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"\n[System] Graph diagram saved to: {filename}")
    except Exception as e:
        print(f"\n[System] Failed to save graph: {e}")


def create_agent_graph(agent_name: str,
                       is_save_graph_image: bool = False,
                       graph_image_filename: str = "") -> StateGraph:
    workflow = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    workflow.add_node("router",               reset_and_route_node)
    workflow.add_node("prereq_generator",     generate_prereqs_node)
    workflow.add_node("human_prereq_reviewer", human_prereq_reviewer_node)
    workflow.add_node("param_generator",      generate_tool_params_node)
    workflow.add_node("human_reviewer",       review_execution_plan_node)
    workflow.add_node("executor",             execute_commands_node)
    workflow.add_node("summarizer",           summarize_execution_result_node)
    workflow.add_node("llm_answer",           answer_general_question_node)
    workflow.add_node("irrelevant",           handle_irrelevant_request_node)
    workflow.add_node("end_node",             finish_session_node)

    # ── Entry ──────────────────────────────────────────────────────────────────
    workflow.set_entry_point("router")

    # ── Router edges ───────────────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "router",
        lambda state: classify_intent_route(state),
        {
            "route_to_workflow":   "prereq_generator",
            "route_to_answer":     "llm_answer",
            "route_to_irrelevant": "irrelevant",
        }
    )

    # ── Workflow path ──────────────────────────────────────────────────────────
    workflow.add_edge("prereq_generator", "human_prereq_reviewer")
    workflow.add_conditional_edges(
        "human_prereq_reviewer",
        lambda state: "prereq_generator" if state.get("user_feedback") else "param_generator",
        {"prereq_generator": "prereq_generator", "param_generator": "param_generator"},
    )
    workflow.add_edge("param_generator",       "human_reviewer")

    workflow.add_conditional_edges(
        "human_reviewer",
        lambda state: state.get("next_node") or "param_generator",
        {
            "executor":         "executor",
            "param_generator":  "param_generator",
            "prereq_generator": "prereq_generator",
            "end_node":         "end_node",
        }
    )

    workflow.add_conditional_edges(
        "executor",
        lambda state: state.get("next_node") or "summarizer",
        {
            "param_generator": "param_generator",
            "summarizer":      "summarizer",
        }
    )

    # ── Terminal edges ─────────────────────────────────────────────────────────
    workflow.add_edge("llm_answer",  END)
    workflow.add_edge("summarizer",  END)
    workflow.add_edge("irrelevant",  END)
    workflow.add_edge("end_node",    END)

    # ── Compile ────────────────────────────────────────────────────────────────
    from storage.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "human_prereq_reviewer",   # user reviews/edits the generated samplesheet
        ],
        interrupt_after=[
            "human_reviewer",          # user reviews pending commands before executor runs
        ],
    )
    app.name = agent_name

    if is_save_graph_image:
        save_graph_image(app, graph_image_filename or f"{APP_SNAKE}_graph.txt")

    return app
