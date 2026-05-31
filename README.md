<div align="center">

# 🧬 MethylongAgent

**Nanopore & PacBio Methylation Analysis Agent**

A focused AI agent built on LangGraph for end-to-end long-read DNA methylation analysis with the [nf-core/methylong](https://nf-co.re/methylong) pipeline — natural-language-driven, human-in-the-loop, zero command-line required.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1+-1C3C3C?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![nf-core](https://img.shields.io/badge/nf--core-methylong-41B883)](https://nf-co.re/methylong)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **Intent Routing** | Classifies input as pipeline execution or methylation Q&A |
| 📋 **Samplesheet Generation** | LLM builds a CSV samplesheet from uploaded files; user reviews before running |
| 👤 **Human-in-the-Loop** | Two review checkpoints: samplesheet confirmation and full command preview |
| 🔬 **methylong Pipeline** | Drives nf-core/methylong via Nextflow + Singularity — basecalling, alignment, methylation calling, phasing, DMR, FiberSeq |
| 📊 **Auto Analysis & Report** | Parses results, generates charts, and produces a Markdown report after execution |
| ⬇️ **One-click Export** | Download results as `.zip`, report as `.md` or `.pdf` from the chat |
| 💾 **Persistent Sessions** | Multi-user, multi-session isolation; SQLite checkpoints; files stored per user/session |
| 🌐 **Bilingual UI** | English / 中文 switching; language preference persisted per user |
| 🔌 **Flexible LLM Backend** | Local GPU model (Qwen3, etc.) or any OpenAI-compatible API — one config line to switch |

---

## 🔬 Pipeline: nf-core/methylong

| Item | Detail |
|---|---|
| **Input formats** | BAM (aligned/unaligned), pod5 |
| **Modifications** | 5mCpG, 5hmCpG |
| **Steps** | FastQC → Dorado basecalling → Adapter trimming → Alignment → Methylation pileup → Bed→Bedgraph → SNV calling → Phasing → DMR → FiberSeq → MultiQC |
| **Container** | Singularity / Apptainer |
| **Orchestration** | Nextflow 23+ |

Full pipeline documentation: https://nf-co.re/methylong

---

## 🚀 Deployment

A one-click deployment script is provided for server environments.

### Prerequisites

- Linux server with Conda installed
- NVIDIA GPU (recommended) with CUDA 11.8 / 12.x
- ~100 GB free disk space (images + models)

### Steps

**1. Run the deployment — the wizard starts automatically:**

```bash
bash deploy.sh
```

On first run (or when `BASE_DIR` is not yet set), an interactive setup wizard launches. It auto-detects CUDA version, GPU, and available memory, then prompts for the few values it cannot detect:

```
System detected:
  CUDA wheel : cu121
  GPU device : cuda:0
  Memory     : 200.GB (80% of RAM)
  CPUs       : 64

[1/5] Directories
  Base directory for all data files [/home/user/methylong]:

[2/5] LLM backend
  LLM mode (local|api) [local]:

[3/5] Local model settings
  CUDA version for PyTorch wheel (cu118|cu121|cu124|cpu) [cu121]:
  Inference device [cuda:0]:

[4/5] Nextflow resource limits
  Max memory for Nextflow [200.GB]:
  Max CPUs (Enter for auto-detect) []:

[5/5] Pipeline & server
  methylong pipeline git URL [https://github.com/nf-core/methylong]:
  Web server port [50027]:
```

Press Enter at any prompt to accept the shown value. The answers are written to `deploy/deploy.conf` and deployment continues immediately.

This runs 8 steps automatically (steps 3 & 4 in parallel):

| Step | What it does |
|---|---|
| 1 | Create directory structure under `BASE_DIR` |
| 2 | Create `sin` conda env with Nextflow + Singularity/Apptainer |
| 3 | Pull all Singularity images + clone methylong pipeline |
| 4 | Create `methylong_agent` conda env, install Python dependencies |
| 5 | Download Dorado basecall models via the Dorado SIF |
| 6 | Download LLM / Embedding / Reranker models from HuggingFace |
| 7 | Final environment checks and deployment report |
| 8 | Patch `config.yaml` with deployed paths |

**Other options:**

```bash
bash deploy.sh --reconfigure     # re-run the setup wizard
bash deploy.sh --skip-llm        # skip model download (step 6)
bash deploy.sh --step 3          # run only step 3
bash deploy.sh --from 5          # resume from step 5
bash deploy.sh --base /data      # set BASE_DIR directly, skip wizard
```

**2. Start the application:**

```bash
conda activate methylong_agent
streamlit run ui/app_ui.py --server.port 50027 --server.address 0.0.0.0
# or
bash start.sh
```

### Models downloaded

| Model | Purpose | Default location |
|---|---|---|
| Qwen/Qwen3-14B | LLM (local mode) | `{BASE_DIR}/models/qwen3-14b/` |
| sentence-transformers/all-MiniLM-L6-v2 | Embedding | `{BASE_DIR}/models/all-MiniLM-L6-v2/` |
| BAAI/bge-reranker-base | Reranker | `{BASE_DIR}/models/bge-reranker-base/` |
| dna_r10.4.1_e8.2_400bps_sup@v5.2.0 | Dorado simplex | `{BASE_DIR}/tools/dorado_model/` |
| dna_r10.4.1_e8.2_400bps_sup@v5.2.0_5mC_5hmC@v2 | Dorado mod | `{BASE_DIR}/tools/dorado_model/` |

HuggingFace downloads try the official endpoint first, then fall back to `hf-mirror.com` automatically.

---

## ⚙️ Configuration

All settings are in `config.yaml` (committed). The deployment script patches it automatically; edit manually and restart to apply changes.

For personal overrides, copy it to `config.local.yaml` (gitignored) — it is loaded after `config.yaml` and its values take priority:

```bash
cp config.yaml config.local.yaml
```

### Switching to an OpenAI-compatible API

Copy `api_keys.example.py` to `api_keys.py`, fill in `LLM_API_KEY`, `LLM_API_BASE_URL`, and `LLM_API_MODEL`, then set `model_name: openai_compatible` in your config. Supported providers: DeepSeek, OpenAI, SiliconFlow, Ollama.

---

## 🏗️ Architecture

MethylongAgent uses **LangGraph** as its core orchestration layer.

```
User Input
    │
    ▼
[router] ── intent classification
    │
    ├── Q&A ──▶ [llm_answer] ──▶ END
    │
    ├── off-topic ──▶ [irrelevant] ──▶ END
    │
    └── workflow ──▶ [prereq_generator]
                          │  generates CSV samplesheet from uploaded files
                          ▼
                 [human_prereq_reviewer] ⏸  ← interrupt_before
                     user reviews / edits samplesheet
                          │
                          ▼
                   [param_generator]
                     builds nextflow command
                          │
                          ▼
                   [human_reviewer] ⏸  ← interrupt_after
                  full command preview — Confirm / Modify / Cancel
                          │
                          ▼
                      [executor]
                     runs nextflow
                    ┌──────┴──────┐
                    ▼             ▼
               [summarizer]  [param_generator]
              report + zip    retry on error
                    │
                   END
```

### Interrupt Nodes

| Node | When | User action |
|---|---|---|
| `human_prereq_reviewer` | Samplesheet generated | Review / edit CSV, then Confirm or Cancel |
| `human_reviewer` | Command ready | Confirm execution, request modification, or Cancel |

### Key Design Choices

- **Router keyword safety** — Only unambiguous execution signals (`bam`, `pod5`, `samplesheet`) trigger the workflow path directly; everything else goes to the LLM classifier, preventing Q&A questions about methylong from accidentally starting a pipeline run.
- **`run_dir` lifecycle** — On success: zip→`session_dir`, plots→`session_dir`, `run_dir` deleted. On cancel/failure: `run_dir` preserved for user inspection via the sidebar cleanup panel.
- **Singularity image resolution** — At runtime, `NXF_SINGULARITY_CACHEDIR` is set to `{singularity_image_dir}/workflow/methylong/`, and `cacheDir` is written to the Nextflow override config, so pre-pulled images are found without internet access.

---

## 📁 Project Structure

```
methylongAgent/
├── agent_graph/          # LangGraph graph, state, prompts, nodes
├── tools/                # Pipeline command builder, validators, result analyzer
├── configs/              # Config loader (config.yaml / config.local.yaml) + sub-modules
├── deploy/               # Deployment scripts (01–08) + deploy.conf
├── ui/                   # Streamlit pages (app, chat, sidebar, login)
├── storage/              # SQLite session store, file manager, checkpointer
├── utils/                # LLM factory, RAG, PDF export, i18n, helpers
├── static/methylong/     # Pipeline docs (RAG) + args spec
├── LLM/                  # Local model initializers
├── runtime/              # Tool execution environment wrapper
├── config.yaml           # All user-facing configuration (committed)
├── config.local.yaml     # Personal overrides — gitignored, takes priority
└── requirements.txt
```

---

## 🖥️ Usage Guide

### 1. Upload Files

Upload BAM or pod5 files and reference genome FASTA via the **sidebar file panel** before starting a run.

### 2. Start Analysis

Type a natural-language instruction in the chat:

```
Run the methylong pipeline on my uploaded BAM file and reference genome.
```

### 3. Review Samplesheet

The agent generates a CSV samplesheet from uploaded files. Review the file paths, input type (`bam` / `pod5`), and method, edit if needed, then click **Confirm & Continue**.

### 4. Confirm Command

The full `nextflow run` command is displayed for review. Click **Confirm & Run** to execute, **Submit Revision** to let the agent adjust parameters, or **Cancel** to abort.

### 5. Download Results

After the run completes, the chat shows:
- A structured Markdown analysis report
- Charts (methylation distribution, top regions, site coverage)
- **Download buttons**: `.zip` (results), `.md` (report), `.pdf` (report)

Results are also accessible via the **sidebar file panel** for later download.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `langgraph` | Agent graph orchestration |
| `langgraph-checkpoint-sqlite` | Session checkpoint persistence |
| `langchain-openai` | OpenAI-compatible LLM client |
| `streamlit` | Web UI |
| `transformers`, `accelerate` | Local HuggingFace model loading |
| `numpy`, `matplotlib` | Result parsing and chart generation |
| `beautifulsoup4`, `html2text` | Web search result parsing |
| `fpdf2` | PDF report export |
| `pyyaml` | Config file parsing |

> `torch` is installed separately by the deployment script using a CUDA-specific wheel. See `deploy/04_setup_agent_env.sh`.
