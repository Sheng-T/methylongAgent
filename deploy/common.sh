#!/usr/bin/env bash
# deploy/common.sh — shared utilities, sourced by all sub-scripts

set -euo pipefail

_RED='\033[0;31m'; _GRN='\033[0;32m'; _YLW='\033[1;33m'
_BLU='\033[0;34m'; _CYN='\033[0;36m'; _RST='\033[0m'; _BLD='\033[1m'

log_info()    { echo -e "${_BLU}[INFO]${_RST}  $*"; }
log_success() { echo -e "${_GRN}[OK]${_RST}    $*"; }
log_warn()    { echo -e "${_YLW}[WARN]${_RST}  $*"; }
log_error()   { echo -e "${_RED}[ERROR]${_RST} $*" >&2; }
log_step()    { echo -e "\n${_BLD}${_CYN}══ $* ══${_RST}"; }
log_done()    { echo -e "${_GRN}${_BLD}✔ $*${_RST}"; }

die() { log_error "$*"; exit 1; }

init_conda() {
    if command -v conda &>/dev/null; then
        eval "$(conda shell.bash hook 2>/dev/null)" || true
        return 0
    fi
    for _p in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/mambaforge" "/opt/conda" "/usr/local/conda"; do
        if [[ -f "$_p/etc/profile.d/conda.sh" ]]; then
            source "$_p/etc/profile.d/conda.sh"
            return 0
        fi
    done
    die "Conda not found. Please install Miniconda or Anaconda first."
}

conda_run() {
    local env_name="$1"; shift
    init_conda
    conda run -n "$env_name" --no-capture-output "$@"
}

conda_env_exists() {
    init_conda
    conda env list 2>/dev/null | grep -qE "^${1}\s"
}

wait_job() {
    local pid="$1" name="$2"
    wait "$pid"
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        log_error "Step failed: $name (exit $rc)"
        return $rc
    fi
    log_done "$name"
}

show_paths() {
    echo -e "${_BLD}Deployment paths:${_RST}"
    echo "  BASE_DIR         = ${BASE_DIR}"
    echo "  SINGULARITY_DIR  = ${SINGULARITY_DIR}"
    echo "  DORADO_MODEL_DIR = ${DORADO_MODEL_DIR}"
    echo "  PIPELINE_DIR     = ${PIPELINE_DIR}"
    echo "  AGENT_DATA_DIR   = ${AGENT_DATA_DIR}"
    echo "  SIN_ENV          = ${SIN_ENV}"
    echo "  AGENT_ENV        = ${AGENT_ENV}"
}

resolve_paths() {
    BASE_DIR="${BASE_DIR:-$HOME}"
    BASE_DIR="$(realpath -m "${BASE_DIR/#\~/$HOME}")"

    SINGULARITY_DIR="${BASE_DIR}/singularity_image"
    METHYLONG_IMAGE_DIR="${SINGULARITY_DIR}/workflow/methylong"
    DORADO_MODEL_DIR="${BASE_DIR}/tools/dorado_model"
    PIPELINE_DIR="${BASE_DIR}/agent_workflow"
    AGENT_DATA_DIR="${BASE_DIR}/agent_data"

    export BASE_DIR SINGULARITY_DIR METHYLONG_IMAGE_DIR \
           DORADO_MODEL_DIR PIPELINE_DIR AGENT_DATA_DIR

    SIN_ENV="${SIN_ENV:-sin}"
    AGENT_ENV="${AGENT_ENV:-methylong_agent}"
    PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
    LLM_MODE="${LLM_MODE:-local}"
    DORADO_SAMPLE_RATE="${DORADO_SAMPLE_RATE:-5000}"
    SERVER_PORT="${SERVER_PORT:-50027}"
    USER_QUOTA_GB="${USER_QUOTA_GB:-10}"
    NF_MAX_MEMORY="${NF_MAX_MEMORY:-30.GB}"
    NF_MAX_TIME="${NF_MAX_TIME:-72.h}"

    export SIN_ENV AGENT_ENV PYTHON_VERSION LLM_MODE DORADO_SAMPLE_RATE \
           SERVER_PORT USER_QUOTA_GB NF_MAX_MEMORY NF_MAX_TIME
}
