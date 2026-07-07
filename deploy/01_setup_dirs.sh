#!/usr/bin/env bash
# deploy/01_setup_dirs.sh 鈥?create required directory structure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

[[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
resolve_paths

log_step "Step 1 鈥?Create directories"
show_paths

_dirs=(
    "${SINGULARITY_DIR}/workflow/methylong"
    "${DORADO_MODEL_DIR}"
    "${PIPELINE_DIR}/methylong"
    "${AGENT_DATA_DIR}"
    "${AGENT_DATA_DIR}/nextflow_work"
    "${AGENT_DATA_DIR}/.nextflow"
)

for d in "${_dirs[@]}"; do
    if [[ -d "$d" ]]; then
        log_info "Already exists: $d"
    else
        mkdir -p "$d"
        log_success "Created: $d"
    fi
done

log_done "Directory setup complete"
