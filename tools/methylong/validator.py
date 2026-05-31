import copy
import json
import os

from tools.methylong.command_builder import build_methylong_command


_ARGS_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "static", "methylong", "methylong_args.json")

# Params controlled by the system — LLM must never set these
_SYSTEM_PARAMS = {"pipeline", "input", "outdir", "profile", "config",
                  "dorado_model", "dorado_modification_model"}

# Params with a fixed set of accepted string values
_ACCEPTED_VALUES: dict[str, set] = {
    "ont_aligner":       {"dorado", "minimap2"},
    "pacbio_aligner":    {"pbmm2",  "minimap2"},
    "pileup_method":     {"pbcpgtools", "modkit"},
    "haplotype_dmrer":   {"dss",    "modkit"},
    "population_dmrer":  {"dss",    "modkit"},
    "pacbio_modcaller":  {"jasmine", "ccsmeth"},
}

# Params that are boolean flags (no value, just presence)
_BOOLEAN_PARAMS = {
    "pacbio_modcall", "no_trim", "reset", "fiberseq",
    "skip_snvs", "dmr_population_scale", "pileup_count",
    "denovo", "bedgraph", "all_contexts", "m6a",
}


def _load_whitelist() -> set[str]:
    try:
        with open(_ARGS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("args", {}).get("kwargs", {}).keys())
    except Exception:
        return set()


def validate_optional_params(llm_params: dict) -> tuple[dict, list[str]]:
    """
    Validate LLM-generated optional params against the methylong args whitelist.

    Returns (valid_params, warnings) where valid_params is safe to pass to the
    command builder and warnings lists any params that were dropped or coerced.
    """
    whitelist = _load_whitelist()
    valid: dict = {}
    warnings: list[str] = []

    for key, value in llm_params.items():
        if key in _SYSTEM_PARAMS:
            warnings.append(f"Skipped system-controlled param: --{key}")
            continue

        if whitelist and key not in whitelist:
            warnings.append(f"Skipped unknown param: --{key}")
            continue

        if key in _BOOLEAN_PARAMS:
            # Accept truthy values; skip if explicitly false
            if value in (True, "true", "True", 1, "1", "yes"):
                valid[key] = True
            else:
                warnings.append(f"Boolean param --{key} set to false, skipping")
            continue

        if key in _ACCEPTED_VALUES:
            if str(value).lower() not in _ACCEPTED_VALUES[key]:
                allowed = ", ".join(sorted(_ACCEPTED_VALUES[key]))
                warnings.append(f"Invalid value '{value}' for --{key} (accepted: {allowed}), skipping")
                continue
            valid[key] = str(value).lower()
            continue

        # Generic string/numeric param — pass through
        if value is not None and str(value).strip():
            valid[key] = value

    return valid, warnings


def validate_methylong_kwargs(kwargs: dict) -> str | None:
    """Validate required parameters for methylong workflow."""
    pipeline = kwargs.get("pipeline", "")
    if not pipeline:
        return "Error: methylong pipeline requires kwargs['pipeline']."

    if pipeline.lower() != "methylong":
        return f"Error: unsupported pipeline '{pipeline}'. Only 'methylong' is supported."

    if not kwargs.get("input"):
        return "Error: methylong pipeline requires kwargs['input'] (samplesheet path)."

    if not kwargs.get("outdir"):
        return "Error: methylong pipeline requires kwargs['outdir']."

    return None


def methylong(args_dict, data_path):
    """
    Validate and build the methylong nextflow command.
    Called by the workflow runner with (tool_args, data_path).
    """
    args_dict = copy.deepcopy(args_dict)
    kwargs = args_dict.get("kwargs", {})

    err = validate_methylong_kwargs(kwargs)
    if err:
        return err

    return build_methylong_command(kwargs, data_path)
