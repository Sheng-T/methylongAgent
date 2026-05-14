"""
main.py — MethylongAgent entry point.

Launch the Streamlit UI:
    streamlit run ui/app_ui.py --server.address 0.0.0.0 --server.port 8501

Or run this script directly to launch via subprocess:
    python main.py
"""
import os
import subprocess
import sys


def main():
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    project_root = os.path.dirname(os.path.abspath(__file__))
    app_ui_path  = os.path.join(project_root, "ui", "app_ui.py")

    cmd = [
        sys.executable, "-m", "streamlit", "run", app_ui_path,
        "--server.address", "0.0.0.0",
        "--server.port",    "8501",
    ]

    print(f"[MethylongAgent] Starting Streamlit: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n[MethylongAgent] Stopped.")


if __name__ == "__main__":
    main()
