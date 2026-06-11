import os
import requests
from .base import Provider, build_messages

_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
_PRICE_IN  = 0.8 / 1_000_000    # ¥0.8 / 1M input tokens  (doubao-pro-32k)
_PRICE_OUT = 2.0 / 1_000_000    # ¥2.0 / 1M output tokens


class DoubaoProvider(Provider):
    @property
    def name(self) -> str:
        return "doubao"

    def __init__(self, api_key: str | None = None, default_model: str = "doubao-pro-32k"):
        self._api_key = api_key or os.environ["DOUBAO_API_KEY"]
        self._default_model = default_model

    def _call(self, prompt: str, history: list[str], params: dict) -> dict:
        payload = {
            "model": params.get("model", self._default_model),
            "messages": build_messages(history, prompt),
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
        }
        resp = requests.post(
            _API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
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
