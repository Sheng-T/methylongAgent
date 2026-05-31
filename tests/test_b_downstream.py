"""
B-series downstream analysis test cases.
Tests command builder and samplesheet validation logic directly — no LLM, no UI.

Run: pytest tests/test_b_downstream.py -v
"""
import csv
import io
import sys
import os
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_samplesheet(rows: list[dict]) -> str:
    """Build a CSV samplesheet string from a list of row dicts."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["group", "sample", "path", "ref", "method"],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _write_tmp_samplesheet(tmp_path, rows):
    p = tmp_path / "samplesheet.csv"
    p.write_text(_make_samplesheet(rows))
    return str(p)


# ── B01: haplotype-level DMR, ONT modBAM — no Dorado params ───────────────────

def test_b01_modbam_does_not_need_dorado(tmp_path):
    """ONT modBAM input must NOT trigger --dorado_model in command."""
    from tools.methylong.command_builder import _samplesheet_needs_dorado
    ss = _write_tmp_samplesheet(tmp_path, [
        {"group": "group1", "sample": "hg002.modbam",
         "path": "/data/hg002.modbam.bam", "ref": "/data/hg38.fa", "method": "ont"},
    ])
    assert _samplesheet_needs_dorado(ss) is False, \
        "ONT modBAM should NOT require Dorado basecalling"


def test_b01_pod5_needs_dorado(tmp_path):
    """POD5 input MUST trigger --dorado_model in command."""
    from tools.methylong.command_builder import _samplesheet_needs_dorado
    ss = _write_tmp_samplesheet(tmp_path, [
        {"group": "group1", "sample": "sample1",
         "path": "/data/sample1.pod5", "ref": "/data/hg38.fa", "method": "ont"},
    ])
    assert _samplesheet_needs_dorado(ss) is True, \
        "POD5 input MUST require Dorado basecalling"


def test_b01_mixed_pod5_and_bam_needs_dorado(tmp_path):
    """Mixed POD5 + BAM samplesheet: any POD5 triggers Dorado."""
    from tools.methylong.command_builder import _samplesheet_needs_dorado
    ss = _write_tmp_samplesheet(tmp_path, [
        {"group": "group1", "sample": "s1",
         "path": "/data/s1.pod5", "ref": "/data/hg38.fa", "method": "ont"},
        {"group": "group2", "sample": "s2",
         "path": "/data/s2.bam", "ref": "/data/hg38.fa", "method": "ont"},
    ])
    assert _samplesheet_needs_dorado(ss) is True


# ── B02: population-scale DMR, 4 samples, 2 groups ────────────────────────────

def test_b02_dmr_group_validation_passes():
    """4 samples across 2 groups should not raise any error."""
    from agent_graph.nodes.prereq import _validate_samplesheet
    content = textwrap.dedent("""\
        group,sample,path,ref,method
        group1,sample1,/data/sample1.bam,/data/ref.fa,ont
        group1,sample2,/data/sample2.bam,/data/ref.fa,ont
        group2,sample3,/data/sample3.bam,/data/ref.fa,ont
        group2,sample4,/data/sample4.bam,/data/ref.fa,ont
    """)
    user_input = "run population-scale DMR analysis"
    issues = _validate_samplesheet(content, user_input)
    errors = [i for i in issues if i["level"] == "error"
              and "group" in i["message"].lower()]
    assert not errors, f"Unexpected DMR group errors: {errors}"


def test_b02_dmr_single_group_blocked():
    """All samples in one group must produce an error for population-scale DMR."""
    from agent_graph.nodes.prereq import _validate_samplesheet
    content = textwrap.dedent("""\
        group,sample,path,ref,method
        group1,sample1,/data/sample1.bam,/data/ref.fa,ont
        group1,sample2,/data/sample2.bam,/data/ref.fa,ont
    """)
    user_input = "run population-scale DMR analysis"
    issues = _validate_samplesheet(content, user_input)
    errors = [i for i in issues if i["level"] == "error"]
    assert any("group" in i["message"].lower() for i in errors), \
        "Single-group population DMR must produce a group error"


def test_b02_dmr_singleton_group_warns():
    """Groups with only 1 sample should warn (not error) for population-scale DMR."""
    from agent_graph.nodes.prereq import _validate_samplesheet
    content = textwrap.dedent("""\
        group,sample,path,ref,method
        group1,sample1,/data/sample1.bam,/data/ref.fa,ont
        group2,sample2,/data/sample2.bam,/data/ref.fa,ont
    """)
    user_input = "population-scale DMR analysis between groups"
    issues = _validate_samplesheet(content, user_input)
    warnings = [i for i in issues if i["level"] == "warning"]
    assert warnings, "Singleton groups should produce a warning"
    errors = [i for i in issues if i["level"] == "error"
              and "group" in i["message"].lower()]
    assert not errors, "Singleton groups should NOT produce an error"


# ── B03: haplotype-level DMR, single sample — no group error ──────────────────

def test_b03_haplotype_single_sample_no_error():
    """Haplotype-level DMR with a single sample must NOT trigger group errors."""
    from agent_graph.nodes.prereq import _validate_samplesheet
    content = textwrap.dedent("""\
        group,sample,path,ref,method
        group1,sample,/data/sample.bam,/data/ref.fa,ont
    """)
    user_input = "run methylong and use modkit dmr for haplotype-level DMR analysis, not DSS"
    issues = _validate_samplesheet(content, user_input)
    errors = [i for i in issues if i["level"] == "error"
              and "group" in i["message"].lower()]
    assert not errors, \
        f"Haplotype-level DMR should not require multiple groups, got: {errors}"


def test_b03_haplotype_chinese_no_error():
    """同: 中文描述单倍型分析，单样本不应报分组错误。"""
    from agent_graph.nodes.prereq import _validate_samplesheet
    content = textwrap.dedent("""\
        group,sample,path,ref,method
        group1,sample,/data/sample.bam,/data/ref.fa,ont
    """)
    user_input = "运行单倍型水平的甲基化分析"
    issues = _validate_samplesheet(content, user_input)
    errors = [i for i in issues if i["level"] == "error"
              and "group" in i["message"].lower()]
    assert not errors, \
        f"中文单倍型查询不应触发分组错误，got: {errors}"
