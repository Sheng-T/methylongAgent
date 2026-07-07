#!/usr/bin/env bash
# deploy/04_setup_agent_env.sh 鈥?create methylong_agent conda env and install dependencies
# Runs in parallel with 03_pull_images.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"

[[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
resolve_paths

log_step "Step 4 鈥?Set up agent Python env (${AGENT_ENV})"

init_conda

if conda_env_exists "${AGENT_ENV}"; then
    log_info "Conda env '${AGENT_ENV}' already exists."
else
    log_info "Creating conda env '${AGENT_ENV}' with Python ${PYTHON_VERSION}..."
    conda create -y -n "${AGENT_ENV}" python="${PYTHON_VERSION}"
    log_success "Conda env '${AGENT_ENV}' created."
fi

conda_run "${AGENT_ENV}" pip install --upgrade pip -q

# Install torch with the correct CUDA wheel
_cuda="${CUDA_VERSION:-cu118}"
if conda_run "${AGENT_ENV}" python -c "import torch" &>/dev/null; then
    _torch_ver=$(conda_run "${AGENT_ENV}" python -c "import torch; print(torch.__version__)" 2>/dev/null)
    log_info "torch already installed (${_torch_ver}), skipping."
else
    log_info "Installing torch (${_cuda})..."
    case "${_cuda}" in
        cu118) _idx="https://download.pytorch.org/whl/cu118"; _pkg="torch==2.6.0+cu118 torchaudio==2.6.0+cu118" ;;
        cu121|cu12) _idx="https://download.pytorch.org/whl/cu121"; _pkg="torch==2.6.0+cu121 torchaudio==2.6.0+cu121" ;;
        cu124) _idx="https://download.pytorch.org/whl/cu124"; _pkg="torch==2.6.0+cu124 torchaudio==2.6.0+cu124" ;;
        cpu)   _idx="https://download.pytorch.org/whl/cpu";   _pkg="torch==2.6.0+cpu torchaudio==2.6.0+cpu" ;;
        *)     log_warn "Unknown CUDA_VERSION '${_cuda}', defaulting to cu118"
               _idx="https://download.pytorch.org/whl/cu118"; _pkg="torch==2.6.0+cu118 torchaudio==2.6.0+cu118" ;;
    esac
    conda_run "${AGENT_ENV}" pip install ${_pkg} --index-url "${_idx}" || die "torch install failed"
    log_success "torch installed."
fi

# Install project dependencies
REQ_FILE="${PROJECT_ROOT}/requirements.txt"
[[ -f "${REQ_FILE}" ]] || die "requirements.txt not found at ${REQ_FILE}"
log_info "Installing from ${REQ_FILE}..."
conda_run "${AGENT_ENV}" pip install -r "${REQ_FILE}" || die "pip install failed"
log_success "Python dependencies installed."

# Verify key packages
log_info "Verifying key packages..."
conda_run "${AGENT_ENV}" python -c "
import sys
checks = {
    'streamlit': 'streamlit', 'langgraph': 'langgraph',
    'langchain_core': 'langchain-core', 'langchain_openai': 'langchain-openai',
    'fpdf': 'fpdf2', 'yaml': 'pyyaml',
    'numpy': 'numpy', 'matplotlib': 'matplotlib',
    'torch': 'torch', 'transformers': 'transformers', 'bs4': 'beautifulsoup4',
}
failed = [pkg for mod, pkg in checks.items() if __import__('importlib').util.find_spec(mod) is None]
if failed:
    print(f'MISSING: {failed}', file=sys.stderr); sys.exit(1)
import torch
print(f'  torch {torch.__version__}  CUDA={torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
print('  All key packages OK')
"

log_done "Agent env setup complete"
