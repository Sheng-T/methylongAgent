
llm_args = {
    "device": "cuda:0",
}

embedding_args = {
    "device": "cpu",
}

# Optional: execution environment for bioinformatics tools.
# Option A — conda environment:
#   TOOL_EXEC_ENV = {"type": "conda", "env_name": "biotools"}
# Option B — shell script prefix:
#   TOOL_EXEC_ENV = {"type": "script", "script_path": "/home/user/run_in_bioenv.sh"}
# Leave as None to run in the current Python process environment (default).
TOOL_EXEC_ENV = {"type": "conda", "env_name": "sin"}
# TOOL_EXEC_ENV = None

# Number of CPU threads for bioinformatics tools
TOOL_THREADS = 16

# SearXNG instance URL for Q&A web search.
SEARXNG_URL = ""

# Default users seeded at startup (overridden by config.yaml users section)
DEFAULT_USERS: dict = {"admin": "admin"}

# Default nextflow profile
DEFAULT_WORKFLOW_PROFILE = "singularity"

# Default workflow args
DEFAULT_WORKFLOW_ARGS = {
    "profile": DEFAULT_WORKFLOW_PROFILE,
    "extra_args": "",
}

# Resource limits for nextflow workflows
MAX_WORKFLOW_RESOURCES = {
    "max_cpus":   None,       # None = os.cpu_count()
    "max_memory": "30.GB",
    "max_time":   "72.h",
}
