from abc import ABC, abstractmethod
from typing import Optional
import time


class Provider(ABC):
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds

    def run(self, prompt: str, history: list[str], params: dict) -> dict:
        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start = time.monotonic()
                result = self._call(prompt, history, params)
                result["latency"] = round(time.monotonic() - start, 3)
                result["success"] = True
                return result
            except Exception as e:
                last_err = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BASE_DELAY * (2 ** attempt))
        return {"success": False, "error": str(last_err), "text": "", "usage": {}, "latency": 0, "cost_estimate": 0.0}

    @abstractmethod
    def _call(self, prompt: str, history: list[str], params: dict) -> dict:
        """Make the actual API call. Returns dict with text, usage, cost_estimate."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Override per provider with actual pricing."""
        return 0.0


def build_messages(history: list[str], prompt: str) -> list[dict]:
    """Interleave history [user, assistant, ...] then append current prompt."""
    messages = []
    for i, text in enumerate(history):
        messages.append({"role": "user" if i % 2 == 0 else "assistant", "content": text})
    messages.append({"role": "user", "content": prompt})
    return messages
