#!/usr/bin/env bash
# =============================================================================
#  MethylongAgent one-click deployment script
#
#  Usage:
#    bash deploy.sh                  # use config from deploy/deploy.conf
#    bash deploy.sh --base /data     # override BASE_DIR
#    bash deploy.sh --skip-llm       # skip LLM model download
#    bash deploy.sh --step 3         # run a single step (1-8)
#    bash deploy.sh --from 4         # run from step N onward
#    bash deploy.sh --help           # show help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/deploy"

source "${DEPLOY_DIR}/common.sh"

_SKIP_LLM=false
_ONLY_STEP=""
_FROM_STEP=1
_OVERRIDE_BASE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base)    _OVERRIDE_BASE="$2"; shift 2 ;;
        --skip-llm) _SKIP_LLM=true; shift ;;
        --step)    _ONLY_STEP="$2"; shift 2 ;;
        --from)    _FROM_STEP="$2"; shift 2 ;;
        --help|-h)
            cat <<EOF
MethylongAgent deployment script

Usage:
  bash deploy.sh [options]

Options:
  --base  <dir>    Override BASE_DIR (default: \$HOME)
  --skip-llm       Skip LLM/model download (step 6)
  --step  <n>      Run only step n (1-8)
  --from  <n>      Run from step n onward (1-8)
  --help           Show this help

Steps:
  1  Create directory structure
  2  Create sin conda env (Nextflow + Singularity)
  3  Pull Singularity images & clone pipeline  ─╮ parallel
  4  Create agent Python env                   ─╯
  5  Download Dorado basecall models
  6  Download LLM / Embedding / Reranker models
  7  Final environment checks
  8  Patch config.yaml

Config file: deploy/deploy.conf (copy and edit before running)
EOF
            exit 0
            ;;
        *) log_warn "Unknown argument: $1"; shift ;;
    esac
done

CONF_FILE="${DEPLOY_DIR}/deploy.conf"
if [[ -f "${CONF_FILE}" ]]; then
    source "${CONF_FILE}"
    log_info "Loaded config: ${CONF_FILE}"
else
    log_warn "deploy/deploy.conf not found — using defaults"
fi

[[ -n "${_OVERRIDE_BASE}" ]] && BASE_DIR="${_OVERRIDE_BASE}"

resolve_paths
show_paths

_should_run() {
    local step="$1"
    [[ -n "${_ONLY_STEP}" ]] && [[ "${step}" == "${_ONLY_STEP}" ]] && return 0
    [[ -n "${_ONLY_STEP}" ]] && return 1
    [[ "${step}" -ge "${_FROM_STEP}" ]] && return 0
    return 1
}

_run_step() {
    local step="$1" script="$2"
    if _should_run "${step}"; then
        bash "${DEPLOY_DIR}/${script}"
    else
        log_info "Skipping step ${step} (${script})"
    fi
}

echo ""
echo -e "${_BLD}${_CYN}╔══════════════════════════════════════════╗${_RST}"
echo -e "${_BLD}${_CYN}║     MethylongAgent Deployment            ║${_RST}"
echo -e "${_BLD}${_CYN}╚══════════════════════════════════════════╝${_RST}"

_run_step 1 "01_setup_dirs.sh"

_run_step 2 "02_setup_sin_env.sh"

if _should_run 3 || _should_run 4; then
    echo ""
    if _should_run 3 && _should_run 4; then
        log_info "Steps 3 & 4 running in parallel..."
        bash "${DEPLOY_DIR}/03_pull_images.sh" \
            > >(sed 's/^/[03_pull_images] /') \
            2> >(sed 's/^/[03_pull_images] /' >&2) &
        _pid_3=$!

        bash "${DEPLOY_DIR}/04_setup_agent_env.sh" \
            > >(sed 's/^/[04_agent_env]   /') \
            2> >(sed 's/^/[04_agent_env]   /' >&2) &
        _pid_4=$!

        wait_job "${_pid_3}" "03_pull_images.sh"
        wait_job "${_pid_4}" "04_setup_agent_env.sh"
    else
        _run_step 3 "03_pull_images.sh"
        _run_step 4 "04_setup_agent_env.sh"
    fi
fi

_run_step 5 "05_pull_dorado_models.sh"

if [[ "${_SKIP_LLM}" == "true" ]]; then
    log_info "Skipping step 6 (--skip-llm)"
else
    _run_step 6 "06_download_llm.sh"
fi

# Step 8 runs before step 7 so the final check sees the patched config
_run_step 8 "08_patch_config.sh"

_run_step 7 "07_final_check.sh"
