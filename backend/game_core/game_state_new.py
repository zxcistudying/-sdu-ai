"""
game_core/game_state.py

职责：

- 维护故事章节（level）、评分（score）、记忆开关、记忆窗口
- 拼接发给 LLM 的 prompt 上下文（to_context）
- 提供当前进度摘要（get_summary）
- 与 MemoryStore 解耦：GameState 只持有轻量的 turn 列表，
  不直接依赖 memory/ 模块，由 API 层负责两者协调。
"""
from __future__ import annotations

from time import time
import uuid
from typing import Any, Optional

# ── 默认常量（未接入 config/ 前的回退值） ─────────────────────────────────────

DEFAULT_MEMORY_WINDOW: int = 5       # 保留最近几轮对话作为记忆窗口
DEFAULT_LEVEL: int = 1               # 初始章节
DEFAULT_SCORE: float = 0.0           # 初始评分

# ─────────────────────────────────────────────────────────────────────────────

# 数据类：单轮对话记录

# ─────────────────────────────────────────────────────────────────────────────

class TurnRecord:
    def __init__(self, turn_id, timestamp, prompt, reply, chapter, metadata=None):
        self.turn_id = turn_id
        self.timestamp = timestamp
        self.prompt = prompt
        self.reply = reply
        self.chapter = chapter
        self.metadata = metadata or {}

# ─────────────────────────────────────────────────────────────────────────────

# 核心类：GameState

# ─────────────────────────────────────────────────────────────────────────────

