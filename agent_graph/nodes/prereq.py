"""
Prerequisite file generation node for methylong (nfcore) workflow.
Generates a CSV samplesheet from uploaded files using LLM.
"""
import csv
import io
import os
import re

from agent_graph.state import AgentState
from agent_graph.prompts.prompts import build_prereq_prompt
from utils.llm_utils import get_llm_instance
from utils.lang_utils import get_lang
from utils.user_context import get_session_dir


# Methylong samplesheet specification
METHYLONG_PREREQ = {
    "type": "csv",
    "filename": "samplesheet.csv",
    "columns": ["group", "sample", "path", "ref", "method"],
    "example_row": "group1,sample1,/data/uploads/abc123/sample1.bam,/data/uploads/abc123/genome.fa,ont",
    "description": (
        "methylong samplesheet — one row per sample.\n"
        "- group: sample group name. Auto-generate as 'group1', 'group2'... if not specified.\n"
        "- sample: sample name. Use input filename without extension if not specified.\n"
        "- path: FULL absolute path to the BAM or pod5 file.\n"
        "- ref: FULL absolute path to the reference genome FASTA.\n"
        "- method: sequencing platform — 'pacbio' or 'ont'."
    ),
}


def _list_session_files(session_dir: str) -> list[str]:
    """Return full absolute paths of all files in session_dir (no subdirectories)."""
    if not session_dir or not os.path.isdir(session_dir):
        return []
    return [e.path for e in os.scandir(session_dir) if e.is_file()]


def _parse_content(raw) -> str:
    content = raw if isinstance(raw, str) else raw.content
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    content = re.sub(r"<think>.*",          "", content, flags=re.DOTALL)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    return content


def _validate_csv(content: str, required_cols: list[str]) -> tuple[bool, str]:
    if not content:
        return False, "content is empty"
    try:
        reader = csv.DictReader(io.StringIO(content))
        header = reader.fieldnames or []
        missing_cols = [c for c in required_cols if c not in header]
        if missing_cols:
            return False, f"missing columns: {missing_cols} (got header: {header})"
        data_rows = [r for r in reader if any(v.strip() for v in r.values())]
        if not data_rows:
            return False, "header present but no data rows"
        for row_idx, row in enumerate(data_rows, 1):
            empty_cols = [c for c in required_cols if not (row.get(c) or "").strip()]
            if empty_cols:
                return False, f"row {row_idx} has empty values for required columns: {empty_cols}"
    except Exception as exc:
        return False, f"CSV parse error: {exc}"
    return True, ""


def generate_prereqs_node(state: AgentState) -> dict:
    """Generate samplesheet CSV for methylong pipeline."""
    session_dir    = get_session_dir()
    uploaded_files = _list_session_files(session_dir)
    user_input     = state.get("input", "")
    lang           = get_lang()
    llm            = get_llm_instance(is_planner=True)

    prereq = METHYLONG_PREREQ
    filename = prereq["filename"]
    print(f"[PrereqGenerator] Generating {filename}...")

    prompt = build_prereq_prompt(prereq, uploaded_files, user_input, lang)

    MAX_RETRIES = 3
    content = ""
    fail_reason = ""

    expected_header = ",".join(prereq["columns"])

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = llm.invoke(prompt)
            content = _parse_content(raw)
            # Safety net: prepend header if LLM omitted it
            first_line = content.split("\n", 1)[0].strip() if content else ""
            if first_line and first_line != expected_header:
                print(f"[PrereqGenerator] Header missing — prepending. Got first line: {first_line!r}")
                content = expected_header + "\n" + content
            ok, fail_reason = _validate_csv(content, prereq["columns"])
            if ok:
                print(f"[PrereqGenerator] {filename} validated (attempt {attempt})")
                break
            print(f"[PrereqGenerator] {filename} validation failed (attempt {attempt}): {fail_reason}, retrying...")
            content = ""
        except Exception as e:
            print(f"[PrereqGenerator] Attempt {attempt} exception: {e}")
            content = ""

    if not content:
        print(f"[PrereqGenerator] ERROR: {filename} still invalid after {MAX_RETRIES} attempts: {fail_reason}")
        return {"pre_files": []}

    return {"pre_files": [{"filename": filename, "content": content}]}


def human_prereq_reviewer_node(state: AgentState) -> dict:
    """
    Pass-through interrupt node between prereq_generator and param_generator.
    The graph pauses BEFORE this node so the UI can render an editable samplesheet.
    The UI calls app.update_state({"pre_files": edited}) then resumes — this node
    just forwards state unchanged.
    """
    _ = state  # intentionally unused
    return {}
