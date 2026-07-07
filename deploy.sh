#!/usr/bin/env bash
# =============================================================================
#  MethylongAgent one-click deployment script
#
#  First run: just run "bash deploy.sh" and follow the prompts.
#
#  Usage:
#    bash deploy.sh                  # interactive setup if not configured
#    bash deploy.sh --reconfigure    # re-run the setup wizard
#    bash deploy.sh --base /data     # override BASE_DIR (skip wizard)
#    bash deploy.sh --skip-llm       # skip LLM model download
#    bash deploy.sh --step 3         # run a single step (1-9)
#    bash deploy.sh --from 4         # run from step N onward
#    bash deploy.sh --help           # show help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/deploy"
CONF_FILE="${DEPLOY_DIR}/deploy.conf"

source "${DEPLOY_DIR}/common.sh"

_SKIP_LLM=false
_ONLY_STEP=""
_FROM_STEP=1
_OVERRIDE_BASE=""
_RECONFIGURE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base)         _OVERRIDE_BASE="$2"; shift 2 ;;
        --skip-llm)     _SKIP_LLM=true; shift ;;
        --step)         _ONLY_STEP="$2"; shift 2 ;;
        --from)         _FROM_STEP="$2"; shift 2 ;;
        --reconfigure)  _RECONFIGURE=true; shift ;;
        --help|-h)
            cat <<EOF
MethylongAgent deployment script

Usage:
  bash deploy.sh [options]

Options:
  --reconfigure    Re-run the interactive setup wizard
  --base  <dir>   Override BASE_DIR (skips wizard)
  --skip-llm      Skip LLM/model download (step 6)
  --step  <n>     Run only step n (1-9)
  --from  <n>     Run from step n onward (1-9)
  --help          Show this help

Steps:
  1  Create directory structure
  2  Create sin conda env (Nextflow + Singularity)
  3  Pull Singularity images
  4  Create agent Python env
  5  Download Dorado basecall models
  6  Download LLM / Embedding / Reranker models
  7  Download and patch workflow files
  8  Patch config.yaml
  9  Final environment checks
EOF
            exit 0
            ;;
        *) log_warn "Unknown argument: $1"; shift ;;
    esac
done

_detect_cuda() {
    local ver
    ver=$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[\d.]+' | head -1 || true)
    [[ -z "$ver" ]] && { echo "cpu"; return; }
    local major minor
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if   [[ $major -ge 12 && $minor -ge 4 ]]; then echo "cu124"
    elif [[ $major -ge 12 ]];                 then echo "cu121"
    elif [[ $major -ge 11 ]];                 then echo "cu118"
    else echo "cpu"
    fi
}

_detect_gpu_device() {
    nvidia-smi -L &>/dev/null 2>&1 && echo "cuda:0" || echo "cpu"
}

_detect_max_memory() {
    local gb
    gb=$(free -g 2>/dev/null | awk '/^Mem:/{print int($2*0.8)}' || true)
    [[ -n "$gb" && "$gb" -gt 0 ]] && echo "${gb}.GB" || echo "30.GB"
}

_detect_cpus() {
    nproc 2>/dev/null || echo ""
}

# Prints:  Label [default]:
_ask() {
    local label="$1" default="$2" varname="$3"
    local answer
    if [[ -n "$default" ]]; then
        read -rp "  ${label} [${default}]: " answer
        answer="${answer:-$default}"
    else
        read -rp "  ${label}: " answer
    fi
    printf -v "$varname" '%s' "$answer"
}

# _ask_choice "Label" "opt1|opt2|opt3" "default" VAR_NAME
_ask_choice() {
    local label="$1" choices="$2" default="$3" varname="$4"
    while true; do
        local answer
        read -rp "  ${label} (${choices}) [${default}]: " answer
        answer="${answer:-$default}"
        if echo "|${choices}|" | grep -q "|${answer}|"; then
            printf -v "$varname" '%s' "$answer"
            return
        fi
        echo "    闂?Please enter one of: ${choices}"
    done
}