class GameState:

    """
     维护一次多角色故事推演的完整运行时状态
     ```
     属性
     ----
     session_id        : 本次会话唯一标识（由外部传入或自动生成）
     level             : 当前故事章节编号（从 1 开始）
     score: 角色扮演质量评分（0.0~ 100.0）
     memory_enabled    : 是否将历史上下文注入 prompt
     memory_window_size: 记忆窗口大小（最近 N 轮）
     characters        : 本次故事中的角色列表（由前端初始化时传入）
     story_background  : 故事背景/世界观描述（固定不变）
     turns            : 内部维护的轮次列表（私有，外部用方法访问）
"""
    def __init__(
        self,
        session_id= None,
        level = DEFAULT_LEVEL,
        score = DEFAULT_SCORE,
        memory_enabled = True,
        memory_window_size = DEFAULT_MEMORY_WINDOW,
        characters = None,
        story_background = "",
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.level = level
        self.score = score
        self.memory_enabled = memory_enabled
        self.memory_window_size = memory_window_size
        self.characters = characters or []
        self.story_background = story_background
        self._turns = []

# ── 公开方法 ──────────────────────────────────────────────────────────────

    def add_turn(
        self,
        prompt: str,
        provider_output: dict[str, Any],
        metadata: Optional[dict] = None,
    ) -> None:
        """
    记录一轮交互。

    参数
    ----
    prompt          : 本轮用户输入（故事片段）
    provider_output : Provider.run() 的返回字典，至少含 'text' 字段
    metadata        : 可选附加信息（如 token 用量、延迟等）
    """
        reply = provider_output.get("text", "")
        record = TurnRecord(
            turn_id=str(uuid.uuid4()),
            timestamp=time(),
            prompt=prompt,
            reply=reply,
            chapter=self.level,
            metadata=metadata or {},
        )

        self._turns.append(record)

    def get_summary(self) -> str:
        """
    返回当前游戏状态的文字摘要（纯字符串拼接）。

    未来扩展：若需要 LLM 压缩摘要，可在此处注入 summarizer 回调：
        if self._summarizer:
            return self._summarizer(self._turns)
    """
        if not self._turns:
            return f"[第{self.level}章] 故事尚未开始。"

        lines = [
            f"=== 故事进度摘要 ===",
            f"章节：第 {self.level} 章  |  评分：{self.score:.1f}  |  已进行轮次：{len(self._turns)}",
            f"会话ID：{self.session_id}",
            "",
        ]
        for i, t in enumerate(self._turns[-self.memory_window_size:], 1):
            lines.append(f"[轮次 {i}]")
            lines.append(f"  输入：{t.prompt[:120]}{'…' if len(t.prompt) > 120 else ''}")
            lines.append(f"  回复：{t.reply[:120]}{'…' if len(t.reply) > 120 else ''}")
        return "\n".join(lines)

    def to_context(self, extra_history: Optional[list[dict]] = None) -> str | None:
        """
    拼接发给 LLM 的完整 prompt 上下文。

    结构
    ----
    [系统角色设定]
      → 故事背景
      → 角色列表（姓名 + 性格描述）
    [历史对话窗口]（memory_enabled=True 时注入）
      → 最近 N 轮的 用户输入 / 角色回复
    [当前任务说明]
      → 输出格式要求

    参数
    ----
    extra_history : 由 API 层从 MemoryStore 取出并传入的补充历史，
                    格式为 [{"role": "user"/"assistant", "content": "..."}]
                    若为 None，则只使用 GameState 内部的 _turns。
    """
        parts: list[str] = ["## 【系统设定】"]

        # ── 1. 系统：故事世界观 ───────────────────────────────────────────────
        if self.story_background:
            parts.append(f"故事背景：{self.story_background}")
        parts.append(f"当前章节：第 {self.level} 章")
        parts.append("")

    # ── 2. 角色列表 ───────────────────────────────────────────────────────
        if self.characters:
            parts.append("## 【登场角色】")
            for c in self.characters:
                name = c.get("name", "未知")
                persona = c.get("persona", "")
                goal = c.get("goal", "")
                line = f"- {name}"
                if persona:
                    line += f"：{persona}"
                if goal:
                    line += f"（目标：{goal}）"
                parts.append(line)
            parts.append("")

    # ── 3. 历史对话窗口 ───────────────────────────────────────────────────
        if self.memory_enabled:
            history_turns = self._get_windowed_turns()

            # 优先使用 extra_history（来自 MemoryStore），否则用内部 turns
            if extra_history:
                history_turns = extra_history[-self.memory_window_size:]
                parts.append("## 【历史对话记录】")
                for entry in history_turns:
                    role_label = "用户" if entry.get("role") == "user" else "助手"
                    parts.append(f"[{role_label}]：{entry.get('content', '')}")
            elif history_turns:
                parts.append("## 【历史对话记录】")
                for t in history_turns:
                    parts.append(f"[用户]：{t.prompt}")
                    parts.append(f"[助手]：{t.reply}")
            parts.append("")

    # ── 4. 输出格式要求 ───────────────────────────────────────────────────
        parts.append("## 【任务说明】")
        parts.append(
            "你正在扮演童话故事中的一个角色，与【玩家/用户】进行对话。"
        )
        parts.append(
            "【重要】与你对话的是【玩家/用户】，不是故事中的其他角色！"
        )
        parts.append(
            "请根据以上背景和对话历史，以角色身份进行自然对话。"
        )
        parts.append("")
        parts.append("请直接输出角色的对话内容，只需要一句符合角色人设的话。")
        parts.append("不要使用 JSON 格式或其他结构化输出。")

        return "\n".join(parts)

    def advance_chapter(self, step: int = 1) -> None:
        """推进故事章节。"""
        self.level = max(1, self.level + step)

    def update_score(self, delta: float) -> None:
        """更新评分，限制在 [0, 100] 范围内。"""
        self.score = max(0.0, min(100.0, self.score + delta))

    def reset(self) -> None:
        """重置当前会话状态（保留 session_id 和角色设定）。"""
        self.level = DEFAULT_LEVEL
        self.score = DEFAULT_SCORE
        self._turns.clear()

    def to_dict(self) -> dict[str, Any]:
        """将当前状态序列化为字典，便于 API 层返回或调试。"""
        return {
            "session_id": self.session_id,
            "level": self.level,
            "score": self.score,
            "memory_enabled": self.memory_enabled,
            "memory_window_size": self.memory_window_size,
            "turn_count": len(self._turns),
            "characters": self.characters,
        }

# ── 私有辅助 ──────────────────────────────────────────────────────────────

    def _get_windowed_turns(self) -> list[TurnRecord]:
            """返回最近 memory_window_size 条轮次记录。"""
            return self._turns[-self.memory_window_size:]

    def __repr__(self) -> str:
            return (
                f"GameState(session={self.session_id[:8]}…, "
                f"chapter={self.level}, score={self.score:.1f}, "
                f"turns={len(self._turns)})"
            )