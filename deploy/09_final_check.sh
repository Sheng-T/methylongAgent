#!/usr/bin/env bash
# deploy/09_final_check.sh - final environment checks and deployment report

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"

[[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
resolve_paths

log_step "Step 9 - Final checks"

_PASS=(); _WARN=(); _FAIL=()
_ok()   { _PASS+=("$*"); echo -e "  ${_GRN}OK${_RST}  $*"; }
_warn() { _WARN+=("$*"); echo -e "  ${_YLW}!!${_RST}  $*"; }
_fail() { _FAIL+=("$*"); echo -e "  ${_RED}XX${_RST}  $*"; }

init_conda

_hf_model_complete() {
    local local_dir="$1"
    [[ -f "${local_dir}/config.json" ]] || return 1
    ls "${local_dir}"/pytorch_model.bin \
       "${local_dir}"/model.safetensors \
       "${local_dir}"/*.safetensors 2>/dev/null | head -1 | grep -q .
}

echo -e "\n${_BLD}GPU / NVIDIA:${_RST}"
if command -v nvidia-smi &>/dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "")
    if [[ -n "${GPU_INFO}" ]]; then
        _ok "nvidia-smi OK"
        while IFS=',' read -r name total free; do
            echo "     GPU: ${name// /}  Total: ${total// /}  Free: ${free// /}"
        done <<< "${GPU_INFO}"
    else
        _warn "nvidia-smi present but returned no GPU info"
    fi
else
    _warn "nvidia-smi not found - GPU unavailable"
fi

echo -e "\n${_BLD}Port ${SERVER_PORT}:${_RST}"
_in_use=""
command -v ss      &>/dev/null && _in_use=$(ss -tulpn 2>/dev/null | grep ":${SERVER_PORT}\b" || true)
command -v netstat &>/dev/null && [[ -z "${_in_use}" ]] && \
    _in_use=$(netstat -tulpn 2>/dev/null | grep ":${SERVER_PORT}\b" || true)
if [[ -n "${_in_use}" ]]; then
    _warn "Port ${SERVER_PORT} is already in use"
    echo "     ${_in_use}"
else
    _ok "Port ${SERVER_PORT} is available"
fi

echo -e "\n${_BLD}Conda environments:${_RST}"
if conda_env_exists "${SIN_ENV}"; then
    NF_VER=$(conda_run "${SIN_ENV}" bash -c 'nextflow -version' 2>/dev/null | grep -oP '[\d.]+' | head -1 || echo "?")
    _ok "sin env '${SIN_ENV}' (Nextflow ${NF_VER})"
else
    _fail "sin env '${SIN_ENV}' not found"
fi
if conda_env_exists "${AGENT_ENV}"; then
    PY_VER=$(conda_run "${AGENT_ENV}" python --version 2>&1 | grep -oP '[\d.]+' | head -1 || echo "?")
    _ok "agent env '${AGENT_ENV}' (Python ${PY_VER})"
else
    _fail "agent env '${AGENT_ENV}' not found"
fi

echo -e "\n${_BLD}Directories:${_RST}"
for _d in "${METHYLONG_IMAGE_DIR}" "${DORADO_MODEL_DIR}"; do
    [[ -d "$_d" ]] && _ok "exists: $_d" || _fail "missing: $_d"
done

echo -e "\n${_BLD}Singularity images (${METHYLONG_IMAGE_DIR}):${_RST}"
_img_count=$(find "${METHYLONG_IMAGE_DIR}" -maxdepth 1 -name "*.img" 2>/dev/null | wc -l || echo 0)
if [[ "${_img_count}" -ge 15 ]]; then
    _ok "${_img_count} images found"
elif [[ "${_img_count}" -gt 0 ]]; then
    _warn "Only ${_img_count}/15 images found - run 03_pull_images.sh"
else
    _fail "No images found - run 03_pull_images.sh"
fi

echo -e "\n${_BLD}Pipeline:${_RST}"
_pipeline_dir="${PIPELINE_DIR}/methylong"
if [[ -d "${_pipeline_dir}/.git" ]]; then
    _ok "methylong pipeline: ${_pipeline_dir}"
elif [[ -d "${_pipeline_dir}" ]]; then
    _warn "methylong dir exists but is not a git repo - may be manually placed"
else
    _fail "methylong pipeline not found at ${_pipeline_dir}"
fi
if [[ -d "${_pipeline_dir}" ]]; then
    [[ -f "${_pipeline_dir}/nextflow.config" ]] && _ok "pipeline nextflow.config present" \
                                                   || _fail "pipeline nextflow.config missing"
    [[ -f "${_pipeline_dir}/modules/local/dorado/basecaller/main.nf" ]] && _ok "patched dorado basecaller present" \
                                                                            || _fail "patched dorado basecaller file missing"
fi

echo -e "\n${_BLD}Dorado models (${DORADO_MODEL_DIR}):${_RST}"
_simplex="${DORADO_MODEL_DIR}/dna_r10.4.1_e8.2_400bps_sup@v5.2.0"
_mod="${DORADO_MODEL_DIR}/dna_r10.4.1_e8.2_400bps_sup@v5.2.0_5mC_5hmC@v2"
[[ -d "${_simplex}" ]] && _ok "simplex model: dna_r10.4.1_e8.2_400bps_sup@v5.2.0" \
                       || _warn "simplex model not found - run 05_pull_dorado_models.sh"
[[ -d "${_mod}" ]] && _ok "mod model: dna_r10.4.1_e8.2_400bps_sup@v5.2.0_5mC_5hmC@v2" \
                   || _warn "mod model not found - run 05_pull_dorado_models.sh"

echo -e "\n${_BLD}Models (LLM_MODE=${LLM_MODE:-local}):${_RST}"
LLM_MODEL_DIR="${LLM_MODEL_DIR:-${BASE_DIR}/models/qwen3-14b}"
EMBEDDING_MODEL_DIR="${EMBEDDING_MODEL_DIR:-${BASE_DIR}/models/all-MiniLM-L6-v2}"
RERANKER_MODEL_DIR="${RERANKER_MODEL_DIR:-${BASE_DIR}/models/bge-reranker-base}"

if [[ "${LLM_MODE:-local}" == "local" ]]; then
    _hf_model_complete "${LLM_MODEL_DIR}" && _ok "LLM: ${LLM_MODEL_DIR}" \
                                            || _warn "LLM model incomplete or not found at ${LLM_MODEL_DIR}"
else
    [[ -f "${PROJECT_ROOT}/api_keys.py" ]] \
        && _ok "API mode: api_keys.py found" || _warn "API mode: api_keys.py missing"
fi
_hf_model_complete "${EMBEDDING_MODEL_DIR}" && _ok "Embedding: ${EMBEDDING_MODEL_DIR}" \
                                           || _warn "Embedding model incomplete or not found"
_hf_model_complete "${RERANKER_MODEL_DIR}"  && _ok "Reranker: ${RERANKER_MODEL_DIR}" \
                                           || _warn "Reranker model incomplete or not found"

echo ""
echo -e "${_BLD}====================${_RST}"
echo -e "${_GRN}${_BLD}  Passed  : ${#_PASS[@]}${_RST}"
[[ ${#_WARN[@]} -gt 0 ]] && echo -e "${_YLW}${_BLD}  Warnings: ${#_WARN[@]}${_RST}"
[[ ${#_FAIL[@]} -gt 0 ]] && echo -e "${_RED}${_BLD}  Failed  : ${#_FAIL[@]}${_RST}"
echo -e "${_BLD}====================${_RST}"

if [[ ${#_FAIL[@]} -eq 0 ]]; then
    echo -e "\n${_GRN}${_BLD}Deployment complete!${_RST}"
    echo ""
    echo -e "${_BLD}Start command:${_RST}"
    echo "  conda activate ${AGENT_ENV}"
    echo "  streamlit run ui/app_ui.py --server.port ${SERVER_PORT} --server.address 0.0.0.0"
    exit 0
else
    echo -e "\n${_RED}${_BLD}Deployment incomplete - ${#_FAIL[@]} check(s) failed.${_RST}"
    exit 1
fi