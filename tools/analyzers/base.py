from abc import ABC, abstractmethod


class WorkflowAnalyzer(ABC):
    """
    Base class for per-workflow result analyzers.

    Each subclass handles one workflow (e.g. methylong).
    It receives the nextflow outdir and an analysis_dir where it may write
    additional plots, then returns a structured dict for the LLM report.
    """

    @abstractmethod
    def analyze(self, outdir: str, analysis_dir: str) -> dict:
        """
        Parameters
        ----------
        outdir       : absolute path to the nextflow --outdir (e.g. run_dir/results)
        analysis_dir : absolute path to {app_snake}_analysis/<workflow>/ inside run_dir
                       Created before this call; write all generated PNGs here.

        Returns
        -------
        {
            "workflow"   : str,
            "summary"    : dict,        # key metrics passed to the LLM
            "plot_paths" : [str, ...],  # absolute paths of generated PNG files
            "warnings"   : [str, ...],  # issues / recommendations
        }
        """
