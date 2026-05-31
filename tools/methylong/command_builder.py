import os
import subprocess
import threading

from configs.path_config import PROJECT_ROOT
from configs.runtime_config import DEFAULT_WORKFLOW_ARGS, MAX_WORKFLOW_RESOURCES
from configs.app_config import APP_PASCAL
from tools.methylong.helper import _resolve_methylong_models


# 进程内缓存，避免重复 singularity exec 扫描
_DORADO_LIB_CACHE: dict[str, str] = {}
_cache_lock = threading.Lock()


def _join_data_dir(base_data_dir: str, p: str) -> str:
    if not p:
        return p
    return os.path.join(base_data_dir, os.path.basename(str(p)))


def _resolve_pipeline_path(pipeline: str) -> str:
    if "/" in pipeline or os.path.exists(pipeline):
        return pipeline
    if pipeline.lower() == "methylong":
        from configs import DATA_PATH
        configured = DATA_PATH.get("workflow", {}).get("pipeline_dir", "")
        if configured:
            base = os.path.abspath(os.path.expanduser(configured))
        else:
            base = os.path.join(PROJECT_ROOT, "agent_workflow")
        return os.path.join(base, pipeline)
    return f"nf-core/{pipeline}"


def _find_free_gpu(min_free_mb: int = 10000) -> str:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for i, line in enumerate(result.stdout.strip().split("\n")):
                try:
                    if int(line.strip()) >= min_free_mb:
                        return f"cuda:{i}"
                except ValueError:
                    continue
    except Exception:
        pass
    return "cuda:0"


