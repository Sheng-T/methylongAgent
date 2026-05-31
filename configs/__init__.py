"""
configs package entry point for methyl-agent.

Load order:
  1. Import sub-modules (triggers default value initialization)
  2. Read config.yaml from project root, apply user overrides
  3. Star-import to expose all names
"""
import os as _os

from . import model_config  as _mc
from . import path_config   as _pc
from . import runtime_config as _rc
from . import app_config    as _apc
from . import i18n_config   as _ic


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins on conflicts)."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _apply_user_config():
    base_dir = _os.path.dirname(__file__)
    cfg_path       = _os.path.join(base_dir, '..', 'config.yaml')
    cfg_local_path = _os.path.join(base_dir, '..', 'config.local.yaml')

    if not _os.path.exists(cfg_path) and not _os.path.exists(cfg_local_path):
        return

    try:
        import yaml as _yaml
    except ImportError:
        print("[Config] Warning: PyYAML not installed — config.yaml ignored. "
              "Run: pip install pyyaml")
        return

    cfg: dict = {}
    loaded: list[str] = []

    for path, label in ((cfg_path, 'config.yaml'), (cfg_local_path, 'config.local.yaml')):
        if not _os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as _f:
                data = _yaml.safe_load(_f) or {}
            cfg = _deep_merge(cfg, data)
            loaded.append(label)
        except Exception as e:
            print(f"[Config] Warning: failed to parse {label}: {e}")

    # ── llm ──────────────────────────────────────────────────────────────────
    llm = cfg.get('llm') or {}
    if 'model_name' in llm:
        # API key takes priority: if key is set, always use openai_compatible
        if not _mc._api_key:
            _mc.LLM_NAME = llm['model_name']
        else:
            _mc.LLM_NAME   = "openai_compatible"
            _mc.LLM_SOURCE = "api"
    if 'device' in llm:
        _rc.llm_args['device'] = llm['device']
    if isinstance(llm.get('model_paths'), dict):
        _mc.llm_model_path.update(llm['model_paths'])

    # ── tools.exec_env ────────────────────────────────────────────────────────
    tools = cfg.get('tools') or {}
    exec_env = tools.get('exec_env')
    if exec_env is not None:
        if isinstance(exec_env, dict) and exec_env.get('type'):
            _rc.TOOL_EXEC_ENV = exec_env
        else:
            _rc.TOOL_EXEC_ENV = None

    # ── data ─────────────────────────────────────────────────────────────────
    data = cfg.get('data') or {}
    if 'agent_data' in data:
        _agent_data = _os.path.abspath(_os.path.expanduser(str(data['agent_data'])))
        _wf_sec = _pc.DATA_PATH.get('workflow', {})
        if _wf_sec:
            _wf_sec['base_data_dir'] = _agent_data
            _wf_sec['work_dir']      = _os.path.join(_agent_data, 'nextflow_work')
            _wf_sec['nfcore_home']   = _os.path.join(_agent_data, '.nextflow')
    if 'dorado_models' in data:
        _pc.DATA_PATH['dorado']['dorado_models'] = _os.path.expanduser(
            str(data['dorado_models']))
    if 'dorado_sample_rate' in data:
        _pc.DATA_PATH['dorado']['sample_rate'] = int(data['dorado_sample_rate'])
    if 'singularity_image_dir' in data:
        _pc.IMAGE_PATH['image_store'] = _os.path.expanduser(
            str(data['singularity_image_dir']))
    if 'nfcore_home' in data:
        _pc.DATA_PATH['workflow']['nfcore_home'] = _os.path.abspath(
            _os.path.expanduser(str(data['nfcore_home'])))
    if 'nextflow_offline' in data:
        _rc.NEXTFLOW_OFFLINE = bool(data['nextflow_offline'])
    if 'pipeline_dir' in data:
        _pc.DATA_PATH['workflow']['pipeline_dir'] = _os.path.expanduser(
            str(data['pipeline_dir']))
    if 'user_quota_gb' in data:
        _pc.USER_QUOTA_BYTES = int(float(data['user_quota_gb']) * 1024 ** 3)

    # ── users ─────────────────────────────────────────────────────────────────
    auth_users = cfg.get('users')
    if isinstance(auth_users, dict):
        # store in runtime_config for auth
        _rc.DEFAULT_USERS = {str(k): str(v) for k, v in auth_users.items()}

    # ── workflow ──────────────────────────────────────────────────────────────
    wf = cfg.get('workflow') or {}
    if 'profile' in wf:
        _rc.DEFAULT_WORKFLOW_PROFILE = wf['profile']
    if 'max_memory' in wf:
        _rc.MAX_WORKFLOW_RESOURCES['max_memory'] = wf['max_memory']
    if 'max_time' in wf:
        _rc.MAX_WORKFLOW_RESOURCES['max_time'] = wf['max_time']
    if 'max_cpus' in wf:
        _rc.MAX_WORKFLOW_RESOURCES['max_cpus'] = wf['max_cpus']

    # ── server ────────────────────────────────────────────────────────────────
    server = cfg.get('server') or {}
    if 'file_server_port' in server:
        _rc.FILE_SERVER_PORT = int(server['file_server_port'])

    # ── language ──────────────────────────────────────────────────────────────
    if 'language' in cfg:
        _ic.DEFAULT_LANG = str(cfg['language'])

    if loaded:
        print(f"[Config] Loaded {' + '.join(loaded)}  (model={_mc.LLM_NAME}  lang={_ic.DEFAULT_LANG})")


_apply_user_config()

# ── star-import ────────────────────────────────────────────────────────────────
from .model_config   import *   # noqa: E402, F401, F403
from .path_config    import *   # noqa: E402, F401, F403
from .runtime_config import *   # noqa: E402, F401, F403
from .app_config     import *   # noqa: E402, F401, F403
from .i18n_config    import *   # noqa: E402, F401, F403
