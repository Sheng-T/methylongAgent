#!/usr/bin/env bash
# deploy/07_download_workflows.sh - download and patch workflow files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"

[[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
resolve_paths

log_step "Step 7 - Download workflows and apply compatibility patches"

PIPELINE_DIR="${PIPELINE_DIR:-${BASE_DIR}/agent_workflow}"
STATIC_WORKFLOWS="${PROJECT_ROOT}/static/workflows"
SINGULARITY_DIR="${SINGULARITY_DIR:-${BASE_DIR}/singularity_image}"
IMAGE_DIR="${SINGULARITY_DIR}/workflow"

pipeline_cloned=false

if [[ -n "${METHYLONG_PIPELINE_REPO:-}" ]]; then
    _pipeline_dest="${PIPELINE_DIR}/methylong"
    if [[ -d "${_pipeline_dest}/.git" ]]; then
        log_info "Pipeline repo exists, pulling latest..."
        git -C "${_pipeline_dest}" pull || log_warn "git pull failed, using existing code."
        pipeline_cloned=true
    else
        log_info "Cloning pipeline from ${METHYLONG_PIPELINE_REPO}..."
        _ref_arg=()
        [[ -n "${METHYLONG_PIPELINE_REF:-}" ]] && _ref_arg=(--branch "${METHYLONG_PIPELINE_REF}")
        if git clone "${_ref_arg[@]}" "${METHYLONG_PIPELINE_REPO}" "${_pipeline_dest}"; then
            log_success "Pipeline cloned to ${_pipeline_dest}"
            pipeline_cloned=true
        else
            log_warn "Pipeline clone failed, patch step will only use existing local files."
        fi
    fi
else
    log_warn "METHYLONG_PIPELINE_REPO not set - place pipeline code manually at ${PIPELINE_DIR}/methylong/"
fi

log_info "Applying workflow compatibility patches..."

patches_found=0
patches_applied=0

for workflow_dir in "${STATIC_WORKFLOWS}"/*/; do
    [[ -d "${workflow_dir}" ]] || continue
    workflow_name=$(basename "${workflow_dir}")
    patch_file="${workflow_dir}patch/patch.py"
    pipeline_target="${PIPELINE_DIR}/${workflow_name}"
    pipeline_image_dir="${IMAGE_DIR}/${workflow_name}"

    if [[ -f "${patch_file}" ]]; then
        patches_found=$((patches_found + 1))
        log_info "Found patch for workflow: ${workflow_name}"

        if [[ -d "${pipeline_target}" ]]; then
            if [[ "${workflow_name}" == "methylong" ]]; then
                _required_files=(
                    "${pipeline_target}/modules/local/dorado/basecaller/main.nf"
                    "${pipeline_target}/nextflow.config"
                )
                _missing_files=()
                for _required in "${_required_files[@]}"; do
                    [[ -f "${_required}" ]] || _missing_files+=("${_required}")
                done
                if [[ ${#_missing_files[@]} -gt 0 ]]; then
                    log_warn "Pipeline directory exists but is not a compatible methylong source tree; skipping patch."
                    for _missing in "${_missing_files[@]}"; do
                        log_warn "  missing: ${_missing}"
                    done
                    continue
                fi
            fi

            log_info "  Applying: ${patch_file} -> ${pipeline_target}"
            init_conda
            conda_run "${AGENT_ENV}" python3 "${patch_file}" --base "${pipeline_target}" --cache-dir "${pipeline_image_dir}" && {
                patches_applied=$((patches_applied + 1))
                log_success "Patched: ${workflow_name}"
            } || {
                log_error "Failed to patch: ${workflow_name}"
            }
        else
            if [[ "${workflow_name}" == "methylong" && "${pipeline_cloned}" != "true" && -z "${METHYLONG_PIPELINE_REPO:-}" ]]; then
                log_warn "Pipeline directory not found because METHYLONG_PIPELINE_REPO is unset; skipping patch: ${pipeline_target}"
            else
                log_warn "Pipeline directory not found, skipping: ${pipeline_target}"
            fi
        fi
    fi
done

if [[ ${patches_found} -eq 0 ]]; then
    log_info "No workflow patches found in ${STATIC_WORKFLOWS}"
elif [[ ${patches_applied} -lt ${patches_found} ]]; then
    log_warn "${patches_applied}/${patches_found} patches applied (some skipped)"
else
    log_success "${patches_applied} workflow patch(es) applied."
fi

log_done "Workflow patching complete"
