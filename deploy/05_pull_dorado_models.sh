#!/usr/bin/env bash
# deploy/05_pull_dorado_models.sh — download Dorado basecall models using the Dorado SIF
# Requires: Dorado SIF already pulled (03_pull_images.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

if [[ -z "${BASE_DIR:-}" ]]; then
    [[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
    resolve_paths
fi

log_step "Step 5 — Download Dorado basecall models"

_SIMPLEX_MODEL="dna_r10.4.1_e8.2_400bps_sup@v5.2.0"
_MOD_MODEL="dna_r10.4.1_e8.2_400bps_sup@v5.2.0_5mC_5hmC@v2"

log_info "Simplex model : ${_SIMPLEX_MODEL}"
log_info "Mod model     : ${_MOD_MODEL}"
log_info "Download dir  : ${DORADO_MODEL_DIR}"

_DORADO_FIXED="${METHYLONG_IMAGE_DIR}/docker.io-nanoporetech-dorado-shae423e761540b9d08b526a1eb32faf498f32e8f22.img"

if [[ -f "${_DORADO_FIXED}" ]]; then
    DORADO_SIF="${_DORADO_FIXED}"
else
    DORADO_SIF=""
    for f in "${METHYLONG_IMAGE_DIR}"/*.img "${METHYLONG_IMAGE_DIR}"/*.sif; do
        [[ -f "$f" ]] || continue
        [[ "$(basename "$f")" == *dorado* ]] && { DORADO_SIF="$f"; break; }
    done
fi

if [[ -z "${DORADO_SIF}" || ! -f "${DORADO_SIF}" ]]; then
    log_error "Dorado SIF not found in ${METHYLONG_IMAGE_DIR}"
    log_error "Please run 03_pull_images.sh first."
    exit 1
fi
log_info "Using Dorado SIF: ${DORADO_SIF}"

init_conda
_sng=""
for _c in singularity apptainer; do
    if conda_run "${SIN_ENV}" which "$_c" &>/dev/null; then
        _sng="conda_run ${SIN_ENV} ${_c}"; break
    elif command -v "$_c" &>/dev/null; then
        _sng="$_c"; break
    fi
done
[[ -z "${_sng}" ]] && die "Singularity/Apptainer not found."

_dorado_exec() {
    ${_sng} exec --nv \
        --bind "${DORADO_MODEL_DIR}:${DORADO_MODEL_DIR}" \
        "${DORADO_SIF}" "$@"
}

_download_model() {
    local model_name="$1"
    local dest="${DORADO_MODEL_DIR}/${model_name}"
    if [[ -d "${dest}" ]]; then
        log_info "Already exists, skipping: ${model_name}"
        return 0
    fi
    log_info "Downloading: ${model_name}"
    _dorado_exec dorado download \
        --model "${model_name}" \
        --directory "${DORADO_MODEL_DIR}"
    if [[ -d "${dest}" ]]; then
        log_success "Downloaded: ${model_name}"
    else
        log_warn "Download may have failed — check ${DORADO_MODEL_DIR}"
        return 1
    fi
}

_download_model "${_SIMPLEX_MODEL}"
_download_model "${_MOD_MODEL}"

log_info "Dorado models in ${DORADO_MODEL_DIR}:"
ls -1 "${DORADO_MODEL_DIR}/" 2>/dev/null || log_warn "Model directory is empty."

log_done "Dorado model download complete"
