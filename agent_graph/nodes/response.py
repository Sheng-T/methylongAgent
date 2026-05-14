"""
Response nodes: Q&A answering, workflow summarizer, irrelevant handler, and finish node.
"""
import json
import os
import re
import shutil
import zipfile
from datetime import datetime

from agent_graph.state import AgentState
from utils.llm_utils import get_llm_instance
from utils.lang_utils import get_lang
from utils.user_context import get_session_dir
from utils.ui_logger import ui_print
from configs.app_config import APP_SNAKE


def answer_general_question_node(state: AgentState) -> AgentState:
    """Answer methylation/bioinformatics Q&A questions."""
    from agent_graph.prompts.prompts import build_qa_prompt

    user_input = state["input"]
    lang = get_lang()

    try:
        ui_print(f"\n[LLM Answer] Invoking LLM: {user_input[:60]}...")
        llm = get_llm_instance(is_planner=False)
        final_prompt = build_qa_prompt(user_input, "", lang)
        llm_response = llm.invoke(final_prompt)
        llm_response = llm_response.strip() if isinstance(llm_response, str) else llm_response.content.strip()
        llm_response = re.sub(r"<think>.*?</think>", "", llm_response, flags=re.DOTALL).strip()
        state["final_answer"] = llm_response
    except Exception as e:
        ui_print(f"[LLM Answer] Failed: {e}")
        state["final_answer"] = (
            "Sorry, the service is temporarily unavailable."
            if lang == "en_US" else
            "抱歉，服务暂时不可用，无法回答您的问题。"
        )

    answer = state["final_answer"]
    if not answer:
        answer = "(no content)"
    if len(answer) > 1000:
        ui_print(f'\n[LLM Answer]\n{answer[:1000]}\n...\n[{len(answer)} chars total]')
    else:
        ui_print(f'\n[LLM Answer]\n{answer}')

    return state


