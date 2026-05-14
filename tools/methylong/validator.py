import copy

from tools.methylong.command_builder import build_methylong_command


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
