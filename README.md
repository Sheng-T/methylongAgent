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

All user-facing settings are in `config.yaml` at the project root. The deployment script patches this file automatically; you can also edit it manually and restart the app.

```yaml
llm:
  model_name: qwen3_14B          # model key, or "openai_compatible" for API mode
  device: cuda:0                 # LLM inference device
  embedding_device: cpu          # embedding model device
  model_paths:
    qwen3_14B: /path/to/qwen3-14b
    embedding:  /path/to/all-MiniLM-L6-v2
    reranker:   /path/to/bge-reranker-base

tools:
  exec_env:
    type: conda
    env_name: sin                # conda env with Nextflow + Singularity
  threads: 16                    # CPU threads for bio tools
  searxng_url: ""                # optional SearXNG URL for web search

data:
  agent_data: ~/agent_data       # upload root and run output directory
  dorado_models: ~/tools/dorado_model/
  dorado_sample_rate: 5000       # 4000 = v4.x models, 5000 = v5.x models
  singularity_image_dir: ~/singularity_image
  pipeline_dir: ~/agent_workflow/

workflow:
  profile: singularity
  max_memory: "30.GB"
  max_time: "72.h"
  max_cpus: null                 # null = auto-detect

server:
  port: 50027
  address: "0.0.0.0"
  max_upload_mb: 10240

users:
  admin: yourpassword

language: en_US                  # en_US | zh_CN
```

### Switching to an OpenAI-compatible API

```bash
cp configs/secrets.example.py configs/secrets.py
# Edit configs/secrets.py:
#   LLM_API_KEY      = "sk-..."
#   LLM_API_BASE_URL = "https://api.deepseek.com/v1"
#   LLM_API_MODEL    = "deepseek-chat"
```

Set `model_name: openai_compatible` in `config.yaml`.

| Provider | `LLM_API_BASE_URL` | `LLM_API_MODEL` |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `Qwen/Qwen3-235B-A22B` |
| Ollama (local) | `http://localhost:11434/v1` | `qwen3:14b` |

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
├── agent_graph/
│   ├── graph.py                  # LangGraph graph definition
│   ├── state.py                  # AgentState TypedDict
│   ├── prompts/                  # LLM prompt builders
│   └── nodes/
│       ├── router.py             # Intent classification + state reset
│       ├── prereq.py             # Samplesheet generation + human reviewer
│       ├── params.py             # Nextflow command parameter builder
│       ├── review.py             # Command preview node
│       ├── runner.py             # Pipeline executor
│       └── response.py          # Q&A, summarizer, irrelevant handlers
├── tools/
│   ├── methylong/
│   │   ├── command_builder.py    # Builds the nextflow run command
│   │   ├── helper.py             # Dorado model auto-discovery
│   │   └── validator.py
│   └── analyzers/
│       └── methylong.py          # Post-run result parser + chart generator
├── configs/
│   ├── __init__.py               # Loads config.yaml and applies overrides
│   ├── model_config.py           # LLM model registry
│   ├── path_config.py            # Data dirs, DB paths, quota
│   ├── runtime_config.py         # TOOL_EXEC_ENV, threads, searxng
│   ├── app_config.py             # APP_DISPLAY / APP_SNAKE / APP_PASCAL
│   ├── i18n_config.py            # DEFAULT_LANG, SUPPORTED_LANGS
│   └── secrets.example.py        # API key template (copy to secrets.py)
├── deploy/
│   ├── deploy.conf               # Deployment configuration
│   ├── common.sh                 # Shared utilities for deploy scripts
│   ├── 01_setup_dirs.sh          # Create directory structure
│   ├── 02_setup_sin_env.sh       # sin conda env (Nextflow + Singularity)
│   ├── 03_pull_images.sh         # Pull Singularity images
│   ├── 04_setup_agent_env.sh     # Agent Python env + dependencies
│   ├── 05_pull_dorado_models.sh  # Download Dorado basecall models
│   ├── 06_download_llm.sh        # Download LLM / Embedding / Reranker
│   ├── 07_final_check.sh         # Environment validation report
│   └── 08_patch_config.sh        # Patch config.yaml with deployed paths
├── ui/
│   ├── app_ui.py                 # Streamlit entry point
│   ├── chat.py                   # Chat area, review panels, download buttons
│   ├── sidebar.py                # Session mgmt, file upload, storage panel
│   └── login.py                  # Login page
├── storage/
│   ├── session_store.py          # SQLite: users, sessions, messages
│   ├── file_manager.py           # File upload, quota tracking, cleanup
│   └── checkpointer.py           # LangGraph SQLite checkpointer
├── runtime/
│   └── env_wrapper.py            # Tool execution environment wrapper
├── utils/
│   ├── llm_utils.py              # LLM instance factory + model cache
│   ├── pdf_exporter.py           # Markdown → PDF (fpdf2)
│   └── i18n.py                   # Translation helper _()
├── static/
│   └── modkit/modkit_doc.md      # Pipeline documentation for Q&A context
├── LLM/                          # Local model initializers (qwen3_*.py)
├── deploy.sh                     # One-click deployment entry point
├── start.sh                      # App launch script
├── config.yaml                   # All user-facing configuration
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
