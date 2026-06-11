# -*- coding: utf-8 -*-
import re

file_path = r'd:\town4.19\town4.19\backend\game_core\game_state.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section to replace
old_text = '''        parts.append("## 【任务说明】")
        parts.append(
            "你是一个多角色故事推演引擎。"
            "请根据以上背景、角色设定和历史对话，"
            "为每个登场角色生成下一步的行动指令。"
        )
        parts.append("")
        parts.append("请严格按照以下 JSON 格式输出，不要包含任何额外文字：")
        parts.append(
        """```json
```

{
"chapter": <当前章节编号>,
"actions": [
{
"character": "<角色名>",
"action": "<动作描述，简洁明了>",
"dialogue": "<该角色说的话，若无对话则为空字符串>",
"emotion": "<当前情绪状态，如：平静/愤怒/悲伤/惊讶/喜悦>",
"target": "<动作对象，若无则为空字符串>"
}
],
"story_hint": "<对下一段剧情走向的简短预测，1句话>"
}

```"""
        )'''

new_text = '''        parts.append("## 【任务说明】")
        parts.append(
            "你是一个童话故事中的角色，请根据以上背景和对话历史，"
            "以角色身份进行自然对话。"
        )
        parts.append("")
        parts.append("请直接输出角色的对话内容，只需要一句符合角色人设的话。")
        parts.append("不要使用 JSON 格式或其他结构化输出。")'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Success!')
else:
    print('Pattern not found')
    # Debug: show what we have around line 195
    lines = content.split('\n')
    for i, line in enumerate(lines[190:210], start=191):
        print(f'{i}: {repr(line)}')