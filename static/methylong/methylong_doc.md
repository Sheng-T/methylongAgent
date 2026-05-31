# nf-core/methylong 2.0.0 Documentation

Extract methylation calls from long reads (ONT / PacBio).

---

## Introduction

**nf-core/methylong** is a bioinformatics pipeline for long-read methylation calling. It requires a genome reference and accepts:

- Modification-basecalled ONT reads (modBAM, unaligned)
- Raw ONT POD5 reads (triggers automatic Dorado basecalling)
- Raw ONT BAM reads
- PacBio HiFi reads (modBAM)

The pipeline auto-detects whether ONT input is POD5 or BAM and decides whether to run basecalling automatically.

### ONT workflow

1. **Modcalling** (optional — only for POD5 or raw BAM input)
   - Basecall POD5 reads to modBAM: `dorado basecaller sup --modified-bases 5mC_5hmC` (default)
2. **Preprocessing** (trim and repair MM/ML tags)
   - Sort modBAM → convert to FASTQ → trim adapters/barcodes (porechop) → re-import → repair MM/ML tags (modkit repair)
3. **Alignment** — `dorado aligner` (default) or `minimap2`; includes `samtools flagstat`
4. **Methylation pileup** — `modkit pileup`, minimum 5× base coverage
5. **Bedgraph conversion** (optional)

### PacBio workflow

1. **Modcalling** (optional — for unmodified BAM input, use `--pacbio_modcall`)
   - `jasmine` (default) or `ccsmeth`
2. **Alignment** — `pbmm2` (default) or `minimap2`; includes `samtools flagstat`
3. **Methylation pileup** — `pb-CpG-tools` (default) or `modkit pileup`; minimum 5× base coverage
4. **Bedgraph conversion** (optional)

### Downstream workflow

1. **SNV calling** — `clair3`
2. **Phasing** — `whatshap phase`
3. **DMR analysis**
   - Haplotype-level and population-scale
   - Tag reads by haplotype → create bedMethyl → DMR with `DSS` (default) or `modkit dmr`

### Fiber-seq workflow (`--fiberseq`)

- **ONT**: filter m6A calls (`modkit call-mods`) → infer nucleosomes/MSPs (`ft add-nucleosomes`) → extract (`ft extract`)
- **PacBio**: predict m6A and nucleosomes (`ft predict-m6a`) → extract (`ft extract`)

---

## Samplesheet Input

The samplesheet is a CSV file with 5 columns:

```
group,sample,path,ref,method
group1,sample1,/data/sample1.bam,/data/ref.fa,ont
group2,sample2,/data/sample2.bam,/data/ref.fa,pacbio
```

| Column | Description |
|--------|-------------|
| `group` | Sample group name. Multiple samples can share a group. |
| `sample` | Sample name. |
| `path` | Full absolute path to modBAM or POD5 file. Must end in `.bam` or `.pod5`. |
| `ref` | Full absolute path to reference genome FASTA (`.fa`, `.fasta`, `.fna`). |
| `method` | Sequencing platform: `ont` or `pacbio`. |

Notes:
- For ONT input, the pipeline auto-detects POD5 vs BAM from the file extension.
- If input modBAM was previously aligned, use `--reset` to strip alignment info before re-aligning.
- One group can contain multiple samples; sample names can repeat across methods (ONT + PacBio same sample).

---

## Running the Pipeline

```bash
nextflow run nf-core/methylong \
  --input samplesheet.csv \
  --outdir results \
  -profile singularity
```

Common examples:

```bash
# PacBio unmodified BAM (requires modcalling step)
nextflow run nf-core/methylong --input samplesheet.csv --outdir results -profile singularity --pacbio_modcall

# ONT Fiber-seq with 6mA calling
nextflow run nf-core/methylong --input samplesheet.csv --outdir results -profile singularity \
  --dorado_modification "5mCG_5hmCG 6mA" --fiberseq --m6a

# PacBio Fiber-seq
nextflow run nf-core/methylong --input samplesheet.csv --outdir results -profile singularity --fiberseq

# Population-scale DMR
nextflow run nf-core/methylong --input samplesheet.csv --outdir results -profile singularity \
  --dmr_population_scale --dmr_a group1 --dmr_b group2
```

Note: Do not use `-c` to pass pipeline parameters. Use `--param` flags or `-params-file`.

---

## Parameters

### Input / Output

| Parameter | Description |
|-----------|-------------|
| `--input` | Path to samplesheet CSV (required) |
| `--outdir` | Output directory (required) |

### Modcalling

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dorado_model` | `sup` | Dorado basecall model |
| `--dorado_modification` | `5mC_5hmC` | Dorado modification type. For ONT Fiber-seq 6mA: `5mCG_5hmCG 6mA` |
| `--pacbio_modcall` | false | Enable modcalling in PacBio workflow (for unmodified BAM input) |
| `--pacbio_modcaller` | `jasmine` | PacBio modcaller: `jasmine` (default) or `ccsmeth` |

### Preprocessing

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--reset` | false | Remove alignment info and reset flags before processing |
| `--no_trim` | false | Skip trimming step in ONT workflow |

