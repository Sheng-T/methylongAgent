#!/usr/bin/env bash
# deploy/02_setup_sin_env.sh — create sin conda env with Nextflow + Singularity/Apptainer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

if [[ -z "${BASE_DIR:-}" ]]; then
    [[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
    resolve_paths
fi

log_step "Step 2 — Set up sin conda env (Nextflow + Singularity)"

init_conda

if conda_env_exists "${SIN_ENV}"; then
    log_info "Conda env '${SIN_ENV}' already exists, skipping creation."
else
    log_info "Creating conda env '${SIN_ENV}' with Python 3.10..."
    conda create -y -n "${SIN_ENV}" python=3.10
    log_success "Conda env '${SIN_ENV}' created."
fi

# Install Nextflow
if conda_run "${SIN_ENV}" which nextflow &>/dev/null; then
    NF_VER=$(conda_run "${SIN_ENV}" nextflow -version 2>/dev/null | grep -oP '[\d.]+' | head -1 || echo "unknown")
    log_info "Nextflow already installed (${NF_VER}), skipping."
else
    log_info "Installing Nextflow..."
    conda_run "${SIN_ENV}" conda install -y -c bioconda nextflow || \
        conda install -y -n "${SIN_ENV}" -c bioconda nextflow
    log_success "Nextflow installed."
fi

# Check Singularity / Apptainer
_has_singularity=false
for _c in singularity apptainer; do
    if conda_run "${SIN_ENV}" which "$_c" &>/dev/null || command -v "$_c" &>/dev/null; then
        log_info "${_c} found."
        _has_singularity=true
        break
    fi
done

if [[ "${_has_singularity}" == "false" ]]; then
    log_info "Installing Apptainer via conda-forge..."
    conda install -y -n "${SIN_ENV}" -c conda-forge apptainer || \
        conda install -y -n "${SIN_ENV}" -c conda-forge singularity || \
        die "Failed to install Singularity/Apptainer. Please install manually."
    log_success "Apptainer installed."
fi

# Verify
NF_VER=$(conda_run "${SIN_ENV}" nextflow -version 2>/dev/null | grep -oP '[\d.]+' | head -1 || echo "FAILED")
[[ "${NF_VER}" == "FAILED" ]] && die "Nextflow verification failed."
log_success "Nextflow ${NF_VER}"

SNG_VER=$(conda_run "${SIN_ENV}" singularity --version 2>/dev/null \
          || conda_run "${SIN_ENV}" apptainer --version 2>/dev/null \
          || singularity --version 2>/dev/null \
          || apptainer --version 2>/dev/null \
          || echo "FAILED")
[[ "${SNG_VER}" == "FAILED" ]] && die "Singularity/Apptainer verification failed."
log_success "Singularity/Apptainer: ${SNG_VER}"

log_done "sin env setup complete"
