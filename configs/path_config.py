import os

current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)

USER_HOME = os.environ.get("HOME") or os.path.expanduser("~")

# Methylong-specific data paths
DATA_PATH = {
    "dorado": {
        "base_data_dir": f"{USER_HOME}/agent_data",
        "dorado_models": f"{USER_HOME}/tools/dorado_model/",
        # Pod5 sampling rate: 4000 for R10.4.1 data, 5000 for newer; 0 = auto
        "sample_rate": 4000,
    },
    "workflow": {
        "base_data_dir": f"{USER_HOME}/agent_data",
        "work_dir":      f"{USER_HOME}/agent_data/nextflow_work",
        "nfcore_home":   f"{USER_HOME}/agent_data/.nextflow",
        # Directory containing local nextflow pipeline directories.
        "pipeline_dir":  f"{USER_HOME}/agent_workflow/",
    },
}

IMAGE_PATH = {
    "image_store": f"{USER_HOME}/singularity_image",
}

OTHER_PATH = {
    "db_dir":        os.path.join(PROJECT_ROOT, "static/vector_db_cache"),
    "graph_image":   os.path.join(PROJECT_ROOT, "static/methylongagent_graph.txt"),
    "checkpoint_db": os.path.join(PROJECT_ROOT, "static/checkpoints/agent.db"),
    "session_db":    os.path.join(PROJECT_ROOT, "static/sessions/sessions.db"),
    "user_data_root": os.path.join(PROJECT_ROOT, "static/user_data"),
}

# Methylong workflow doc and prereqs config
WORKFLOWS_DOC = os.path.join(PROJECT_ROOT, "static", "methylong", "methylong_doc.md")
WORKFLOWS_CACHE_DIR = os.path.join(PROJECT_ROOT, "static", "vector_db_cache", "methylong")

# Single user maximum storage quota (bytes), default 10 GB
USER_QUOTA_BYTES = 10 * 1024 * 1024 * 1024
