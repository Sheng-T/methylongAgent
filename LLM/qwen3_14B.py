import torch
from typing import Any, List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from langchain_core.language_models.llms import LLM

class Qwen3LLM(LLM):

    model: Any
    tokenizer: Any
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    enable_thinking: bool = True
    system_role: str = "You are a helpful assistant."

    @property
    def _llm_type(self) -> str:
        return "qwen3"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        system_prompt = "You are a helpful assistant." if self.system_role is None else self.system_role
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.enable_thinking,
        )

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=self.temperature,
                top_p=self.top_p,
                repetition_penalty=self.repetition_penalty,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        gen_ids = outputs[0][inputs.input_ids.shape[-1]:]
        text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)

        # 可选 stop 处理
        if stop:
            for s in stop:
                if s in text:
                    text = text.split(s)[0]

        return text.strip()


def get_llm(
    model_dir: str,
    device: str = "auto",
    torch_dtype: Any = "auto",
    max_new_tokens: int = 1024,
    temperature: float = 0.7,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
    enable_thinking: bool = True,
    system_role: str = "You are a helpful assistant."
) -> LLM:

    print(f"--- Loading model: {model_dir} ---")

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        trust_remote_code=True,
    )

    if torch_dtype == "auto":
        if torch.cuda.is_available() and torch.cuda.get_device_properties(0).major >= 8:
            dtype = torch.bfloat16
        else:
            dtype = torch.float16
    else:
        dtype = torch_dtype

    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=dtype,
        device_map=device,
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )

    model.eval()

    print("--- Loading model finish ---")

    return Qwen3LLM(
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        enable_thinking=enable_thinking,
        system_role=system_role
    )


if __name__ == "__main__":
    llm = get_llm("/path/to/qwen3-14b")
    prompt = "你好，agent"
    print(llm.invoke(prompt))
