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


_RESULTS_KEYWORDS = {
    "show me result", "show result", "show me the result",
    "view result", "view the result", "get result", "my result",
    "download result", "download the result",
    "查看结果", "显示结果", "我的结果", "下载结果", "结果在哪", "结果怎么下载",
}

_HELP_KEYWORDS = {
    "how to use", "how do i use", "how do i start", "getting started",
    "how does this work", "what should i do", "where do i start",
    "怎么用", "如何使用", "怎么开始", "如何开始", "怎么操作", "使用说明",
}

_CAPABILITY_KEYWORDS = {
    "what can you do", "what are your capabilities", "what do you support",
    "what can this do", "what is this", "what does this agent do",
    "你能做什么", "你有什么功能", "这个agent能做什么", "支持什么功能",
    "功能介绍", "能做什么",
}

_FORMAT_KEYWORDS = {
    "what file", "supported format", "what format", "file type", "what input",
    "支持什么文件", "支持什么格式", "什么格式", "什么文件", "上传什么", "文件格式",
}


def _match_any(text: str, keywords: set) -> bool:
    lower = text.lower()
    return any(k in lower for k in keywords)


_CANNED = {
    "help_en": """\
### 🚀 Getting Started

MethylongAgent helps you run nanopore methylation analysis through a conversational interface.

**Typical workflow:**
1. **Upload files** — Use the **📁 File Management** panel in the left sidebar to upload your BAM or POD5 files (and reference genome if needed)
2. **Describe your analysis** — Type your request, e.g. *"Run 5mC methylation analysis on my ONT BAM files"*
3. **Review the samplesheet** — The agent auto-generates a CSV samplesheet; verify paths and confirm
4. **Confirm commands** — Review the generated Nextflow commands, then click **▶ Yes, run it**
5. **Get results** — Download buttons appear automatically after the pipeline completes

**Tips:**
- For files > 1 GB, upload directly to the server and use the **📋** button next to File Management to copy the session path
- Use the mode pills (**🔄 Auto / 🔬 Run Workflow / 💬 Q&A**) to control routing
- Use **💬 Submit Revision** in the command review panel to adjust parameters before running
""",
    "help_zh": """\
### 🚀 快速上手

MethylongAgent 通过对话界面帮助你完成纳米孔甲基化测序分析。

**典型流程：**
1. **上传文件** — 在左侧边栏 **📁 文件管理** 面板上传 BAM 或 POD5 文件（如需可同时上传参考基因组）
2. **描述需求** — 在对话框输入分析需求，例如 *"对我的 ONT BAM 文件做 5mC 甲基化分析"*
3. **确认样本表** — Agent 自动生成 CSV 样本表，检查路径无误后确认
4. **确认命令** — 查看生成的 Nextflow 命令，点击 **▶ 确认运行**
5. **获取结果** — 流水线完成后下载按钮自动出现在页面底部

**小贴士：**
- 文件 > 1 GB 时建议直接上传到服务器，点击文件管理旁的 **📋** 按钮复制会话路径
- 可用顶部模式选择（**🔄 自动 / 🔬 执行流水线 / 💬 问答**）控制路由
- 在命令确认面板使用 **💬 提交修改** 可以在运行前调整参数
""",
    "capability_en": """\
### 🧬 What MethylongAgent Can Do

I specialize in nanopore methylation sequencing analysis using the **methylong** Nextflow pipeline.

**Pipeline tasks:**
- 5mC / 5hmC / CpG methylation analysis on ONT modBAM or POD5 files
- Dorado basecalling from raw POD5 files (GPU required)
- DMR (Differentially Methylated Region) analysis across sample groups
- PacBio HiFi methylation analysis

**Q&A:**
- Methylation biology questions (5mC, CpG islands, DMR interpretation, etc.)
- Pipeline parameter guidance
- Troubleshooting failed runs

**I cannot** handle unrelated bioinformatics tasks (e.g. variant calling, RNA-seq, ChIP-seq).
""",
    "capability_zh": """\
### 🧬 MethylongAgent 能做什么

我专注于使用 **methylong** Nextflow 流水线进行纳米孔甲基化测序分析。

**流水线任务：**
- ONT modBAM 或 POD5 文件的 5mC / 5hmC / CpG 甲基化分析
- 从原始 POD5 进行 Dorado 碱基识别（需要 GPU）
- 跨样本组的 DMR（差异甲基化区域）分析
- PacBio HiFi 甲基化分析

**问答：**
- 甲基化生物学问题（5mC、CpG 岛、DMR 解读等）
- 流水线参数建议
- 运行失败的排查

**无法处理**与甲基化无关的生信任务（如变异检测、RNA-seq、ChIP-seq）。
""",
    "format_en": """\
### 📁 Supported File Formats

| Type | Extension | Notes |
|------|-----------|-------|
| ONT modBAM | `.bam` | Must contain MM/ML methylation tags (Dorado output) |
| POD5 raw signal | `.pod5` | Dorado basecalling will be run automatically |
| PacBio HiFi BAM | `.bam` | Specify *pacbio* as method; mention "PacBio" or "HiFi" in your request |
| Reference genome | `.fa` / `.fasta` / `.fna` | Required for alignment; auto-detected from uploaded files if not specified |

**Large files (> 1 GB):** Upload directly to the server rather than through the browser.
Use the **📋** button next to File Management in the sidebar to copy the session upload path.
""",
    "format_zh": """\
### 📁 支持的文件格式

| 类型 | 扩展名 | 说明 |
|------|--------|------|
| ONT modBAM | `.bam` | 必须包含 MM/ML 甲基化标签（Dorado 输出） |
| POD5 原始信号 | `.pod5` | 自动触发 Dorado 碱基识别 |
| PacBio HiFi BAM | `.bam` | 需在需求中注明 "PacBio" 或 "HiFi"，method 填 pacbio |
| 参考基因组 | `.fa` / `.fasta` / `.fna` | 对齐必需；未指定时自动从上传文件中检测 |

**大文件（> 1 GB）：** 建议直接上传到服务器，
点击侧边栏文件管理旁的 **📋** 按钮复制会话上传路径。
""",
}