def _find_dorado_lib_path_in_image(image_path: str) -> str:
    """在 Dorado SIF 镜像内找 libtorch 所在目录，结果缓存。找不到时返回已知兜底路径。"""
    with _cache_lock:
        if image_path in _DORADO_LIB_CACHE:
            return _DORADO_LIB_CACHE[image_path]

    fallback = "/opt/custflow/epi2meuser/dorado/lib"

    if not image_path or not os.path.isfile(image_path):
        with _cache_lock:
            _DORADO_LIB_CACHE[image_path] = fallback
        return fallback

    try:
        result = subprocess.run(
            ["singularity", "exec", image_path,
             "find", "/opt", "/usr", "-name", "libtorch.so",
             "-not", "-path", "*/session/*", "-not", "-path", "/tmp/*"],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line:
                lib_dir = os.path.dirname(line)
                print(f"[CmdBuilder] Found dorado lib dir: {lib_dir}")
                with _cache_lock:
                    _DORADO_LIB_CACHE[image_path] = lib_dir
                return lib_dir
    except Exception as e:
        print(f"[CmdBuilder] dorado lib detection failed: {e}, using fallback")

    with _cache_lock:
        _DORADO_LIB_CACHE[image_path] = fallback
    return fallback


def _bam_has_mod_tags(bam_path: str) -> bool:
    """Return True if the BAM already has MM/ML modification tags (i.e. is a modBAM)."""
    try:
        import pysam
        with pysam.AlignmentFile(bam_path, "rb", check_sq=False) as bam:
            for i, read in enumerate(bam.fetch(until_eof=True)):
                if read.has_tag("MM") or read.has_tag("Mm"):
                    return True
                if i >= 4:
                    break
        return False
    except Exception as e:
        print(f"[CmdBuilder] MM tag check failed: {e}")
        return False


def _samplesheet_pacbio_needs_modcall(input_file: str) -> bool:
    """Return True if any PacBio sample needs --pacbio_modcall.

    method='pacbio' → inspect BAM for MM/ML tags via pysam.
                      If BAM unreadable, falls back to assuming modcall needed.
    """
    if not input_file or not os.path.isfile(input_file):
        return False
    try:
        with open(input_file, encoding="utf-8") as f:
            header_line = f.readline().strip().lower()
            cols = [c.strip() for c in header_line.split(",")]
            if "method" not in cols:
                return False
            method_idx = cols.index("method")
            path_idx   = cols.index("path") if "path" in cols else -1

            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [c.strip() for c in line.split(",")]
                if method_idx >= len(parts):
                    continue
                method = parts[method_idx].lower()

                if method == "pacbio":
                    bam = parts[path_idx] if 0 <= path_idx < len(parts) else ""
                    if bam and os.path.isfile(bam):
                        if _bam_has_mod_tags(bam):
                            print(f"[CmdBuilder] {os.path.basename(bam)}: MM/ML tags found → modBAM, skip modcall")
                            continue
                        else:
                            print(f"[CmdBuilder] {os.path.basename(bam)}: no MM/ML tags → needs --pacbio_modcall")
                            return True
                    else:
                        print(f"[CmdBuilder] method='pacbio', BAM not found → needs --pacbio_modcall")
                        return True
        return False
    except Exception as e:
        print(f"[CmdBuilder] _samplesheet_pacbio_needs_modcall error: {e}")
        return False


def _samplesheet_needs_dorado(input_file: str) -> bool:
    """Return True if any sample provides raw POD5 input (needs Dorado basecalling).
    ONT modBAM files are already basecalled — Dorado is NOT needed for them.
    """
    if not input_file or not os.path.isfile(input_file):
        return False  # unknown → don't assume Dorado; user will get a pipeline error if needed
    try:
        import csv as _csv
        with open(input_file, encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                path = (row.get("path") or "").strip().lower()
                if path.endswith(".pod5"):
                    return True
        return False
    except Exception:
        return False


def _find_dorado_image(image_store: str) -> str:
    img_dir = os.path.join(os.path.expanduser(image_store), "workflow", "methylong")
    if not os.path.isdir(img_dir):
        return ""
    # 优先匹配固定部署文件名
    preferred = "docker.io-nanoporetech-dorado-shae423e761540b9d08b526a1eb32faf498f32e8f22.img"
    preferred_path = os.path.join(img_dir, preferred)
    if os.path.isfile(preferred_path):
        return preferred_path
    # 兜底：任何带 dorado 的镜像文件
    for f in os.listdir(img_dir):
        if f.endswith((".img", ".sif")) and "dorado" in f:
            return os.path.join(img_dir, f)
    return ""


def _write_resource_override_config(run_dir: str, max_cpus: int,
                                    max_memory: str, max_time: str,
                                    extra_binds: list[str] = None,
                                    dorado_image_path: str = "",
                                    singularity_cache_dir: str = "") -> str:
    if not run_dir:
        return ""

    os.makedirs(run_dir, exist_ok=True)
    cfg_path = os.path.join(run_dir, "override.config")

    gpu_device = _find_free_gpu(min_free_mb=10000)

    extra_bind_str = ""
    if extra_binds:
        parts = [f"--bind {p}:{p}" for p in extra_binds if p and os.path.exists(p)]
        if parts:
            extra_bind_str = " " + " ".join(parts)

    dorado_lib = _find_dorado_lib_path_in_image(dorado_image_path) if dorado_image_path else "/opt/custflow/epi2meuser/dorado/lib"
    nv_libs = [p for p in ["/usr/local/nvidia/lib64", "/usr/local/nvidia/lib"] if os.path.isdir(p)]
    ld_library_path = ":".join([dorado_lib] + nv_libs)

    nv_bind = "--bind /usr/local/nvidia:/usr/local/nvidia" if os.path.isdir("/usr/local/nvidia") else ""
    nv_bind_str = f" {nv_bind}" if nv_bind else ""

    cache_dir_line = f"\n    cacheDir = '{singularity_cache_dir}'" if singularity_cache_dir else ""

    content = f"""\
// Auto-generated by {APP_PASCAL}
singularity {{
    enabled = true{cache_dir_line}
    runOptions = "--nv{nv_bind_str}{extra_bind_str} --env LD_LIBRARY_PATH={ld_library_path}"
}}

process {{
    resourceLimits = [
        cpus:   {max_cpus},
        memory: '{max_memory}',
        time:   '{max_time}'
    ]
    withName: 'DORADO_BASECALLER' {{
        ext.use_gpu = true
        ext.args = '--device {gpu_device}'
    }}
    withName: 'DORADO_ALIGNER' {{
        beforeScript = 'outdir=$(grep -oP "(?<=--output-dir )\\\\S+" .command.sh 2>/dev/null | head -1); [ -n "$outdir" ] && mkdir -p "$outdir" || true'
        ext.args = {{ "--output-dir ${{meta.id}} && find ${{meta.id}} -mindepth 2 '(' -name '*.bam' -o -name '*.bai' ')' -exec mv {{}} ${{meta.id}}/ ';' 2>/dev/null || true" }}
    }}
}}
"""
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(content)
    return cfg_path


def build_methylong_command(kwargs: dict, data_path: dict) -> str:
    """Build the nextflow methylong run command."""
    base_data_dir = os.path.abspath(os.path.expanduser(data_path.get("base_data_dir", "~/agent_data")))
    out_dir = os.path.abspath(os.path.expanduser(data_path.get("out_dir", base_data_dir)))

    pipeline = kwargs.get("pipeline", "methylong")
    pipeline_path = _resolve_pipeline_path(pipeline)

    profile = DEFAULT_WORKFLOW_ARGS.get("profile", "singularity")

    input_raw = kwargs.get("input", "")
    if os.path.isabs(input_raw):
        input_file = os.path.abspath(input_raw)
    else:
        input_file = os.path.abspath(_join_data_dir(base_data_dir, input_raw))

    outdir_raw = kwargs.get("outdir", "results")
    if os.path.isabs(outdir_raw):
        outdir = os.path.abspath(outdir_raw)
    else:
        outdir = os.path.abspath(_join_data_dir(out_dir, outdir_raw))

    cmd_parts = [
        "nextflow run",
        pipeline_path,
        f"--input {input_file}",
        f"--outdir {outdir}",
        f"-profile {profile}",
    ]

    extra_binds = []
    dorado_image_path = ""

    needs_dorado         = _samplesheet_needs_dorado(input_file)
    needs_pacbio_modcall = _samplesheet_pacbio_needs_modcall(input_file)
    print(f"[CmdBuilder] needs dorado: {needs_dorado}  needs pacbio_modcall: {needs_pacbio_modcall}")

    from configs import DATA_PATH as _FULL_DATA_PATH
    simplex_model, mod_model = _resolve_methylong_models(_FULL_DATA_PATH)
    if needs_dorado:
        if simplex_model:
            cmd_parts.append(f"--dorado_model {simplex_model}")
            extra_binds.append(os.path.dirname(simplex_model))
            print(f"[CmdBuilder] dorado_model: {simplex_model}")
        else:
            print("[CmdBuilder] WARNING: dorado_model not found in model_dir")
        if mod_model:
            cmd_parts.append(f"--dorado_modification_model {mod_model}")
            print(f"[CmdBuilder] dorado_modification_model: {mod_model}")
        else:
            print("[CmdBuilder] WARNING: dorado_modification_model not found in model_dir")
    else:
        print("[CmdBuilder] PacBio-only samplesheet — skipping dorado model params")

    from configs import IMAGE_PATH as _IMAGE_PATH
    image_store = _IMAGE_PATH["image_store"]
    dorado_image_path = _find_dorado_image(image_store)
    singularity_cache_dir = os.path.join(os.path.expanduser(image_store), "workflow", "methylong")

    if kwargs.get("config"):
        cmd_parts.append(f"-c {os.path.abspath(kwargs['config'])}")

    # Optional params from LLM — boolean → flag, string/numeric → --param value
    # pacbio_modcall is auto-detected above; exclude from LLM-decided params
    _HANDLED = {"pipeline", "input", "outdir", "config",
                "dorado_model", "dorado_modification_model",
                "pacbio_modcall"}
    for key, value in kwargs.items():
        if key in _HANDLED:
            continue
        if value is True:
            cmd_parts.append(f"--{key}")
        elif value not in (False, None, ""):
            cmd_parts.append(f"--{key} {value}")

    if needs_pacbio_modcall:
        cmd_parts.append("--pacbio_modcall")

    max_cpus   = MAX_WORKFLOW_RESOURCES.get("max_cpus") or os.cpu_count() or 8
    max_memory = MAX_WORKFLOW_RESOURCES.get("max_memory", "30.GB")
    max_time   = MAX_WORKFLOW_RESOURCES.get("max_time",   "72.h")

    override_cfg = _write_resource_override_config(
        outdir, max_cpus, max_memory, max_time,
        extra_binds=extra_binds,
        dorado_image_path=dorado_image_path,
        singularity_cache_dir=singularity_cache_dir,
    )
    if override_cfg:
        cmd_parts.append(f"-c {override_cfg}")

    # data_path is already the workflow sub-dict when called from nodes_utils
    work_dir = os.path.abspath(os.path.expanduser(
        data_path.get("work_dir", os.path.join(base_data_dir, "nextflow_work"))
    ))
    from configs import DATA_PATH as _DP
    _global_nxf_home = _DP.get("workflow", {}).get("nfcore_home", os.path.join(base_data_dir, ".nextflow"))
    nxf_home = os.path.abspath(os.path.expanduser(_global_nxf_home))

    from configs.runtime_config import NEXTFLOW_OFFLINE
    offline_flag = "NXF_OFFLINE=true " if NEXTFLOW_OFFLINE else ""
    nextflow_cmd = " ".join(cmd_parts) + f" -work-dir {work_dir}"
    full_cmd = (
        f"export {offline_flag}NXF_HOME={nxf_home} "
        f"NXF_SINGULARITY_CACHEDIR={singularity_cache_dir} && "
        f"{nextflow_cmd}"
    )
    return full_cmd