### Alignment

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ont_aligner` | `dorado` | ONT aligner: `dorado` (default) or `minimap2` |
| `--pacbio_aligner` | `pbmm2` | PacBio aligner: `pbmm2` (default) or `minimap2` |

### Pileup

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--pileup_method` | `pbcpgtools` | PacBio pileup method: `pbcpgtools` (default) or `modkit` |
| `--pileup_count` | false | Use count mode in pb-CpG-tools instead of model mode |
| `--bedgraph` | false | Output bedgraph files |
| `--all_contexts` | false | Include all cytosine contexts in pileup |
| `--m6a` | false | Pileup m6A motif (ONT Fiber-seq only) |
| `--denovo` | false | Reference-free CpG identification (pb-CpG-tools) |

### Fiber-seq

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--fiberseq` | false | Enable Fiber-seq analysis (m6A calling + nucleosome/MSP annotation) |

### DMR

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--skip_snvs` | false | Skip SNV calling and haplotype phasing steps |
| `--dmr_population_scale` | false | Enable population-scale DMR analysis |
| `--dmr_a` | — | Group name A for population-scale DMR |
| `--dmr_b` | — | Group name B for population-scale DMR |
| `--haplotype_dmrer` | `dss` | DMR caller for haplotype-level: `dss` (default) or `modkit` |
| `--population_dmrer` | `dss` | DMR caller for population-scale: `dss` (default) or `modkit` |

---

## Output Files

### Output directory structure

```
results/
├── ont/<sample>/
│   ├── fastqc/                    # FastQC HTML + zip
│   ├── basecall/                  # *_calls.bam (if POD5 input)
│   ├── modcall/                   # *_modbam.bam (ONT modcall)
│   ├── trim/                      # *_fastq.gz, *.log
│   ├── repair/                    # *_repaired.bam, *.log
│   ├── alignment/                 # *.bam, *.bam.bai, *.flagstat
│   ├── pileup/modkit/             # *.bed.gz, *_pileup.log
│   ├── bedgraphs/                 # *.bedgraph
│   ├── fiberseq/                  # *_m6acall.bam, *_m6a.bed
│   ├── snvcall/                   # *.vcf.gz, *.vcf.gz.tbi, *_SNV_PASS.vcf
│   ├── phase/                     # *_phased.vcf, *_haplotagged.bam
│   ├── dmr_haplotype_level/dss/   # DSS DMR results
│   └── dmr_population_scale/      # population DMR results
│
├── pacbio/<sample>/
│   ├── fastqc/
│   ├── modcall/                   # *_modbam.bam or *_ccsmeth_modbam.bam
│   ├── alignment/                 # *.bam, *.bam.bai, *.flagstat
│   ├── pileup/                    # *.bed.gz, *_pileup.log, *.bw (pb-CpG-tools only)
│   ├── bedgraphs/
│   ├── fiberseq/                  # *_m6a_predicted.bam, *_m6a.bed
│   ├── snvcall/
│   ├── phase/
│   ├── dmr_haplotype_level/dss/
│   └── dmr_population_scale/
│
└── multiqc/
    ├── multiqc_report.html        # Standalone QC report (open in browser)
    ├── multiqc_data/              # Parsed statistics from all tools
    └── multiqc_plots/             # Static plot images
```

### Key output files

| File | Location | Description |
|------|----------|-------------|
| `*.bam` + `*.bam.bai` | `alignment/` | Aligned modBAM + index. Load into IGV for read-level visualization. |
| `*.flagstat` | `alignment/` | Alignment summary: total reads, mapped reads, mapping rate |
| `*.bed.gz` | `pileup/` | bedMethyl format: per-site methylation calls with modification probability |
| `*.bedgraph` | `bedgraphs/` | Context-specific methylation levels (CpG/CHG/CHH), min 5× coverage |
| `*.bw` | `pileup/` | BigWig methylation track (pb-CpG-tools only) |
| `multiqc_report.html` | `multiqc/` | Aggregated QC report for all samples |

### IGV visualization

To visualize methylation results in IGV:
1. Load `alignment/*.bam` (aligned modBAM) and its `.bam.bai` index
2. Load methylation tracks — choose one:
   - `pileup/*.bed.gz` (bedMethyl, requires `.tbi` index for large files)
   - `bedgraphs/*.bedgraph` (context-specific methylation levels)
   - `pileup/*.bw` (BigWig, PacBio pb-CpG-tools output only)
3. Optionally load `snvcall/*_SNV_PASS.vcf` for co-visualization of variants

No need to re-run the pipeline — all files are generated during standard execution.

### Alignment QC: flagstat metrics

The `*.flagstat` file (from `samtools flagstat`) contains:

```
1234567 + 0 in total (QC-passed reads + QC-failed reads)
0 + 0 secondary
0 + 0 supplementary
1200000 + 0 mapped (97.20% : N/A)
34567 + 0 unmapped
```

