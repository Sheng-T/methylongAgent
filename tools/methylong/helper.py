import os
import re


def _find_latest_dorado_model(model_dir: str, prefix: str, major_version: int = 0) -> str:
    """
    Find the latest dorado model directory matching the given prefix and optional major version.
    Returns the full path or empty string if not found.
    """
    if not os.path.isdir(model_dir):
        return ""
    candidates = []
    for name in os.listdir(model_dir):
        if not name.startswith(prefix):
            continue
        full = os.path.join(model_dir, name)
        if not os.path.isdir(full):
            continue
        ver_match = re.search(r'@v(\d+)\.(\d+)\.(\d+)', name)
        if ver_match:
            ver = tuple(int(x) for x in ver_match.groups())
            if major_version > 0 and ver[0] != major_version:
                continue
            candidates.append((ver, full))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _resolve_methylong_models(data_path: dict) -> tuple[str, str]:
    """
    Returns (dorado_model_path, dorado_modification_model_path).
    Returns empty strings if not found.
    """
    model_dir = os.path.abspath(os.path.expanduser(
        data_path.get("dorado", {}).get("dorado_models", "")
        or os.path.expanduser("~/tools/dorado_model/")
    ))
    sample_rate = int(data_path.get("dorado", {}).get("sample_rate", 0))
    major = 4 if sample_rate == 4000 else (5 if sample_rate == 5000 else 0)

    simplex_model = _find_latest_dorado_model(model_dir, "dna_r10.4.1_e8.2_400bps_sup@v", major_version=major)
    if not simplex_model and major > 0:
        simplex_model = _find_latest_dorado_model(model_dir, "dna_r10.4.1_e8.2_400bps_sup@v")

    mod_model = ""
    if os.path.isdir(model_dir):
        candidates = []
        for name in os.listdir(model_dir):
            if re.match(r'dna_r10\.4\.1_e8\.2_400bps_sup@v\d+\.\d+\.\d+_5mC_5hmC@v\d+', name):
                if os.path.isdir(os.path.join(model_dir, name)):
                    ver_match = re.search(r'@v(\d+)\.(\d+)\.(\d+)_5mC_5hmC@v(\d+)', name)
                    if ver_match:
                        ver = tuple(int(x) for x in ver_match.groups())
                        if major > 0 and ver[0] != major:
                            continue
                        candidates.append((ver, os.path.join(model_dir, name)))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            mod_model = candidates[0][1]
        if not mod_model and major > 0:
            for name in os.listdir(model_dir):
                if re.match(r'dna_r10\.4\.1_e8\.2_400bps_sup@v\d+\.\d+\.\d+_5mC_5hmC@v\d+', name):
                    if os.path.isdir(os.path.join(model_dir, name)):
                        ver_match = re.search(r'@v(\d+)\.(\d+)\.(\d+)_5mC_5hmC@v(\d+)', name)
                        if ver_match:
                            ver = tuple(int(x) for x in ver_match.groups())
                            candidates.append((ver, os.path.join(model_dir, name)))
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                mod_model = candidates[0][1]

    return simplex_model, mod_model
