# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

file_path = r'd:\town4.19\town4.19\backend\game_core\game_state.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start line (line 195: parts.append('## 【任务说明】'))
# and end line (line 221: the closing ))

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is the start of the section we want to replace
    if i == 194 and '## 【任务说明】' in line:
        # Add the new content
        new_lines.append(line)  # parts.append("## 【任务说明】")
        i += 1
        # Skip old content until we reach the return statement
        while i < len(lines):
            if 'return' in lines[i] and 'join' in lines[i]:
                break
            i += 1
        # Now add new task instructions
        new_lines.append('        parts.append(\n')
        new_lines.append('            "你是一个童话故事中的角色，请根据以上背景和对话历史，"\n')
        new_lines.append('            "以角色身份进行自然对话。"\n')
        new_lines.append('        )\n')
        new_lines.append('        parts.append("")\n')
        new_lines.append('        parts.append("请直接输出角色的对话内容，只需要一句符合角色人设的话。")\n')
        new_lines.append('        parts.append("不要使用 JSON 格式或其他结构化输出。")\n')
    else:
        new_lines.append(line)
        i += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Done!')