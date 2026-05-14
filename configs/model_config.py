
# ── Read API settings from secrets.py (gitignored) ────────────────────────────
def _secret(name: str, default=""):
    try:
        import configs.secrets as _s
        return getattr(_s, name, default) or default
    except ImportError:
        return default

_api_key = _secret("LLM_API_KEY")

# Auto-switch: local GPU when no API key, API mode when key is set.
LLM_SOURCE = "api"               if _api_key else "huggingface"
LLM_NAME   = "openai_compatible" if _api_key else "qwen3_14B"

# OpenAI-compatible endpoint config — all values read from secrets.py.
openai_compat_config = {
    "base_url":   _secret("LLM_API_BASE_URL", "https://api.deepseek.com/v1"),
    "api_key":    _api_key,
    "model":      _secret("LLM_API_MODEL",    "deepseek-chat"),
    "max_tokens": _secret("LLM_API_MAX_TOKENS", 4096),
}

llm_model_path: dict = {
    "qwen3_14B":  "/path/to/qwen3-14b",
    "embedding":  "/path/to/embedding-model",
    "reranker":   "/path/to/reranker-model",
}
