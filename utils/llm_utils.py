import importlib
import json
import logging
import re
import sys
import threading
from typing import Any, Iterator

from langchain_core.runnables import Runnable, RunnableConfig

from configs.model_config import LLM_NAME, LLM_SOURCE, llm_model_path
from configs.runtime_config import llm_args

logging.getLogger("transformers").setLevel(logging.ERROR)


def import_llm_initializer(module_name: str, function_name: str = "get_llm"):
    full_module_path = f"LLM.{module_name}"
    try:
        spec = importlib.util.find_spec(full_module_path)
        if spec is None:
            raise ModuleNotFoundError(f"Unable to find the module: {full_module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_path] = module
        spec.loader.exec_module(module)
        if not hasattr(module, function_name):
            raise AttributeError(f"The function '{function_name}' was not found in '{module_name}'.")
        return getattr(module, function_name)
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Fatal error: Dynamic import of LLM failed: {e}")
        raise e


_MODEL_CACHE: dict = {}
_model_init_lock = threading.Lock()
_inference_lock = threading.Lock()


class _ThreadSafeLLMWrapper(Runnable):
    """
    Wraps a local GPU model to serialize inference and prevent concurrent GPU use.
    Inherits from LangChain Runnable to support pipe (|) operations.
    """
    def __init__(self, model, temperature: float, enable_thinking: bool):
        super().__init__()
        self._model = model
        self.temperature = temperature
        self.enable_thinking = enable_thinking

    @property
    def InputType(self):
        return str

    @property
    def OutputType(self):
        return str

    def invoke(self, input: str, config: RunnableConfig = None) -> Any:
        with _inference_lock:
            self._model.temperature = self.temperature
            self._model.enable_thinking = self.enable_thinking
            return self._model.invoke(input)

    def batch(self, inputs: list, config: RunnableConfig = None, **kwargs) -> list:
        return [self.invoke(input_item, config) for input_item in inputs]

    def stream(self, input: str, config: RunnableConfig = None, **kwargs) -> Iterator:
        with _inference_lock:
            self._model.temperature = self.temperature
            self._model.enable_thinking = self.enable_thinking
            if hasattr(self._model, 'stream'):
                yield from self._model.stream(input)
            else:
                yield self._model.invoke(input)


def invoke_json(llm, prompt_str: str) -> dict:
    """Invoke the LLM with a plain string prompt and parse the JSON response."""
    raw = llm.invoke(prompt_str)
    content = raw if isinstance(raw, str) else raw.content
    clean = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()
    return json.loads(clean)


def get_llm_instance(is_planner: bool = False, temperature: float = 0.01):
    """
    Returns a ready-to-use LLM object.

    - LLM_SOURCE == "api": creates a new API client instance each call (thread-safe)
    - LLM_SOURCE == "huggingface": shared local model with serialized GPU inference
    """
    if LLM_SOURCE == "api":
        t = temperature if is_planner else 0.7
        llm_func = import_llm_initializer(module_name=LLM_NAME)
        return llm_func("", device="cpu", temperature=t)

    with _model_init_lock:
        if "llm" not in _MODEL_CACHE:
            print("[System] Initializing the model for the first time, please wait ..")
            llm_func = import_llm_initializer(module_name=LLM_NAME)
            llm_path = llm_model_path[LLM_NAME]
            _MODEL_CACHE["llm"] = llm_func(llm_path, device=llm_args['device'])

    model = _MODEL_CACHE["llm"]
    if is_planner:
        return _ThreadSafeLLMWrapper(model, temperature=temperature, enable_thinking=False)
    else:
        return _ThreadSafeLLMWrapper(model, temperature=0.7, enable_thinking=True)
