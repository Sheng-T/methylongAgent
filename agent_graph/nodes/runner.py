"""
Executor node: runs the methylong Nextflow pipeline command.
"""
import shutil

from agent_graph.state import AgentState
from runtime.env_wrapper import EnvWrapper, cleanup_temp_scripts
from runtime.executor import ToolExecutor
from utils.nodes_utils import build_command_for_call

from utils.lang_utils import get_lang
from utils.ui_logger import ui_print


def _format_error(resp: dict, tail: int = 3000) -> str:
    """Format stderr + stdout for error display, prioritizing the tail."""
    stdout = (resp.get("stdout") or "").strip()
    stderr = (resp.get("stderr") or "").strip()
    parts = []
    if stderr:
        parts.append("--- stderr ---\n" + (stderr[-tail:] if len(stderr) > tail else stderr))
    if stdout:
        parts.append("--- stdout ---\n" + (stdout[-tail:] if len(stdout) > tail else stdout))
    return "\n".join(parts) if parts else "(no output)"


def execute_commands_node(state: AgentState) -> dict:
    wrapper  = EnvWrapper()
    executor = ToolExecutor()
    lang     = get_lang()

    tool_calls       = state.get("tool_calls", [])
    history          = state.get("chat_history", [])
    pending_commands = state.get("pending_commands", [])
    next_node        = "summarizer"
    tool_output      = []

    run_dir = state.get("run_dir") or ""

    def _msg(en: str, zh: str) -> str:
        return en if lang == "en_US" else zh

    # methylong is always nfcore workflow
    for raw_cmd in pending_commands:
        if "error" in raw_cmd.lower():
            history.append({"role": "assistant", "content": _msg(
                f"Pre-validation intercepted an error: {raw_cmd}",
                f"系统拦截预校验失败: {raw_cmd}",
            )})
            next_node = "param_generator"
            break

        ui_print(f"\n[Executor] Running methylong: {raw_cmd[:120]}...")
        final_cmd = wrapper.wrap_command("workflow", raw_cmd, is_workflow=True, cwd=run_dir)
        resp = executor.run(final_cmd)

        if resp["status"] == "success":
            output = resp.get("output", "")
            tool_output.append(output)
            history.append({"role": "assistant", "content": _msg(
                f"methylong pipeline completed.\nOutput: {output[-200:]}",
                f"methylong 流水线执行成功\n输出: {output[-200:]}",
            )})
        else:
            next_node = "param_generator"
            error_log = _format_error(resp)
            ui_print(f"\n[Executor] Failed:\n{error_log}")
            history.append({"role": "assistant", "content": _msg(
                f"methylong execution failed:\n{error_log}\nI will correct the parameters.",
                f"methylong 执行失败，报错如下：\n{error_log}\n我需要根据这个错误修正参数。",
            )})
            break

    cleanup_temp_scripts()
    return {
        "chat_history": history,
        "next_node":    next_node,
        "tool_output":  tool_output,
        "run_dir":      run_dir,
    }
