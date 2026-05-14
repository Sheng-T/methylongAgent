# runtime/executor.py
import subprocess
import threading

from utils.ui_logger import ui_print


class ToolExecutor:
    @staticmethod
    def run(cmd: str):
        """Execute command, stream output in real-time to avoid blocking Streamlit."""
        ui_print(f"[ToolExecutor] running command: {cmd}")

        proc = subprocess.Popen(
            ['bash', '-c', cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stdout_lines = []
        stderr_lines = []

        def _read(pipe, buf):
            for line in pipe:
                line = line.rstrip("\n")
                buf.append(line)
                if line.startswith("[- "):
                    # Nextflow progress lines — only print to terminal, not UI
                    print(line)
                else:
                    ui_print(line)

        t_out = threading.Thread(target=_read, args=(proc.stdout, stdout_lines), daemon=True)
        t_err = threading.Thread(target=_read, args=(proc.stderr, stderr_lines), daemon=True)
        t_out.start()
        t_err.start()
        proc.wait()
        t_out.join()
        t_err.join()

        stdout = "\n".join(stdout_lines)
        stderr = "\n".join(stderr_lines)
        output = (stdout + "\n" + stderr).strip()

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "stdout": stdout,
            "stderr": stderr,
            "output": output,
            "exit_code": proc.returncode,
        }
