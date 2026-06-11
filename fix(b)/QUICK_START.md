# 快速启动指南

## 🚀 5分钟快速体验剧情控制系统

### 第一步：启动后端

```bash
cd d:\town5.1\town5.1\backend
python app.py
```

你会看到：
```
==================================================
童话镇多智能体系统
==================================================
游戏状态管理器已初始化
剧情导演已初始化
记忆存储已初始化

启动Flask服务器...
后端地址: http://localhost:5000
==================================================
```

### 第二步：测试 API（使用 curl 或 Postman）

#### 测试 1：执行剧情回合

```bash
curl -X POST http://localhost:5000/api/execute-turn \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"小红帽走到森林深处，遇到了大灰狼\", \"scene\": \"森林\"}"
```

**预期响应**：
```json
{
  "success": true,
  "session_id": "abc-123...",
  "director_output": {
    "turn_id": 1,
    "narrative": "场景：森林\n小红帽走向森林深处。小红帽遇到了大灰狼。",
    "character_action": {...},
    "dialogue": {...},
    "world_state_update": {...},
    "next_options": [...]
  }
}
```

#### 测试 2：获取游戏状态

```bash
curl http://localhost:5000/api/game-state
```

#### 测试 3：重置游戏

```bash
curl -X POST http://localhost:5000/api/reset-game
```

### 第三步：运行单元测试

```bash
cd d:\town5.1\town5.1\backend\game_core
python test_director.py
```

**预期输出**：
```
============================================================
测试剧情导演系统
============================================================

✓ 游戏状态初始化成功
  角色数量: 2
✓ 剧情导演创建成功

✓ 准备测试 4 个动作

============================================================
导演输出结果:
============================================================

📖 回合ID: 1

📝 旁白:
   场景：森林
   小红帽走向森林深处。小红帽遇到了大灰狼。

🎭 主要动作:
   角色: 小红帽
   动画: walk
   表情: surprised
   目标: 森林深处

💬 对话:
   大灰狼: "你好啊，小姑娘！"
   情绪: friendly

🌍 状态变更:
   1. position_change: 小红帽
   2. encounter: 小红帽

🔘 后续选项:
   - 继续对话
   - 逃跑

📊 元数据:
   总动作数: 4
   有效动作: 4
   已执行: 4

============================================================
✅ 测试完成！
============================================================

所有测试通过！✨
```

---

## 🎨 前端快速集成（简化版）

如果你只想快速测试，可以在 `frontend/index.html` 中添加以下代码：

### HTML 部分

在 `<body>` 中添加：

```html
<div id="game-container" style="max-width: 800px; margin: 0 auto; padding: 20px;">
  <h1>童话镇剧情系统</h1>
  
  <!-- 输入框 -->
  <div style="margin: 20px 0;">
    <input type="text" id="story-input" placeholder="输入剧情..." 
           style="width: 70%; padding: 10px;" />
    <button onclick="sendStory()" style="padding: 10px 20px;">发送</button>
  </div>
  
  <!-- 输出区域 -->
  <div id="output" style="border: 1px solid #ccc; padding: 15px; min-height: 200px;">
    <p style="color: #999;">等待输入...</p>
  </div>
</div>

<script src="quick-test.js"></script>
```

### JavaScript 部分

创建 `frontend/quick-test.js`：