def answer_general_question_node(state: AgentState) -> AgentState:
    """Answer methylation/bioinformatics Q&A questions, with RAG context from local docs."""
    from agent_graph.prompts.prompts import build_qa_prompt
    from utils.rag_utils import rag_search

    user_input   = state["input"]
    lang         = get_lang()
    zip_path     = state.get("workflow_result_zip", "")
    images       = state.get("analysis_images", [])
    run_dir      = state.get("run_dir", "")

    # ── Short-circuit: deterministic responses for common meta-queries ───────────
    sfx = "en" if lang == "en_US" else "zh"

    if _match_any(user_input, _HELP_KEYWORDS):
        state["final_answer"] = _CANNED[f"help_{sfx}"]
        ui_print("[LLM Answer] help query → canned response")
        return state

    if _match_any(user_input, _CAPABILITY_KEYWORDS):
        state["final_answer"] = _CANNED[f"capability_{sfx}"]
        ui_print("[LLM Answer] capability query → canned response")
        return state

    if _match_any(user_input, _FORMAT_KEYWORDS):
        state["final_answer"] = _CANNED[f"format_{sfx}"]
        ui_print("[LLM Answer] format query → canned response")
        return state

    if _match_any(user_input, _RESULTS_KEYWORDS):
        if zip_path and os.path.isfile(zip_path):
            chart_line_en = f"- **Analysis charts**: {len(images)} plot(s) displayed above\n" if images else ""
            chart_line_zh = f"- **分析图表**：上方已展示 {len(images)} 张\n" if images else ""
            if lang == "en_US":
                state["final_answer"] = (
                    f"### ✅ Pipeline Complete — Results Ready\n\n"
                    f"- **Results ZIP**: `{os.path.basename(zip_path)}`\n"
                    f"  → Click the **⬇ Download Results (.zip)** button below\n"
                    f"{chart_line_en}"
                    f"\n> Run directory: `{run_dir}`"
                )
            else:
                state["final_answer"] = (
                    f"### ✅ 流水线已完成，结果就绪\n\n"
                    f"- **结果压缩包**：`{os.path.basename(zip_path)}`\n"
                    f"  → 点击下方 **⬇ 下载结果压缩包 (.zip)** 按钮下载\n"
                    f"{chart_line_zh}"
                    f"\n> 运行目录：`{run_dir}`"
                )
        else:
            state["final_answer"] = (
                "### 📭 No Results Yet\n\n"
                "The methylong pipeline hasn't been run in this session.\n\n"
                "**To get started:**\n"
                "1. Upload your BAM or POD5 files using the **File Management** panel in the sidebar\n"
                "2. Describe your analysis in the chat (e.g. *\"Run 5mC methylation analysis on my ONT BAM files\"*)\n"
                "3. Confirm the samplesheet and commands when prompted\n\n"
                "Once the pipeline completes, download buttons for the results ZIP and report will appear automatically."
                if lang == "en_US" else
                "### 📭 暂无结果\n\n"
                "本次会话尚未运行 methylong 流水线。\n\n"
                "**快速开始：**\n"
                "1. 在左侧边栏 **文件管理** 面板上传 BAM 或 POD5 文件\n"
                "2. 在对话框中描述分析需求（例如：*\"对我的 ONT BAM 文件做 5mC 甲基化分析\"*）\n"
                "3. 确认样本表和命令后流水线自动运行\n\n"
                "流水线完成后，结果压缩包和报告的下载按钮会自动出现在页面底部。"
            )
        ui_print("[LLM Answer] results query → canned response")
        return state

    # Build results context so LLM can refer to actual outputs
    results_context = ""
    if zip_path and os.path.isfile(zip_path):
        results_context += f"- Results ZIP ready for download from the sidebar: `{os.path.basename(zip_path)}`\n"
    if images:
        results_context += f"- Analysis charts available in the sidebar: {[os.path.basename(p) for p in images]}\n"
    if run_dir:
        results_context += f"- Run directory: `{run_dir}`\n"

    # Query local docs first
    rag_context = ""
    try:
        result = rag_search(user_input, top_k=3)
        if result:
            rag_context = result
            ui_print(f"[RAG] Retrieved {len(rag_context)} chars of context")
        else:
            ui_print("[RAG] No relevant context found, using LLM knowledge only")
    except Exception as e:
        ui_print(f"[RAG] Search failed ({e}), falling back to LLM knowledge")

    try:
        ui_print(f"\n[LLM Answer] Invoking LLM: {user_input[:60]}...")
        llm = get_llm_instance(is_planner=False)
        final_prompt = build_qa_prompt(user_input, rag_context, lang, results_context=results_context)
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

    lang        = get_lang()
    tool_output = state.get("tool_output", [])
    run_dir     = state.get("run_dir", "")
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

    zip_path = ""
    if outdir and os.path.isdir(outdir) and run_dir:
        temp_zip = os.path.join(run_dir, f"{workflow_name}_results.zip")
        try:
            ui_print("[WorkflowSummarizer] Creating results zip...")
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for root, _, files in os.walk(outdir):
                    for fname in files:
                        full = os.path.join(root, fname)
                        arcname = os.path.relpath(full, os.path.dirname(outdir))
                        zf.write(full, arcname)
            size_mb = os.path.getsize(temp_zip) / 1024 / 1024
            ui_print(f"[WorkflowSummarizer] Zip ready: {temp_zip} ({size_mb:.1f} MB)")

            session_dir = get_session_dir()
            if session_dir and os.path.isdir(session_dir):
                try:
                    zip_path = os.path.join(session_dir,
                        f"{workflow_name}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
                    shutil.move(temp_zip, zip_path)
                    ui_print(f"[WorkflowSummarizer] Zip moved to session: {zip_path}")
                except Exception as move_err:
                    ui_print(f"[WorkflowSummarizer] Move to session failed: {move_err}, keeping in run_dir")
                    zip_path = temp_zip
            else:
                ui_print(f"[WorkflowSummarizer] session_dir unavailable, keeping zip in run_dir")
                zip_path = temp_zip

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
