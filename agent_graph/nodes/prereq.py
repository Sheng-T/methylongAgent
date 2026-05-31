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
        "- method: sequencing platform. Accepted values: 'ont' or 'pacbio'.\n"
        "  RULES:\n"
        "  1. Default to 'ont' if the user does not explicitly mention PacBio or HiFi.\n"
        "  2. Use 'pacbio' only when the user explicitly says 'PacBio', 'HiFi', or 'pb'.\n"
        "  3. DO NOT infer method from the filename."
    ),
}


_GENERATED_FILES = {"samplesheet.csv"}


def _list_session_files(session_dir: str) -> list[str]:
    """Return full absolute paths of uploaded files in session_dir, excluding generated files."""
    if not session_dir or not os.path.isdir(session_dir):
        return []
    return [
        e.path for e in os.scandir(session_dir)
        if e.is_file() and e.name not in _GENERATED_FILES
    ]


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
    user_feedback  = state.get("user_feedback", "")
    lang           = get_lang()
    from utils.llm_utils import get_llm_instance
    llm            = get_llm_instance(is_planner=True)

    prereq = METHYLONG_PREREQ
    filename = prereq["filename"]

    if user_feedback:
        print(f"[PrereqGenerator] Re-generating with user feedback: {user_feedback!r}")

    prompt = build_prereq_prompt(prereq, uploaded_files, user_input, lang, feedback=user_feedback)

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
            print(f"[PrereqGenerator] {filename} validation failed (attempt {attempt}): {fail_reason}")
            content = ""
        except Exception as e:
            print(f"[PrereqGenerator] Attempt {attempt} exception: {e}")
            content = ""

    if not content:
        print(f"[PrereqGenerator] ERROR: {filename} still invalid after {MAX_RETRIES} attempts: {fail_reason}")
        return {"pre_files": [], "samplesheet_issues": []}

    content = _fix_paths(content, uploaded_files)
    issues = _validate_samplesheet(content, user_input)
    if issues:
        for issue in issues:
            print(f"[PrereqGenerator] {issue['level'].upper()}: {issue['message']}")

    return {
        "pre_files":          [{"filename": filename, "content": content}],
        "user_feedback":      "",
        "samplesheet_issues": issues,
    }


_REF_EXTENSIONS = {".fa", ".fasta", ".fna"}


def _fix_paths(content: str, uploaded_files: list[str]) -> str:
    """Fix wrong-directory paths and auto-fill empty ref from uploaded files."""
    if not uploaded_files:
        return content
    basename_map = {os.path.basename(f): f for f in uploaded_files}
    ref_candidates = [f for f in uploaded_files
                      if os.path.splitext(f)[1].lower() in _REF_EXTENSIONS]

    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    except Exception:
        return content

    changed = False
    for row in rows:
        # Fix wrong-directory paths via basename match
        for col in ("path", "ref"):
            val = (row.get(col) or "").strip()
            if not val or os.path.isfile(val):
                continue
            basename = os.path.basename(val)
            if basename in basename_map:
                print(f"[PrereqGenerator] Path corrected: {val!r} → {basename_map[basename]!r}")
                row[col] = basename_map[basename]
                changed = True

        # Auto-fill empty ref from uploaded .fa/.fasta/.fna files
        if "ref" in fieldnames and not (row.get("ref") or "").strip() and ref_candidates:
            row["ref"] = ref_candidates[0]
            print(f"[PrereqGenerator] ref auto-filled: {ref_candidates[0]!r}")
            changed = True

    if not changed:
        return content

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


_DMR_KEYWORDS = {
    "dmr", "differential methylation", "population-scale", "population scale",
    "group comparison", "between groups", "compare groups", "dmr analysis",
    "差异甲基化", "群体分析", "组间比较", "组间差异", "样本组比较",
}

_HAPLOTYPE_KEYWORDS = {
    "haplotype", "haplotype-level", "haplotype level",
    "allele-specific", "allele specific", "ase", "phased",
    "单倍型", "等位基因特异", "相位",
}


def _user_wants_dmr(user_input: str) -> bool:
    lower = user_input.lower()
    return any(k in lower for k in _DMR_KEYWORDS)


def _user_wants_haplotype(user_input: str) -> bool:
    lower = user_input.lower()
    return any(k in lower for k in _HAPLOTYPE_KEYWORDS)


def _validate_samplesheet(content: str, user_input: str) -> list[dict]:
    """
    Validate the generated samplesheet for common biological / data errors.
    Returns list of {"level": "error"|"warning", "message": str}.
    """
    issues: list[dict] = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception:
        return issues

    # ── 1. Missing files ───────────────────────────────────────────────────────
    for i, row in enumerate(rows, 1):
        for col in ("path", "ref"):
            p = (row.get(col) or "").strip()
            if p and not os.path.isfile(p):
                issues.append({
                    "level": "error",
                    "message": f"Row {i}: file not found — `{p}`",
                })

    # ── 2. ONT BAM without MM/ML modification tags ────────────────────────────
    for i, row in enumerate(rows, 1):
        method = (row.get("method") or "").strip().lower()
        path   = (row.get("path")   or "").strip()
        if method == "ont" and path.lower().endswith(".bam") and os.path.isfile(path):
            try:
                from tools.methylong.command_builder import _bam_has_mod_tags
                if not _bam_has_mod_tags(path):
                    issues.append({
                        "level": "error",
                        "message": (
                            f"Row {i}: ONT BAM `{os.path.basename(path)}` has no MM/ML "
                            "modification tags. Methylation analysis requires a modBAM "
                            "(basecalled with Dorado + modification model) or pod5 files."
                        ),
                    })
            except Exception:
                pass

    # ── 3. DMR group validation ────────────────────────────────────────────────
    if _user_wants_dmr(user_input) and not _user_wants_haplotype(user_input):
        groups: dict[str, list] = {}
        for row in rows:
            g = (row.get("group") or "").strip()
            groups.setdefault(g, []).append(row)

        if len(groups) < 2:
            g_name = list(groups.keys())[0] if groups else "unknown"
            issues.append({
                "level": "error",
                "message": (
                    f"DMR analysis requires ≥ 2 distinct groups, but all samples belong "
                    f"to group '{g_name}'. Please assign samples to at least two groups."
                ),
            })
        else:
            singleton_groups = [g for g, members in groups.items() if len(members) == 1]
            if singleton_groups:
                issues.append({
                    "level": "warning",
                    "message": (
                        f"Groups {singleton_groups} have only 1 sample each. "
                        "Statistical DMR calling (DSS / modkit dmr) needs replicates "
                        "for robust p-values. Results may not be statistically reliable."
                    ),
                })

    return issues


def human_prereq_reviewer_node(state: AgentState) -> dict:
    """
    Pass-through interrupt node between prereq_generator and param_generator.
    The graph pauses BEFORE this node so the UI can render an editable samplesheet.
    The UI calls app.update_state({"pre_files": edited}) then resumes — this node
    just forwards state unchanged.
    """
    _ = state  # intentionally unused
    return {}
