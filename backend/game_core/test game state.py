"""
game_core/test_game_state.py

快速验证 GameState 各方法是否按预期工作。
运行方式：python -m pytest game_core/test_game_state.py -v
或直接：python game_core/test_game_state.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from game_state import GameState

# ── 测试数据 ──────────────────────────────────────────────────────────────────

CHARACTERS = [
{"name": "林晓", "persona": "聪明勇敢的侦探", "goal": "查明真相"},
{"name": "陈默", "persona": "神秘的信息掮客", "goal": "保护秘密"},
]

BACKGROUND = "2087年，霓虹城。一场针对AI公司的阴谋正在悄然展开。"

# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def make_provider_output(text: str) -> dict:
 return {'text': text, 'usage': {'prompt_tokens': 100, 'completion_tokens': 50}}

# ── 测试用例 ──────────────────────────────────────────────────────────────────

def test_init():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)


 assert state.level == 1
 assert state.score == 0.0
 assert state.memory_enabled is True
 assert len(state._turns) == 0
 print("✅ test_init passed")

def test_add_turn():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)

 state.add_turn(
 prompt="林晓发现了一封加密邮件。",
 provider_output=make_provider_output('{"actions": [{"character": "林晓", "action":"打开邮件"}]}'),
 metadata={"latency": 0.8},
 )
 assert len(state._turns) == 1
 assert state._turns[0].chapter == 1
 print("✅ test_add_turn passed")

def test_memory_window():
 state = GameState(memory_window_size=3)
 for i in range(6):
  state.add_turn(f"第{i+1}段故事", make_provider_output(f"回复{i+1}"))
  window = state._get_windowed_turns()
  assert len(window) == 3
  assert window[0].prompt == "第4段故事"
  print("✅ test_memory_window passed")

def test_get_summary():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)
 # 空状态
 summary = state.get_summary()
 assert "尚未开始" in summary

 state.add_turn("故事开始了", make_provider_output("角色开始行动"))
 summary = state.get_summary()
 assert "第 1 章" in summary
 assert "故事开始了" in summary
 print("✅ test_get_summary passed")

def test_to_context_structure():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)
 state.add_turn("林晓走进了废弃仓库。", make_provider_output("林晓拔出手电筒，四处查看。"))

 ctx = state.to_context()

 assert "【系统设定】" in ctx
 assert "【登场角色】" in ctx
 assert "【历史对话记录】" in ctx
 assert "【任务说明】" in ctx
 assert "```json" in ctx
 assert "actions" in ctx
 print("✅ test_to_context_structure passed")

def test_to_context_memory_disabled():
 state = GameState(characters=CHARACTERS, memory_enabled=False)
 state.add_turn("测试输入", make_provider_output("测试回复"))
 ctx = state.to_context()
 assert "历史对话记录" not in ctx
 print("✅ test_to_context_memory_disabled passed")

def test_to_context_extra_history():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)
 extra = [
 {"role": "user", "content": "来自MemoryStore的历史输入"},
 {"role": "assistant", "content": "来自MemoryStore的历史回复"},
 ]
 ctx = state.to_context(extra_history=extra)
 assert "来自MemoryStore的历史输入" in ctx
 print("✅ test_to_context_extra_history passed")

def test_advance_chapter():
 state = GameState()
 state.advance_chapter()
 assert state.level == 2
 state.advance_chapter(3)
 assert state.level == 5
 state.advance_chapter(-10)  # 不能低于1
 assert state.level == 1
 print("✅ test_advance_chapter passed")

def test_update_score():
 state = GameState()
 state.update_score(30)
 assert state.score == 30.0
 state.update_score(80)   # 超过100则截断
 assert state.score == 100.0
 state.update_score(-200) # 不能低于0
 assert state.score == 0.0
 print("✅ test_update_score passed")

def test_reset():
 state = GameState(characters=CHARACTERS)
 state.add_turn("输入", make_provider_output("回复"))
 state.advance_chapter(2)
 state.update_score(50)
 state.reset()
 assert state.level == 1
 assert state.score == 0.0
 assert len(state._turns) == 0
 assert state.characters == CHARACTERS  # 角色设定保留
 print("✅ test_reset passed")

def test_to_dict():
 state = GameState(characters=CHARACTERS, story_background=BACKGROUND)
 d = state.to_dict()
 assert "session_id" in d
 assert d["level"] == 1
 assert d["turn_count"] == 0
 print("✅ test_to_dict passed")

# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
 tests = [
  test_init,
  test_add_turn,
  test_memory_window,
  test_get_summary,
  test_to_context_structure,
  test_to_context_memory_disabled,
  test_to_context_extra_history,
  test_advance_chapter,
  test_update_score,
  test_reset,
  test_to_dict,
 ]
 print(f"\n运行 {len(tests)} 个测试…\n")

 for t in tests:
  t()
 print(f"\n🎉 全部测试通过！")