_run_wizard() {
    echo ""
    echo -e "${_BLD}${_CYN}闂傚倷绀佺壕顓㈠磿閵堝钃熼柨鐔哄Т閻ら箖鏌＄仦璇插姎闁绘挻鐩弻鐔兼嚋椤掆偓婵¤姤绻涢崨顔剧煉闁哄苯绉归幃婊兾熼崫鍕垫綂闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢?{_RST}"
    echo -e "${_BLD}${_CYN}闂?    MethylongAgent 闂?Setup Wizard        闂?{_RST}"
    echo -e "${_BLD}${_CYN}闂傚倷绀佺壕顓㈠磿閵堝鏄ラ柛鎰靛枛閻ら箖鏌＄仦璇插姎闁绘挻鐩弻鐔兼嚋椤掆偓婵¤姤绻涢崨顔剧煉闁哄苯绉归幃婊兾熼崫鍕垫綂闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢?{_RST}"
    echo ""
    echo "  Press Enter to accept the detected / default value."
    echo "  Results are saved to deploy/deploy.conf."
    echo ""

    # 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞?Detect system info 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟?
    local _det_cuda _det_device _det_mem _det_cpus
    _det_cuda=$(_detect_cuda)
    _det_device=$(_detect_gpu_device)
    _det_mem=$(_detect_max_memory)
    _det_cpus=$(_detect_cpus)

    echo -e "${_BLD}System detected:${_RST}"
    echo "  CUDA wheel : ${_det_cuda}"
    echo "  GPU device : ${_det_device}"
    echo "  Memory     : ${_det_mem} (80% of RAM)"
    [[ -n "$_det_cpus" ]] && echo "  CPUs       : ${_det_cpus}"
    echo ""

    # 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞?Prompts 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌?    local W_BASE W_LLM_MODE W_CUDA W_DEVICE W_PORT W_REPO
    local W_API_KEY W_API_URL W_API_MODEL
    local W_MEM W_CPUS

    echo -e "${_BLD}[1/5] Directories${_RST}"
    _ask "Base directory for all data files" "${HOME}/methylong" W_BASE

    echo ""
    echo -e "${_BLD}[2/5] LLM backend${_RST}"
    _ask_choice "LLM mode" "local|api" "local" W_LLM_MODE

    echo ""
    if [[ "$W_LLM_MODE" == "local" ]]; then
        echo -e "${_BLD}[3/5] Local model settings${_RST}"
        _ask_choice "CUDA version for PyTorch wheel" "cu118|cu121|cu124|cpu" "$_det_cuda" W_CUDA
        _ask "Inference device" "$_det_device" W_DEVICE
        W_API_KEY=""; W_API_URL="https://api.deepseek.com/v1"; W_API_MODEL="deepseek-chat"
    else
        echo -e "${_BLD}[3/5] API settings${_RST}"
        _ask "API key (e.g. sk-...)" "" W_API_KEY
        _ask "API base URL" "https://api.deepseek.com/v1" W_API_URL
        _ask "API model name" "deepseek-chat" W_API_MODEL
        W_CUDA="cu118"; W_DEVICE="cpu"
    fi

    echo ""
    echo -e "${_BLD}[4/5] Nextflow resource limits${_RST}"
    _ask "Max memory for Nextflow" "$_det_mem" W_MEM
    if [[ -n "$_det_cpus" ]]; then
        local _cpus_prompt
        _ask "Max CPUs (Enter for auto-detect)" "" W_CPUS
    else
        W_CPUS=""
    fi

    echo ""
    echo -e "${_BLD}[5/5] Pipeline & server${_RST}"
    _ask "methylong pipeline git URL" "https://github.com/nf-core/methylong.git" W_REPO
    _ask "Web server port" "50027" W_PORT

    # 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞?Write deploy.conf 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹?    echo ""
    log_info "Writing deploy/deploy.conf ..."

    cat > "${CONF_FILE}" <<EOF
# =============================================================================
#  MethylongAgent deployment configuration
# =============================================================================

BASE_DIR="${W_BASE}"

SIN_ENV="sin"
AGENT_ENV="methylong_agent"
PYTHON_VERSION="3.10"

CUDA_VERSION="${W_CUDA}"

DORADO_SAMPLE_RATE=5000

LLM_MODE="${W_LLM_MODE}"

LLM_MODEL_NAME="qwen3_14B"
LLM_DEVICE="${W_DEVICE}"
HF_ENDPOINT=""

API_BASE_URL="${W_API_URL}"
API_KEY="${W_API_KEY}"
API_MODEL="${W_API_MODEL}"

SERVER_PORT=${W_PORT}
USER_QUOTA_GB=10

NF_MAX_MEMORY="${W_MEM}"
NF_MAX_TIME="72.h"
NF_MAX_CPUS="${W_CPUS}"

METHYLONG_PIPELINE_REPO="${W_REPO}"
METHYLONG_PIPELINE_REF=""
EOF

    log_success "deploy/deploy.conf saved."
    echo ""
}


# Run wizard if BASE_DIR is unset and we're doing a full deployment
_need_wizard=false
[[ -z "${_OVERRIDE_BASE}" && -z "${BASE_DIR:-}" ]] && _need_wizard=true
[[ "${_RECONFIGURE}" == "true" ]]                  && _need_wizard=true

if [[ "${_need_wizard}" == "true" && -z "${_ONLY_STEP}" && "${_FROM_STEP}" -eq 1 ]]; then
    _run_wizard
    source "${CONF_FILE}"
fi

[[ -n "${_OVERRIDE_BASE}" ]] && BASE_DIR="${_OVERRIDE_BASE}"

resolve_paths
show_paths

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
echo -e "${_BLD}${_CYN}闂傚倷绀佺壕顓㈠磿閵堝钃熼柨鐔哄Т閻ら箖鏌＄仦璇插姎闁绘挻鐩弻鐔兼嚋椤掆偓婵¤姤绻涢崨顔剧煉闁哄苯绉归幃婊兾熼崫鍕垫綂闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢?{_RST}"
echo -e "${_BLD}${_CYN}闂?    MethylongAgent Deployment            闂?{_RST}"
echo -e "${_BLD}${_CYN}闂傚倷绀佺壕顓㈠磿閵堝鏄ラ柛鎰靛枛閻ら箖鏌＄仦璇插姎闁绘挻鐩弻鐔兼嚋椤掆偓婵¤姤绻涢崨顔剧煉闁哄苯绉归幃婊兾熼崫鍕垫綂闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢宥咁煥閸喓鍘撻梺缁樺灦閿氬┑顔瑰亾闂備礁鎼幊蹇涙偂閿熺姴鏄ラ柨鐔哄Т缁犳盯鏌曟繝蹇涙闁绘繃濞婂鍝勭暦閸パ冨闂佸憡鏌ㄧ换妯侯嚕閺屻儱钃熼柕澶堝劤閸樻悂姊虹涵鍛劷闁告柨绉撮埢?{_RST}"

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

# Run workflow download/patching before config patching.
_run_step 7 "07_download_workflows.sh"
_run_step 8 "08_patch_config.sh"
_run_step 9 "09_final_check.sh"
