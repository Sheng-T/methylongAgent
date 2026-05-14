"""
methylong workflow result analyzer.

Expected outdir layout (subset relevant to analysis):
  multiqc/
    multiqc_data/multiqc_data.json
    multiqc_plots/png/*.png
  ont/<sample>/
    alignment/flagstat/<sample>*.flagstat
    pileup/<sample>.bed.gz
    phase/<sample>.readlist
    snvcall/<sample>*.vcf

Analysis output is written under analysis_dir/:
  mapping/        <- per-sample mapping pie chart
  methylation/    <- methylation distribution + CpG coverage histogram
"""
import gzip
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from tools.analyzers.base import WorkflowAnalyzer

_C = {
    "mapped":   "#4C9BE8",
    "unmapped": "#E87B4C",
    "hyper":    "#E84C6B",
    "hypo":     "#4CE8A0",
    "mid":      "#F5A623",
    "bg":       "#F8F9FA",
    "grid":     "#E0E0E0",
    "text":     "#2C3E50",
}

plt.rcParams.update({
    "axes.facecolor":   _C["bg"],
    "figure.facecolor": "white",
    "axes.grid":        True,
    "grid.color":       _C["grid"],
    "grid.linewidth":   0.8,
    "font.size":        11,
})


def _savefig(fig, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _parse_flagstat(path: str) -> dict:
    stats: dict = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                parts = line.split(" + ")
                if len(parts) < 2:
                    continue
                count = int(parts[0])
                label = parts[1].split(None, 1)[-1].split("(")[0].strip()
                if "in total" in label:
                    stats["total"] = count
                elif "primary mapped" in label:
                    stats["primary_mapped"] = count
                elif label.startswith("mapped"):
                    stats.setdefault("mapped", count)
    except Exception:
        pass
    return stats


def _parse_bed_gz(path: str, max_lines: int = 200_000) -> dict:
    """Parse a bedMethyl file (modkit pileup output). Columns 9-10 are coverage & fraction."""
    total = covered = 0
    meth: list[float] = []
    cov:  list[int]   = []
    try:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                cols = line.strip().split("\t")
                if len(cols) < 10 or cols[0].startswith("#"):
                    continue
                try:
                    c = int(cols[9])
                    frac = float(cols[10]) if len(cols) > 10 else 0.0
                except (ValueError, IndexError):
                    continue
                total += 1
                cov.append(c)
                if c >= 5:
                    covered += 1
                    meth.append(frac)
    except Exception as e:
        return {"error": str(e)}

    if not meth:
        return {"total_sites": total, "covered_sites": covered}

    arr = np.array(meth)
    return {
        "total_sites":          total,
        "covered_sites":        covered,
        "coverage_rate_pct":    round(covered / total * 100, 2) if total else 0,
        "mean_methylation":     round(float(arr.mean()), 4),
        "median_methylation":   round(float(np.median(arr)), 4),
        "hypermethylated_pct":  round(float((arr >= 0.8).mean() * 100), 2),
        "hypomethylated_pct":   round(float((arr <= 0.2).mean() * 100), 2),
        "_meth_sample":         arr[:5000].tolist(),
        "_cov_sample":          cov[:5000],
    }


def _find_multiqc_data_json(outdir: str) -> str:
    """Search for multiqc_data.json under outdir."""
    for root, dirs, files in os.walk(outdir):
        if "multiqc_data.json" in files:
            return os.path.join(root, "multiqc_data.json")
    return ""


def _find_multiqc_pngs(outdir: str) -> list[str]:
    """Find all PNG files under the multiqc plots directory."""
    paths = []
    for root, dirs, files in os.walk(outdir):
        if "multiqc_plots" in root or "multiqc" in root.lower():
            for f in files:
                if f.endswith(".png"):
                    paths.append(os.path.join(root, f))
    return paths


def _parse_multiqc_json(json_path: str) -> dict:
    """Extract key summary metrics from multiqc_data.json."""
    try:
        with open(json_path) as f:
            data = json.load(f)
        # Return a trimmed version to avoid overloading the LLM
        return {
            "report_general_stats": data.get("report_general_stats_data", {}),
        }
    except Exception as e:
        return {"error": str(e)}


def _plot_mapping(fs: dict, sample: str, out_dir: str) -> str:
    total    = fs.get("total", 0)
    mapped   = fs.get("primary_mapped", fs.get("mapped", 0))
    unmapped = max(0, total - mapped)
    if total == 0:
        return ""
    pairs = [(mapped, f"Mapped ({mapped:,})", _C["mapped"]),
             (unmapped, f"Unmapped ({unmapped:,})", _C["unmapped"])]
    pairs = [(v, l, c) for v, l, c in pairs if v > 0]
    if not pairs:
        return ""
    vs, ls, cs = zip(*pairs)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(vs, colors=cs, autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
           startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.legend(ls, loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=9)
    ax.set_title(f"Mapping — {sample}\n(total {total:,})", color=_C["text"])
    return _savefig(fig, os.path.join(out_dir, f"{sample}_mapping.png"))


def _plot_methylation(bed: dict, sample: str, out_dir: str) -> list[str]:
    paths: list[str] = []
    meth_vals = bed.get("_meth_sample", [])
    if not meth_vals:
        return paths
    arr = np.array(meth_vals)

    fig, ax = plt.subplots(figsize=(7, 4))
    n, bins, patches = ax.hist(arr, bins=50, edgecolor="white", linewidth=0.3)
    for patch, left in zip(patches, bins[:-1]):
        patch.set_facecolor(_C["hyper"] if left >= 0.8 else
                            _C["hypo"]  if left <= 0.2 else _C["mid"])
    legend_patches = [
        mpatches.Patch(color=_C["hyper"], label=">=80% (hyper)"),
        mpatches.Patch(color=_C["mid"],   label="20-80% (intermediate)"),
        mpatches.Patch(color=_C["hypo"],  label="<=20% (hypo)"),
    ]
    ax.legend(handles=legend_patches, fontsize=8)
    ax.axvline(float(arr.mean()), color=_C["text"], linestyle="--", linewidth=1.5)
    ax.set_xlabel("Methylation Fraction")
    ax.set_ylabel("CpG Site Count")
    ax.set_title(f"Methylation Distribution — {sample}")
    fig.tight_layout()
    paths.append(_savefig(fig, os.path.join(out_dir, f"{sample}_methylation_dist.png")))

    cov_vals = bed.get("_cov_sample", [])
    if cov_vals:
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        ax2.hist(cov_vals, bins=50, color=_C["mapped"], edgecolor="white",
                 linewidth=0.3, alpha=0.85)
        ax2.axvline(5, color=_C["unmapped"], linestyle="--",
                    linewidth=1.5, label="Min depth = 5x")
        ax2.set_xlabel("Read Depth per CpG Site")
        ax2.set_ylabel("Site Count")
        ax2.set_title(f"CpG Site Coverage — {sample}")
        ax2.legend(fontsize=9)
        fig2.tight_layout()
        paths.append(_savefig(fig2, os.path.join(out_dir, f"{sample}_cpg_coverage.png")))

    return paths


class MethylongAnalyzer(WorkflowAnalyzer):

    def analyze(self, outdir: str, analysis_dir: str) -> dict:
        plot_paths: list[str] = []
        warnings:   list[str] = []
        summary:    dict      = {}

        mq_json = _find_multiqc_data_json(outdir)
        if mq_json:
            summary["multiqc"] = _parse_multiqc_json(mq_json)
        else:
            warnings.append("multiqc_data.json not found — MultiQC may not have completed")
        plot_paths.extend(_find_multiqc_pngs(outdir))

        per_sample: dict = {}

        for platform in os.listdir(outdir):
            platform_path = os.path.join(outdir, platform)
            if not os.path.isdir(platform_path) or platform in ("multiqc", "pipeline_info"):
                continue
            for sample in os.listdir(platform_path):
                sample_path = os.path.join(platform_path, sample)
                if not os.path.isdir(sample_path):
                    continue
                s: dict = {}

                flagstat_dir = os.path.join(sample_path, "alignment", "flagstat")
                if os.path.isdir(flagstat_dir):
                    for fname in os.listdir(flagstat_dir):
                        if fname.endswith(".flagstat"):
                            fs = _parse_flagstat(os.path.join(flagstat_dir, fname))
                            if fs:
                                s["flagstat"] = fs
                                p = _plot_mapping(
                                    fs, sample,
                                    os.path.join(analysis_dir, "mapping"),
                                )
                                if p:
                                    plot_paths.append(p)

                pileup_dir = os.path.join(sample_path, "pileup")
                if os.path.isdir(pileup_dir):
                    for fname in os.listdir(pileup_dir):
                        if fname.endswith(".bed.gz") or fname.endswith(".bed"):
                            bed = _parse_bed_gz(os.path.join(pileup_dir, fname))
                            if "error" not in bed:
                                s["methylation"] = {k: v for k, v in bed.items()
                                                    if not k.startswith("_")}
                                ps = _plot_methylation(
                                    bed, sample,
                                    os.path.join(analysis_dir, "methylation"),
                                )
                                plot_paths.extend(ps)
                                if bed.get("coverage_rate_pct", 100) < 50:
                                    warnings.append(
                                        f"{sample}: CpG coverage rate only "
                                        f"{bed['coverage_rate_pct']:.1f}% — "
                                        "consider deeper sequencing"
                                    )
                                if (m := bed.get("mean_methylation")) is not None and m < 0.05:
                                    warnings.append(
                                        f"{sample}: very low mean methylation ({m:.3f}) — "
                                        "verify reference genome matches the sample"
                                    )
                            else:
                                warnings.append(f"{sample}: pileup parse error — {bed['error']}")

                phase_dir = os.path.join(sample_path, "phase")
                if os.path.isdir(phase_dir):
                    readlists = [f for f in os.listdir(phase_dir) if f.endswith(".readlist")]
                    if readlists:
                        s["phasing"] = {"readlist_files": len(readlists)}

                if s:
                    per_sample[sample] = s

        summary["per_sample"] = per_sample
        return {
            "workflow":   "methylong",
            "summary":    summary,
            "plot_paths": plot_paths,
            "warnings":   warnings,
        }


# Singleton instance for use by the graph
_analyzer_instance: MethylongAnalyzer | None = None


def get_methylong_analyzer() -> MethylongAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MethylongAnalyzer()
    return _analyzer_instance
