import os
import requests
from .base import Provider, build_messages
from config.settings import config

_PRICE_IN  = 0.14 / 1_000_000   # $0.14 / 1M input tokens  (deepseek-chat)
_PRICE_OUT = 0.28 / 1_000_000   # $0.28 / 1M output tokens


class DeepSeekProvider(Provider):
    @property
    def name(self) -> str:
        return "deepseek"

    def __init__(self, api_key: str | None = None, default_model: str = None):
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._default_model = default_model or config.get("DEEPSEEK_MODEL", "deepseek-chat")
        self._api_base_url = config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    def _call(self, prompt: str, history: list[str], params: dict) -> dict:
        model = params.get("model", self._default_model)
        messages = build_messages(history, prompt)
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
        }
        
        api_url = f"{self._api_base_url.rstrip('/')}/chat/completions"
        
        resp = requests.post(
            api_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        in_tok  = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        return {
            "text": data["choices"][0]["message"]["content"],
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
            "cost_estimate": self._estimate_cost(in_tok, out_tok),
        }

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return round(input_tokens * _PRICE_IN + output_tokens * _PRICE_OUT, 6)