```javascript
let sessionId = null;

async function sendStory() {
  const input = document.getElementById('story-input');
  const output = document.getElementById('output');
  const text = input.value.trim();
  
  if (!text) return;
  
  output.innerHTML = '<p style="color: blue;">处理中...</p>';
  
  try {
    const response = await fetch('http://localhost:5000/api/execute-turn', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        text: text,
        session_id: sessionId
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      sessionId = data.session_id;
      displayResult(data.director_output);
    } else {
      output.innerHTML = `<p style="color: red;">错误: ${data.error}</p>`;
    }
  } catch (error) {
    output.innerHTML = `<p style="color: red;">网络错误: ${error.message}</p>`;
  }
  
  input.value = '';
}

function displayResult(output) {
  const outputDiv = document.getElementById('output');
  
  let html = `
    <div style="margin-bottom: 15px;">
      <strong style="color: green;">回合 #${output.turn_id}</strong>
    </div>
  `;
  
  // 旁白
  if (output.narrative) {
    html += `
      <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px;">
        <strong>📖 旁白:</strong><br/>
        ${output.narrative}
      </div>
    `;
  }
  
  // 角色动作
  if (output.character_action) {
    const action = output.character_action;
    html += `
      <div style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px;">
        <strong>🎭 动作:</strong><br/>
        角色: ${action.name}<br/>
        动画: ${action.animation}<br/>
        表情: ${action.expression}
      </div>
    `;
  }
  
  // 对话
  if (output.dialogue) {
    const dialogue = output.dialogue;
    html += `
      <div style="background: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 5px;">
        <strong>💬 对话:</strong><br/>
        <strong>${dialogue.speaker}:</strong> "${dialogue.text}"<br/>
        <small>情绪: ${dialogue.emotion}</small>
      </div>
    `;
  }
  
  // 选项
  if (output.next_options && output.next_options.length > 0) {
    html += '<div style="margin: 10px 0;"><strong>🔘 选项:</strong><br/>';
    output.next_options.forEach(opt => {
      html += `<button onclick="selectOption('${opt.action_input}')" 
                       style="margin: 5px; padding: 8px 15px; cursor: pointer;">
                ${opt.label}
               </button>`;
    });
    html += '</div>';
  }
  
  outputDiv.innerHTML = html;
}

function selectOption(actionInput) {
  document.getElementById('story-input').value = actionInput;
  sendStory();
}

// 支持回车键发送
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('story-input');
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      sendStory();
    }
  });
});
```

### 启动前端

直接用浏览器打开 `frontend/index.html`，即可开始测试！

---

## 📋 测试用例

尝试以下输入，观察不同的输出：

1. **简单移动**
   ```
   小红帽走到门口
   ```

2. **对话场景**
   ```
   小红帽说：你好，大灰狼！
   ```

3. **相遇事件**
   ```
   小红帽在森林里遇到了猎人
   ```

4. **复杂场景**
   ```
   小红帽走进奶奶的房子，看到床上躺着大灰狼，惊讶地说：你的耳朵怎么这么大？
   ```

---

## 🔍 调试技巧

### 查看后端日志

后端会输出详细的日志信息：

```
收到文本: 小红帽走到森林深处，遇到了大灰狼
AI提取动作成功: 3个
开始剧情导演处理，共 3 个动作
第 1 回合导演完成
已添加导演输出到响应
```

### 浏览器控制台

打开浏览器开发者工具（F12），在 Console 中可以看到：

- 网络请求详情
- 响应数据结构
- 任何 JavaScript 错误

### 使用 Postman

如果使用 Postman 测试，建议保存以下 Collection：

1. **Execute Turn**
   - Method: POST
   - URL: `http://localhost:5000/api/execute-turn`
   - Body (JSON):
     ```json
     {
       "text": "测试文本",
       "scene": "森林"
     }
     ```

2. **Get Game State**
   - Method: GET
   - URL: `http://localhost:5000/api/game-state`

3. **Reset Game**
   - Method: POST
   - URL: `http://localhost:5000/api/reset-game`

---

## ❓ 常见问题

**Q: 后端启动失败？**
A: 检查是否安装了依赖：`pip install flask flask-cors`

**Q: AI 动作提取失败？**
A: 检查 `backend/config/settings.py` 中的 API Key 是否配置正确。如果没有配置，系统会自动使用规则兜底。

**Q: 前端无法连接后端？**
A: 确保后端正在运行（`python app.py`），并且 CORS 已正确配置。

**Q: 返回的动作很少？**
A: 这是正常的。系统会过滤掉无效动作，只保留合法的动作序列。

---

## 🎯 下一步

1. ✅ 完成后端测试
2. ✅ 实现完整的前端界面（参考 `INTEGRATION_GUIDE.md`）
3. ✅ 添加更多角色和场景
4. ✅ 优化动画效果
5. ✅ 部署到生产环境

祝你开发愉快！🚀