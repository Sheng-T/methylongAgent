# runtime/env_wrapper.py
import atexit
import os
import re
import shlex
import stat
import tempfile

from configs import IMAGE_PATH, DATA_PATH, TOOL_EXEC_ENV
from configs.path_config import USER_HOME
from configs.app_config import APP_SNAKE

_TEMP_SCRIPTS: list[str] = []


def _find_dorado_lib_path_in_image(image_path: str) -> str:
    """Find dorado CUDA lib path inside a singularity image (best-effort)."""
    if not image_path or not os.path.isfile(image_path):
        return ""
    try:
        result = os.popen(
            f"singularity exec {shlex.quote(image_path)} find /opt /usr -name 'libdorado*' 2>/dev/null | head -1"
        ).read().strip()
        if result:
            return os.path.dirname(result)
    except Exception:
        pass
    return ""


def cleanup_temp_scripts():
    """Remove all temp script files created by _wrap_with_exec_env."""
    for path in _TEMP_SCRIPTS:
        try:
            os.unlink(path)
        except OSError:
            pass
    _TEMP_SCRIPTS.clear()


atexit.register(cleanup_temp_scripts)


class EnvWrapper:
    def __init__(self):
        self.image_store = IMAGE_PATH['image_store']

    def _wrap_with_exec_env(self, raw_cmd: str, cwd: str = "") -> str:
        if not TOOL_EXEC_ENV:
            return raw_cmd

        exec_type = TOOL_EXEC_ENV.get("type", "")

        if exec_type == "conda":
            env_name = TOOL_EXEC_ENV.get("env_name", "")
            if not env_name:
                print("[Wrapper] TOOL_EXEC_ENV type=conda but env_name is empty — running in current env")
                return raw_cmd

            conda_base = os.popen("conda info --base").read().strip()
            script_dir = USER_HOME
            cd_line = f"cd {shlex.quote(cwd)}" if cwd else ""
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.sh', delete=False, prefix=f'{APP_SNAKE}_',
                dir=script_dir,
            )
            tmp.write(f"""#!/bin/bash
source {conda_base}/etc/profile.d/conda.sh
conda activate {env_name}
{cd_line}
{raw_cmd}
""")
            tmp.close()
            os.chmod(tmp.name, stat.S_IRWXU)
            _TEMP_SCRIPTS.append(tmp.name)
            print(f"[Wrapper] conda env '{env_name}', cwd='{cwd}', script={tmp.name}")
            return f"bash {tmp.name}"

        if exec_type == "script":
            script_path = TOOL_EXEC_ENV.get("script_path", "")
            if not script_path or not os.path.isfile(script_path):
                print(f"[Wrapper] TOOL_EXEC_ENV type=script but script_path '{script_path}' not found — running in current env")
                return raw_cmd
            escaped = raw_cmd.replace("'", "'\\''")
            wrapped = f"bash {shlex.quote(script_path)} '{escaped}'"
            print(f"[Wrapper] script wrapper → {wrapped}")
            return wrapped

        print(f"[Wrapper] Unknown TOOL_EXEC_ENV type '{exec_type}' — running in current env")
        return raw_cmd

    def wrap_command(self, tool_name: str, raw_cmd: str,
                     is_workflow: bool = False, cwd: str = "") -> str:
        if is_workflow:
            return self._wrap_workflow_command(raw_cmd, cwd=cwd)
        return self._wrap_tool_chain_command(tool_name, raw_cmd, cwd=cwd)

    def _resolve_image_path(self, tool_name: str) -> str | None:
        tool_dir = os.path.join(os.path.expanduser(self.image_store), tool_name)
        if not os.path.isdir(tool_dir):
            return None
        img_files = [f for f in os.listdir(tool_dir) if f.endswith((".img", ".sif"))]
        if not img_files:
            return None
        img_files.sort(key=lambda f: (0 if f.endswith(".img") else 1, f))
        return os.path.join(tool_dir, img_files[0])

    def _wrap_tool_chain_command(self, tool_name: str, raw_cmd: str, cwd: str = ""):
        image_path = self._resolve_image_path(tool_name)
        if not image_path:
            print(f'[Wrapper] No image found for {tool_name} — using configured exec env')
            return self._wrap_with_exec_env(raw_cmd, cwd=cwd)

        extra_lib = _find_dorado_lib_path_in_image(image_path) if tool_name == "dorado" else ""
        ld_parts = [p for p in [extra_lib, "/usr/local/nvidia/lib64", "/usr/local/nvidia/lib"] if p]
        ld_library_path = ":".join(ld_parts)

        bind_paths = set()
        for path in DATA_PATH.get(tool_name, {}).values():
            if not isinstance(path, str):
                continue
            abs_path = os.path.expanduser(path)
            if os.path.isdir(abs_path):
                bind_paths.add(abs_path)

        redirect_matches = re.findall(r'[>|]\s*(/[^\s>|]+)', raw_cmd)
        for path in redirect_matches:
            parent_dir = os.path.dirname(path)
            if parent_dir and os.path.isdir(parent_dir):
                bind_paths.add(parent_dir)

        output_matches = re.findall(r'(?:-o|--output)\s+(/[^\s-][^\s]*)', raw_cmd)
        for path in output_matches:
            parent_dir = os.path.dirname(path)
            if parent_dir and os.path.isdir(parent_dir):
                bind_paths.add(parent_dir)

        all_paths = re.findall(r'/home/[^\s>|]+', raw_cmd)
        for path in all_paths:
            check_path = path
            while check_path and check_path != '/':
                if os.path.isdir(check_path):
                    bind_paths.add(check_path)
                    break
                elif os.path.isfile(check_path):
                    parent_dir = os.path.dirname(check_path)
                    if parent_dir:
                        bind_paths.add(parent_dir)
                    break
                check_path = os.path.dirname(check_path)

        binds = ''
        for bind_path in sorted(bind_paths):
            binds += f"--bind {bind_path}:{bind_path} "

        wrapped = (
            f"singularity exec --nv "
            f"--bind /usr/local/nvidia:/usr/local/nvidia "
            + binds +
            f"{image_path} /bin/bash -c \""
            f"export LD_LIBRARY_PATH={ld_library_path}:\\$LD_LIBRARY_PATH && "
            f"{raw_cmd}\""
        )
        return wrapped

    def _wrap_workflow_command(self, raw_cmd: str, cwd: str = "") -> str:
        return self._wrap_with_exec_env(raw_cmd, cwd=cwd)