def summarize_execution_result_node(state: AgentState) -> AgentState:
    """
    Workflow summarizer: runs the methylong-specific analyzer, packages results,
    and generates an LLM report.
    """
    from tools.analyzers.methylong import get_methylong_analyzer

    lang          = get_lang()
    tool_calls    = state.get("tool_calls", [])
    tool_output   = state.get("tool_output", [])
    run_dir       = state.get("run_dir", "")
    workflow_name = "methylong"

    _NF_INTERNAL = {"work", f"{APP_SNAKE}_analysis"}
    outdir = os.path.join(run_dir, "results") if run_dir else ""
    if outdir and not os.path.isdir(outdir):
        if run_dir and os.path.isdir(run_dir):
            for entry in sorted(os.scandir(run_dir), key=lambda e: e.name):
                if (entry.is_dir()
                        and entry.name not in _NF_INTERNAL
                        and not entry.name.startswith(".")
                        and not entry.name.startswith("work")):
                    outdir = entry.path
                    break
        else:
            outdir = ""

    analysis_dir = os.path.join(run_dir, f"{APP_SNAKE}_analysis", workflow_name) if run_dir else ""
    if analysis_dir:
        os.makedirs(analysis_dir, exist_ok=True)

    if run_dir and os.path.isdir(run_dir):
        _children = [e.name for e in os.scandir(run_dir)]
        ui_print(f"[WorkflowSummarizer] run_dir contents: {_children}")
    ui_print(f"[WorkflowSummarizer] workflow={workflow_name}  outdir={outdir}")

    plot_paths: list[str] = []
    warnings:   list[str] = []
    summary:    dict      = {}

    if outdir and os.path.isdir(outdir):
        analyzer = get_methylong_analyzer()
        ui_print(f"[WorkflowSummarizer] Using methylong-specific analyzer")
        try:
            result     = analyzer.analyze(outdir, analysis_dir)
            summary    = result.get("summary", {})
            plot_paths = result.get("plot_paths", [])
            warnings   = result.get("warnings", [])
        except Exception as e:
            ui_print(f"[WorkflowSummarizer] Analyzer error: {e}")
            warnings.append(f"Workflow analyzer error: {e}")
    else:
        warnings.append(f"outdir not found or empty: {outdir}")

    # Package results into a zip file (exclude large binary files)
    _SKIP_EXTS = {".bam", ".bai", ".cram", ".crai", ".sam"}
    zip_path = ""
    if outdir and os.path.isdir(outdir) and run_dir:
        temp_zip = os.path.join(run_dir, f"{workflow_name}_results.zip")
        try:
            ui_print("[WorkflowSummarizer] Creating results zip (excluding BAM/CRAM)...")
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for root, _, files in os.walk(outdir):
                    for fname in files:
                        if any(fname.endswith(ext) for ext in _SKIP_EXTS):
                            continue
                        full = os.path.join(root, fname)
                        arcname = os.path.relpath(full, os.path.dirname(outdir))
                        zf.write(full, arcname)
            size_mb = os.path.getsize(temp_zip) / 1024 / 1024
            ui_print(f"[WorkflowSummarizer] Zip ready: {temp_zip} ({size_mb:.1f} MB)")

            session_dir = get_session_dir()
            zip_moved = False
            if session_dir and os.path.isdir(session_dir):
                try:
                    zip_path = os.path.join(session_dir,
                        f"{workflow_name}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
                    shutil.move(temp_zip, zip_path)
                    ui_print(f"[WorkflowSummarizer] Zip moved to session: {zip_path}")
                    zip_moved = True
                except Exception as move_err:
                    ui_print(f"[WorkflowSummarizer] Move to session failed: {move_err}, keeping in run_dir")
                    zip_path = temp_zip
            else:
                ui_print(f"[WorkflowSummarizer] session_dir unavailable, keeping zip in run_dir")
                zip_path = temp_zip

            if zip_moved and os.path.isdir(run_dir):
                try:
                    ui_print(f"[WorkflowSummarizer] Cleaning up run directory: {run_dir}")
                    shutil.rmtree(run_dir, ignore_errors=True)
                    ui_print("[WorkflowSummarizer] Run directory deleted")
                except Exception as e:
                    ui_print(f"[WorkflowSummarizer] Cleanup warning: {e}")
        except Exception as e:
            ui_print(f"[WorkflowSummarizer] Zip failed: {e}")
            zip_path = ""

    # Generate LLM report
    raw_out   = "\n".join(tool_output).strip()[:800]
    stats_txt = json.dumps(summary, ensure_ascii=False, indent=2)[:4000]
    warn_txt  = "\n".join(f"- {w}" for w in warnings) or "None"

    if lang == "en_US":
        prompt = f"""You are a bioinformatics expert. Generate a professional Markdown report for a completed methylong Nextflow workflow run.

[Workflow]: {workflow_name}
[Runtime output (excerpt)]:
{raw_out}

[Analysis statistics]:
{stats_txt}

[Warnings / issues]:
{warn_txt}

Requirements:
1. One-sentence overall summary (completed / partial / failed).
2. Per-sample key metrics (mapping rate, mean methylation, CpG coverage, etc. as available).
3. Biological interpretation of the results.
4. Warnings section with actionable recommendations.
5. Markdown only. Do not echo raw JSON or internal log lines."""
    else:
        prompt = f"""你是生物信息学专家，请根据以下信息生成一份专业的 Markdown 报告。

【Workflow】：{workflow_name}
【运行输出（摘要）】：
{raw_out}

【分析统计数据】：
{stats_txt}

【警告信息】：
{warn_txt}

要求：
1. 一句话总体概况（完成/部分完成/失败）。
2. 按样本列出关键指标（比对率、平均甲基化率、CpG 覆盖率等）。
3. 结合数据给出生物学解读。
4. 列出警告并给出建议。
5. 只输出 Markdown，不输出原始 JSON 或内部日志。"""

    try:
        raw    = get_llm_instance(is_planner=False).invoke(prompt)
        report = raw if isinstance(raw, str) else raw.content
        report = re.sub(r"<think>.*?</think>", "", report, flags=re.DOTALL).strip()
    except Exception as e:
        report = (f"### methylong Workflow Completed\n\nReport generation error: {e}"
                  if lang == "en_US" else
                  f"### methylong 流水线已完成\n\n报告生成失败：{e}")

    state["final_answer"]        = report
    state["analysis_images"]     = [p for p in plot_paths if os.path.isfile(p)]
    state["workflow_result_zip"] = zip_path
    return state


def handle_irrelevant_request_node(state: AgentState) -> AgentState:
    ui_print("\n[Irrelevant] Generating off-topic reply...")
    lang = get_lang()
    state["final_answer"] = (
        "Sorry, I specialise in nanopore methylation sequencing analysis with the methylong pipeline. "
        "I cannot help with that request."
        if lang == "en_US" else
        "抱歉，我专注于使用 methylong 流水线进行纳米孔甲基化测序分析，无法为您提供该信息。"
    )
    ui_print(f'\n[LLM Answer] {state["final_answer"]}')
    return state


def finish_session_node(state: AgentState) -> AgentState:
    ui_print("\n[End] Session complete")
    return state
