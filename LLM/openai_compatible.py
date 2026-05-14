from langchain_openai import ChatOpenAI


def get_llm(model_dir: str, device: str = "cpu", temperature: float = 0.7, **kwargs) -> ChatOpenAI:
    """
    OpenAI-compatible API wrapper (DeepSeek, Qwen, vLLM, Ollama, etc.)
    model_dir is unused for API models; endpoint config comes from model_config.
    """
    from configs.model_config import openai_compat_config

    return ChatOpenAI(
        model=openai_compat_config["model"],
        base_url=openai_compat_config["base_url"],
        api_key=openai_compat_config["api_key"],
        temperature=temperature,
        max_tokens=openai_compat_config.get("max_tokens", 4096),
    )
