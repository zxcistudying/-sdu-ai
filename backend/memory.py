from __future__ import annotations

import datetime
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Any


class SessionNotFoundError(ValueError):
    """自定义异常：会话不存在时抛出。"""


@dataclass
class MemoryEntry:
    """对话记忆条目，禁止外部直接实例化，仅供 MemoryStore 生成。"""

    session_id: str
    timestamp: str
    user_input: str
    model_reply: str
    tokens: int
    provider: str
    model: str
    metadata: Optional[Dict[str, Any]] = field(default=None)

    _allow_instantiate: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self._allow_instantiate:
            raise RuntimeError(
                "MemoryEntry 禁止直接实例化，请使用 MemoryStore.add_turn 方式创建。"
            )

    @classmethod
    def _create(cls, *, session_id: str, timestamp: str, user_input: str, model_reply: str, tokens: int,
                provider: str, model: str, metadata: Optional[Dict[str, Any]] = None) -> "MemoryEntry":
        # 内部工厂方法，仅供 MemoryStore 使用
        instance = cls.__new__(cls)
        # 直接绕过 dataclass生成的 __init__, 手动赋值并设置允许标志
        object.__setattr__(instance, "_allow_instantiate", True)
        instance.session_id = session_id
        instance.timestamp = timestamp
        instance.user_input = user_input
        instance.model_reply = model_reply
        instance.tokens = tokens
        instance.provider = provider
        instance.model = model
        instance.metadata = metadata
        # 禁止外部再次实例化
        object.__setattr__(instance, "_allow_instantiate", False)
        return instance


class MemoryStore:
    """内存会话记忆存储，支持线程安全的会话历史管理与摘要。"""

    def __init__(self, memory_window_size: int = 5) -> None:
        """初始化 MemoryStore。

        Args:
            memory_window_size (int): 每个会话保留的最大历史条数，必须 >=1。

        Raises:
            ValueError: 当 memory_window_size < 1 时抛出。
        """
        if memory_window_size < 1:
            raise ValueError("memory_window_size 必须大于等于 1")

        self._memory_window_size: int = memory_window_size
        self._store: Dict[str, Deque[MemoryEntry]] = {}
        self._lock = threading.RLock()

    def create_session(self) -> str:
        """创建一个全局唯一的 session_id，并注册空会话存储。"""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._store.setdefault(session_id, deque())
        return session_id

    def add_turn(self, session_id: str, user_input: str, model_reply: str,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """向指定会话追加一条对话记录，并触发滑动窗口裁剪。"""
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id 必须为非空字符串")

        timestamp = datetime.datetime.utcnow().isoformat()
        tokens = len(user_input) + len(model_reply)

        provider = "unknown"
        model = "unknown"
        if metadata:
            if isinstance(metadata, dict):
                provider = metadata.get("provider", provider)
                model = metadata.get("model", model)

        entry = MemoryEntry._create(
            session_id=session_id,
            timestamp=timestamp,
            user_input=user_input,
            model_reply=model_reply,
            tokens=tokens,
            provider=provider,
            model=model,
            metadata=metadata,
        )

        with self._lock:
            session_queue = self._store.setdefault(session_id, deque())
            session_queue.append(entry)
            # 滑动窗口自动裁剪，保留最近 N 条
            while len(session_queue) > self._memory_window_size:
                session_queue.popleft()

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[MemoryEntry]:
        """获取指定会话历史，按时间升序返回全部或最近 limit 条记录。"""
        with self._lock:
            session_queue = self._store.get(session_id)
            if not session_queue:
                return []
            if limit is None:
                return list(session_queue)
            if limit < 1:
                raise ValueError("limit 必须大于等于 1 或 None")
            if limit >= len(session_queue):
                return list(session_queue)
            return list(session_queue)[-limit:]

    def prune_history(self, session_id: str, limit: int) -> None:
        """仅保留指定会话最近 limit 条记录，删除更早记录。"""
        if limit < 1:
            raise ValueError("limit 必须大于等于 1")

        with self._lock:
            if session_id not in self._store:
                raise SessionNotFoundError(f"会话 '{session_id}' 不存在")
            queue = self._store[session_id]
            if len(queue) <= limit:
                return
            while len(queue) > limit:
                queue.popleft()

    def summarize_history(self, session_id: str, limit: Optional[int] = None) -> str:
        """将指定会话最近 limit 条历史压缩为纯文本摘要。"""
        history = self.get_history(session_id, limit)
        if not history:
            return ""

        lines: List[str] = []
        for entry in history:
            lines.append(f"User: {entry.user_input}")
            lines.append(f"Assistant: {entry.model_reply}")

        # TODO: 可在此扩展为调用外部摘要模型
        return "\n".join(lines)