| Metric | Meaning |
|--------|---------|
| **in total** | Total number of reads in the BAM |
| **mapped** | Reads successfully aligned to the reference genome |
| **mapping rate** | mapped / total × 100%. Expected > 90% for good data aligned to correct reference |
| **unmapped** | Reads that failed to align |

A mapping rate below 80% may indicate: wrong reference genome, severely degraded sample, heavy contamination, or mismatched chemistry. The MultiQC report aggregates flagstat results across all samples for easy comparison.

---

## FAQ & Comparisons

### POD5 vs modBAM: which input should I use?

| | POD5 | modBAM |
|--|------|--------|
| **What it is** | Raw electrical signal from ONT sequencer, not yet basecalled | BAM already basecalled with Dorado + modification model; contains MM/ML tags |
| **Pipeline steps** | Dorado basecalling → modcalling → trim/repair → align → pileup | Skip basecalling; start from trim/repair → align → pileup |
| **Speed** | Slower (basecalling is GPU-intensive) | Faster (basecalling already done) |
| **Flexibility** | Can re-basecall with updated models | Fixed to the model used at basecalling time |
| **Use when** | You have raw sequencer output and want the pipeline to handle everything | You already ran Dorado externally with `--modified-bases` |

The pipeline auto-detects input type from the file extension (`.pod5` vs `.bam`). If providing a pre-aligned modBAM, add `--reset` to strip alignment info before re-aligning.

The key requirement for modBAM input: the BAM **must contain MM/ML tags** (modification probability tags written by Dorado). A BAM without these tags cannot be used for methylation analysis.

---

### jasmine vs ccsmeth for PacBio modcalling (`--pacbio_modcaller`)

Both tools call 5mCpG methylation from PacBio HiFi reads. Use `--pacbio_modcall` to enable modcalling in the pipeline.

| | jasmine (default) | ccsmeth |
|--|-------------------|---------|
| **Developer** | PacBio | Third-party (academic) |
| **Speed** | Faster | Slower |
| **Output** | MM/ML tags in BAM | MM/ML tags in BAM |
| **Model** | Built-in PacBio model | Configurable model (LSTM-based) |
| **Use when** | Standard PacBio HiFi methylation analysis | When you need a specific ccsmeth model or academic reproducibility |

For most users, **jasmine is recommended** as the default. Use ccsmeth only if you have a specific reason (e.g., comparing tools in a research context, or the sample chemistry requires a custom ccsmeth model).

---

### DSS vs modkit dmr for DMR analysis (`--haplotype_dmrer`, `--population_dmrer`)

Both tools identify differentially methylated regions (DMRs). The default is DSS for both haplotype-level and population-scale DMR.

| | DSS (default) | modkit dmr |
|--|--------------|------------|
| **Method** | Beta-binomial regression, statistical model | Direct comparison of methylation fractions |
| **Output** | DMLtest.txt (per-site statistics) + callDMR.txt | Differential methylation BED file |
| **Statistical test** | Wald test with smoothing | Difference in methylation rate |
| **Replicates** | Works best with biological replicates | Can work with single samples |
| **Use when** | Population-scale analysis with replicates; need p-values and statistical rigor | Quick comparison, single-sample haplotype DMR, or when DSS is too slow |

For **haplotype-level DMR** (comparing hap1 vs hap2 within one sample): either tool works; modkit is faster.
For **population-scale DMR** (comparing groups with replicates): DSS is preferred for statistical robustness.

---

### Docker vs Singularity: which profile to use on HPC?

**Use Singularity on HPC clusters.**

| | Docker | Singularity |
|--|--------|-------------|
| **Root required** | Yes (Docker daemon runs as root) | No (runs as regular user) |
| **HPC compatibility** | Usually not available on shared HPC | Standard on most HPC clusters |
| **Image format** | Docker image | `.sif` file (can be pre-pulled) |
| **Use when** | Local workstation or cloud VM where you have root/admin | HPC clusters (SLURM, PBS, LSF, etc.) |

On HPC, run with `-profile singularity`. If the cluster has no internet access, pre-pull the Singularity images to a local directory and set `NXF_SINGULARITY_CACHEDIR`.

Docker is suitable for local development and testing on a personal workstation or cloud instance where you have admin rights.

---

### Coverage cutoff for methylation analysis

The default minimum base coverage in methylong is **5×** for both ONT (modkit pileup) and PacBio (pb-CpG-tools) pileup steps. Sites with fewer than 5 reads are excluded from the output.

| Coverage | Recommendation |
|----------|---------------|
| < 5× | Below pipeline default; sites excluded from output |
| 5–10× | Minimum; high noise, use with caution |
| 10–20× | Acceptable for most analyses |
| ≥ 20× | Recommended for reliable DMR calling |
| ≥ 5× per haplotype | Required for haplotype-level DMR (each haplotype must meet 5×) |

For population-scale DMR with DSS, higher coverage (≥ 10×) per sample is strongly recommended to obtain reliable p-values. Low coverage leads to high variance in methylation estimates and inflated false positives.

The 5× cutoff is built into the pipeline and cannot be changed via pipeline parameters in the current version.
