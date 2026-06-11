from .base import Provider
from .deepseek import DeepSeekProvider
from .doubao import DoubaoProvider
from .qwen import QwenProvider

_REGISTRY: dict[str, type[Provider]] = {
    "deepseek": DeepSeekProvider,
    "doubao":   DoubaoProvider,
    "qwen":     QwenProvider,
}


def get_provider(name: str, **kwargs) -> Provider:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Available: {list(_REGISTRY)}")
    return cls(**kwargs)


__all__ = ["Provider", "DeepSeekProvider", "DoubaoProvider", "QwenProvider", "get_provider"]
