#!/usr/bin/env bash
# deploy/03_pull_images.sh 閳?pull all Singularity images to METHYLONG_IMAGE_DIR
# Depot images are downloaded directly via wget (pre-built .img files).
# Docker images are pulled via singularity pull docker://.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

[[ -f "${SCRIPT_DIR}/deploy.conf" ]] && source "${SCRIPT_DIR}/deploy.conf"
resolve_paths

log_step "Step 3 閳?Pull Singularity images"
log_info "Target dir: ${METHYLONG_IMAGE_DIR}"

init_conda

_sng=""
for _c in singularity apptainer; do
    if conda_run "${SIN_ENV}" which "$_c" &>/dev/null; then
        _sng="conda_run ${SIN_ENV} ${_c}"; break
    elif command -v "$_c" &>/dev/null; then
        _sng="$_c"; break
    fi
done
[[ -z "${_sng}" ]] && die "Singularity/Apptainer not found. Run 02_setup_sin_env.sh first."

_total=0; _skipped=0; _ok=0; _failed=0
_failed_list=()

_wget_image() {
    local url="$1" filename="$2"
    local dest="${METHYLONG_IMAGE_DIR}/${filename}"
    (( _total++ )) || true
    if [[ -f "${dest}" ]]; then
        log_info "Skip (exists): ${filename}"; (( _skipped++ )) || true; return 0
    fi
    log_info "Downloading: ${filename}"
    local tmp="${dest}.tmp"
    if wget -q --show-progress -O "${tmp}" "${url}"; then
        mv "${tmp}" "${dest}"
        log_success "Done: ${filename}  ($(du -sh "${dest}" | cut -f1))"
        (( _ok++ )) || true
    else
        rm -f "${tmp}"
        log_error "Failed: ${filename}"
        _failed_list+=("${filename}"); (( _failed++ )) || true; return 1
    fi
}

_docker_image() {
    local url="$1" filename="$2" fallback_url="${3:-}"
    local dest="${METHYLONG_IMAGE_DIR}/${filename}"
    (( _total++ )) || true
    if [[ -f "${dest}" ]]; then
        log_info "Skip (exists): ${filename}"; (( _skipped++ )) || true; return 0
    fi
    log_info "Pulling: ${filename}"
    if ${_sng} pull --force "${dest}" "${url}" 2>&1; then
        if [[ -f "${dest}" ]]; then
            log_success "Done: ${filename}  ($(du -sh "${dest}" | cut -f1))"
            (( _ok++ )) || true; return 0
        fi
    fi
    if [[ -n "${fallback_url}" ]]; then
        log_warn "Primary source failed, trying fallback: ${fallback_url}"
        if ${_sng} pull --force "${dest}" "${fallback_url}" 2>&1 && [[ -f "${dest}" ]]; then
            log_success "Done (fallback): ${filename}  ($(du -sh "${dest}" | cut -f1))"
            (( _ok++ )) || true; return 0
        fi
    fi
    log_error "Failed: ${filename}"
    _failed_list+=("${filename}"); (( _failed++ )) || true; return 1
}

# Depot images (direct HTTP download)
_wget_image "https://depot.galaxyproject.org/singularity/clair3:1.1.1--py310h779eee5_0" \
    "depot.galaxyproject.org-singularity-clair3-1.1.1--py310h779eee5_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/fastqc:0.12.1--hdfd78af_0" \
    "depot.galaxyproject.org-singularity-fastqc-0.12.1--hdfd78af_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/gawk:5.3.0" \
    "depot.galaxyproject.org-singularity-gawk-5.3.0.img"
_wget_image "https://depot.galaxyproject.org/singularity/pigz:2.8" \
    "depot.galaxyproject.org-singularity-pigz-2.8.img"
_wget_image "https://depot.galaxyproject.org/singularity/samtools:1.22.1--h96c455f_0" \
    "depot.galaxyproject.org-singularity-samtools-1.22.1--h96c455f_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/ccsmeth:0.5.0--pyhdfd78af_0" \
    "depot.galaxyproject.org-singularity-ccsmeth-0.5.0--pyhdfd78af_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/pbjasmine:2.4.0--h9948957_1" \
    "depot.galaxyproject.org-singularity-pbjasmine-2.4.0--h9948957_1.img"
_wget_image "https://depot.galaxyproject.org/singularity/fibertools-rs:0.7.1--h3b373d1_0" \
    "depot.galaxyproject.org-singularity-fibertools-rs-0.7.1--h3b373d1_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/pbmm2:1.14.99--h9ee0642_0" \
    "depot.galaxyproject.org-singularity-pbmm2-1.14.99--h9ee0642_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/ont-modkit:0.5.0--hcdda2d0_2" \
    "depot.galaxyproject.org-singularity-ont-modkit-0.5.0--hcdda2d0_2.img"
_wget_image "https://depot.galaxyproject.org/singularity/whatshap:2.6--py39h2de1943_0" \
    "depot.galaxyproject.org-singularity-whatshap-2.6--py39h2de1943_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/bioconductor-dss:2.54.0--r44h3df3fcb_0" \
    "depot.galaxyproject.org-singularity-bioconductor-dss-2.54.0--r44h3df3fcb_0.img"
_wget_image "https://depot.galaxyproject.org/singularity/ubuntu%3A24.04" \
    "depot.galaxyproject.org-singularity-ubuntu%3A24.04.img"

# Docker images (singularity pull docker://)
_docker_image \
    "docker://quay.io/pacbio/pb-cpg-tools:3.0.0_build1" \
    "quay.io-pacbio-pb-cpg-tools-3.0.0_build1.img"

_docker_image \
    "docker://nanoporetech/dorado:shae423e761540b9d08b526a1eb32faf498f32e8f22" \
    "docker.io-nanoporetech-dorado-shae423e761540b9d08b526a1eb32faf498f32e8f22.img" \
    "docker://docker.1ms.run/nanoporetech/dorado:shae423e761540b9d08b526a1eb32faf498f32e8f22"

echo ""
echo -e "${_BLD}Images: total=${_total}  skipped=${_skipped}  ok=${_ok}  failed=${_failed}${_RST}"

if [[ ${_failed} -gt 0 ]]; then
    log_error "Failed images:"
    for f in "${_failed_list[@]}"; do echo "  - ${f}"; done
    exit 1
fi

log_done "Image pull complete"
