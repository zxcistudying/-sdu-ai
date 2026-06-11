"""
童话镇多智能体系统 - Flask后端
"""
import os
import sys
import json
import random
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Optional, List, Dict, Any
import sys
import logging

# ==================== 动作协议定义 ====================
# 统一动作格式，供AI输出和前端播放使用

ACTION_TYPES = {
    'narration': '叙述/旁白',
    'enter_scene': '进入场景',
    'appear': '角色出现',
    'move': '移动',
    'meet': '相遇',
    'speak': '对话',
    'think': '思考',
    'emotion': '情绪表达',
    'action': '动作行为',
    'exit_scene': '退出场景'
}

def create_action(
    action_type: str,
    character: str = None,
    target: str = None,
    content: str = None,
    position: Dict[str, int] = None,
    emotion: str = None
) -> Dict[str, Any]:
    """创建标准动作格式"""
    action = {'type': action_type}
    if character:
        action['character'] = character
    if target:
        action['target'] = target
    if content:
        action['content'] = content
    if position:
        action['position'] = position
    if emotion:
        action['emotion'] = emotion
    return action

def validate_actions(actions: Any) -> bool:
    """验证动作格式是否合法"""
    if not isinstance(actions, list):
        logger.warning(f"动作验证失败: 不是数组, 类型={type(actions)}")
        return False
    if len(actions) == 0:
        logger.warning("动作验证失败: 空数组")
        return False

    valid_types = set(ACTION_TYPES.keys())
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            logger.warning(f"动作验证失败: 第{i}项不是字典, 类型={type(action)}")
            return False
        if 'type' not in action:
            logger.warning(f"动作验证失败: 第{i}项缺少type字段")
            return False
        if action['type'] not in valid_types:
            logger.warning(f"动作验证失败: 第{i}项type不合法, value={action['type']}")
            return False
        # 可选字段做类型检查
        for field in ['character', 'target', 'content', 'emotion']:
            if field in action and not isinstance(action[field], str):
                logger.warning(f"动作验证失败: 第{i}项{field}不是字符串")
                return False

    logger.info(f"动作验证通过: {len(actions)}个动作")
    return True

# 配置日志输出
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(__file__))

try:
    from config.settings import config
    from provider.deepseek import DeepSeekProvider
    from game_core.game_state import GameState
    from game_core.director import PlotDirector
    from game_core.story_segmenter import StorySegmenter, segment_story_auto
    from memory import MemoryStore
    from prompt_generator import generate_map_prompt, generate_character_prompt, generate_all_prompts
    from image_generator import create_image_generator, generate_map_image, generate_character_image
    from asset_manager import create_asset_manager, save_map_asset, save_character_asset, save_all_assets
    from doubao_image_generator import (
        create_doubao_image_generator,
        generate_pixel_background,
        generate_pixel_character
    )
except ImportError as e:
    print(f"警告: 无法导入配置模块 - {e}")
    config = None
    GameState = None
    PlotDirector = None
    StorySegmenter = None
    segment_story_auto = None
    MemoryStore = None
    generate_map_prompt = None
    generate_character_prompt = None
    generate_all_prompts = None
    create_image_generator = None
    generate_map_image = None
    generate_character_image = None
    create_asset_manager = None
    save_map_asset = None
    save_character_asset = None
    save_all_assets = None
    create_doubao_image_generator = None
    generate_pixel_background = None
    generate_pixel_character = None

app = Flask(__name__)

# 配置CORS，允许前端访问
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# ==================== 数据存储 ====================
class DataStore:
    """内存数据存储"""
    def __init__(self):
        self.novels = {}
        self.characters = {}
        self.scenes = {}
        self.dialogues = {}
        self.novel_id_counter = 1
        self.character_id_counter = 1
        self.scene_id_counter = 1

    def add_character(self, char_data: dict) -> dict:
        """添加角色"""
        char_id = self.character_id_counter
        char_data['id'] = char_id
        # 同时添加字符串ID以兼容前端
        char_data['id_str'] = f"char-{char_id}"
        self.characters[char_id] = char_data
        self.character_id_counter += 1
        return char_data

    def get_character(self, char_id: int) -> Optional[dict]:
        """获取角色"""
        return self.characters.get(char_id)

    def update_character(self, char_id: int, updates: dict) -> Optional[dict]:
        """更新角色"""
        if char_id in self.characters:
            self.characters[char_id].update(updates)
            return self.characters[char_id]
        return None

    def get_all_characters(self) -> list:
        """获取所有角色"""
        result = []
        for char in self.characters.values():
            # 添加字符串ID兼容前端
            char_copy = char.copy()
            if 'id_str' not in char_copy:
                char_copy['id_str'] = f"char-{char_copy['id']}"
            result.append(char_copy)
        return result

    def add_dialogue(self, char_id: int, role: str, content: str) -> dict:
        """添加对话记录"""
        if char_id not in self.dialogues:
            self.dialogues[char_id] = []
        dialogue = {
            'role': role,
            'content': content,
            'timestamp': self._get_timestamp()
        }
        self.dialogues[char_id].append(dialogue)
        return dialogue

    def get_dialogues(self, char_id: int, limit: int = 20) -> list:
        """获取对话历史"""
        dialogues = self.dialogues.get(char_id, [])
        return dialogues[-limit:]

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 全局数据存储
data_store = DataStore()

# LLM提供者
llm_provider = None
game_state = None
plot_director = None
memory_store = None

def get_memory_store():
    """获取记忆存储"""
    global memory_store
    if memory_store is None and MemoryStore:
        memory_store = MemoryStore(memory_window_size=5)
        print("记忆存储已初始化")
    return memory_store

def get_llm_provider():
    """获取LLM提供者"""
    global llm_provider
    if llm_provider is None and config:
        try:
            api_key = config.get('DEEPSEEK_API_KEY', '')
            if api_key:
                llm_provider = DeepSeekProvider(api_key=api_key)
                print("LLM提供者已初始化 (DeepSeek)")
        except Exception as e:
            print(f"初始化LLM失败: {e}")
    return llm_provider

def get_game_state():
    """获取游戏状态管理器"""
    global game_state
    if game_state is None and GameState:
        game_state = GameState(
            story_background="童话镇是一个充满魔法和奇遇的地方，这里住着许多经典童话故事中的人物。",
            characters=[]
        )
        print("游戏状态管理器已初始化")
    return game_state

def get_plot_director():
    """获取剧情导演"""
    global plot_director
    if plot_director is None and PlotDirector:
        gs = get_game_state()
        if gs:
            plot_director = PlotDirector(gs)
            print("剧情导演已初始化")
    return plot_director


# ==================== 角色识别 ====================

def extract_characters_by_ai(text: str, provider) -> list:
    """使用AI从文本中提取角色"""
    if not provider:
        logger.warning("AI角色提取失败: 无provider")
        return None

    prompt = f"""请分析以下故事文本，提取其中的角色信息。

## 任务要求：
1. 识别所有出现的角色
2. 确定每个角色的类型（主角、反派、配角）
3. 简要描述每个角色

## 输出格式：
请输出JSON数组，每个角色包含以下字段：
- name: 角色名称
- role: 角色类型（主角/反派/配角）
- description: 角色描述

## 输出示例：
[
  {{"name": "小红帽", "role": "主角", "description": "戴着红色帽子的小女孩"}},
  {{"name": "大灰狼", "role": "反派", "description": "森林里的坏蛋"}}
]

## 故事文本：
{text}

请直接输出JSON数组，不要包含任何其他文字。"""

    try:
        logger.info("开始AI角色提取...")
        result = provider.run(
            prompt=prompt,
            history=[],
            params={'temperature': 0.2, 'max_tokens': 500}
        )

        if not result.get('success'):
            logger.warning("AI角色提取失败: provider返回失败")
            return None

        text_response = result['text']
        logger.info(f"AI角色提取返回内容长度: {len(text_response)}")

        # 尝试提取JSON数组
        try:
            characters = json.loads(text_response)
        except:
            json_match = re.search(r'\[.*\]', text_response, re.DOTALL)
            if json_match:
                characters = json.loads(json_match.group())
            else:
                logger.warning("AI返回内容中未找到JSON数组")
                return None

        # 添加位置和情绪信息
        for char in characters:
            char['position'] = {
                'x': random.randint(15, 85),
                'y': random.randint(20, 70)
            }
            char['emotion'] = 'neutral'
            char['confidence'] = 0.9

        logger.info(f"AI角色提取成功: {len(characters)}个角色")
        return characters

    except Exception as e:
        logger.warning(f"AI角色提取异常: {e}")
        return None


def extract_characters_from_text(text: str, provider=None) -> list:
    """从文本中提取角色（优先使用AI，规则兜底）"""
    # 优先尝试AI提取
    if provider:
        ai_characters = extract_characters_by_ai(text, provider)
        if ai_characters and len(ai_characters) > 0:
            return ai_characters
        logger.info("AI角色提取失败，使用规则兜底")

    # 规则兜底：关键词匹配
    extracted = []

    # 角色关键词映射 - 扩展到更多常见童话角色
    character_patterns = {
        '小红帽': {'name': '小红帽', 'role': '主角', 'description': '戴着红色帽子的小女孩'},
        'Little Red': {'name': '小红帽', 'role': '主角', 'description': '戴着红色帽子的小女孩'},
        '大灰狼': {'name': '大灰狼', 'role': '反派', 'description': '森林里的坏蛋'},
        'wolf': {'name': '大灰狼', 'role': '反派', 'description': '森林里的坏蛋'},
        '奶奶': {'name': '奶奶', 'role': '配角', 'description': '住在森林深处的老奶奶'},
        '外婆': {'name': '奶奶', 'role': '配角', 'description': '小红帽的外婆'},
        'grandma': {'name': '奶奶', 'role': '配角', 'description': '住在森林深处的老奶奶'},
        '猎人': {'name': '猎人', 'role': '配角', 'description': '勇敢的猎人'},
        'hunter': {'name': '猎人', 'role': '配角', 'description': '勇敢的猎人'},
        '妈妈': {'name': '妈妈', 'role': '配角', 'description': '小红帽的妈妈'},
        '母亲': {'name': '妈妈', 'role': '配角', 'description': '小红帽的母亲'},
        '小猪': {'name': '小猪', 'role': '配角', 'description': '可爱的小猪'},
        'pig': {'name': '小猪', 'role': '配角', 'description': '可爱的小猪'},
        '白雪公主': {'name': '白雪公主', 'role': '主角', 'description': '美丽的公主'},
        '七个小矮人': {'name': '七个小矮人', 'role': '配角', 'description': '善良的小矮人们'},
        '王子': {'name': '王子', 'role': '配角', 'description': '英俊的王子'},
        '皇后': {'name': '皇后', 'role': '反派', 'description': '邪恶的皇后'},
        '巫婆': {'name': '巫婆', 'role': '反派', 'description': '神秘的巫婆'},
    }

    # 检测文本中的角色
    found_characters = set()
    for keyword, char_info in character_patterns.items():
        if keyword in text and char_info['name'] not in found_characters:
            char_data = {
                'name': char_info['name'],
                'role': char_info['role'],
                'description': char_info['description'],
                'position': {
                    'x': random.randint(15, 85),
                    'y': random.randint(20, 70)
                },
                'emotion': 'neutral',
                'confidence': 0.85 + random.random() * 0.15
            }
            extracted.append(char_data)
            found_characters.add(char_info['name'])

    # 如果没有识别到角色，添加默认角色
    if not extracted:
        extracted.append({
            'name': '角色',
            'role': '主角',
            'description': '故事中的角色',
            'position': {'x': 50, 'y': 50},
            'emotion': 'neutral',
            'confidence': 0.9
        })

    return extracted


def detect_scene_from_text(text: str) -> str:
    """从文本中检测场景"""
    scene_keywords = {
        '森林': ['森林', '树林', ' woods ', 'forest'],
        '城堡': ['城堡', '宫殿', '王宫', 'castle', 'palace'],
        '村庄': ['村庄', '小镇', '村子', 'village'],
        '河流': ['河流', '小溪', '水边', 'river', 'stream'],
    }

    for scene, keywords in scene_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return scene

    return '童话镇广场'


def extract_actions_by_rules(text: str, characters: List[Dict]) -> List[Dict[str, Any]]:
    """规则兜底：从文本中提取动作（当AI不可用或输出不合法时调用）"""
    actions = []
    logger.info(f"使用规则兜底提取动作，文本长度: {len(text)}")

    # 1. 检测场景变化
    scene = detect_scene_from_text(text)
    if scene != '童话镇广场':
        actions.append(create_action('enter_scene', content=f"进入{scene}"))

    # 2. 从文本中提取对话 - 改进策略
    # 先获取所有已知角色名称
    known_characters = [char.get('name', '').strip() for char in characters if char.get('name')]

    # 扩展的对话动词列表
    speak_verbs = r'(说|问|道|应道|答道|回答|喊道|叫着|说道|问到|问到|说着|回应|喊|吼|低声嘀咕|冷笑)'

    # 用于存储已提取的对话，避免重复
    extracted_dialogues = set()

    # 对每个已知角色，搜索他们说的话
    for char_name in known_characters:
        if not char_name:
            continue

        # 使用更精确的模式：角色名后面跟着动词，然后是冒号和对话
        patterns_for_char = [
            # 精确匹配：角色名 + 动词 + 冒号 + 引号对话
            # 使用\b确保角色名在词边界处
            r'\b' + re.escape(char_name) + r'\b[，。！？\s]*' + speak_verbs + r'[：:]["“]([^"”]+)["”]',
            # 角色名 + 动词 + 冒号 + 无引号对话
            r'\b' + re.escape(char_name) + r'\b[，。！？\s]*' + speak_verbs + r'[：:]([^，。！？"“”]{1,200})[，。！？]',
        ]

        for pattern in patterns_for_char:
            matches = re.findall(pattern, text)
            for match in matches[:5]:  # 每个角色最多提取5句对话
                # 匹配结果就是对话内容
                content = match.strip() if isinstance(match, str) else match[-1].strip()

                # 过滤掉太短或无效的内容
                if not content or len(content) < 3:
                    continue

                # 去除开头的引号
                if content.startswith('"') or content.startswith('“'):
                    content = content[1:]
                if content.endswith('"') or content.endswith('”'):
                    content = content[:-1]

                # 检查是否已提取过相同的对话（去重）
                content_key = content[:50]
                if content_key in extracted_dialogues:
                    continue
                extracted_dialogues.add(content_key)

                # 限制长度但不截断中间
                if len(content) > 60:
                    content = content[:57] + "..."

                actions.append(create_action('speak', character=char_name, content=content))

    # 3. 检测相遇事件
    meet_keywords = [
        '遇到', '碰到', '相见', '遇见', ' encounter ', ' meet ',
        '遇到了', '碰到了', '遇见了'
    ]
    for keyword in meet_keywords:
        if keyword.lower() in text.lower():
            actions.append(create_action('meet', content="两人相遇"))
            break

    # 4. 检测角色出现
    appear_keywords = ['出现', '出现', ' arrived ', ' appeared ']
    for char in characters:
        char_name = char.get('name', '')
        for keyword in appear_keywords:
            if char_name and keyword.lower() in text.lower():
                actions.append(create_action('appear', character=char_name, content=f"{char_name}出现"))
                break

    # 5. 检测移动动作
    move_keywords = ['走', '跑', '去', '移动', '走向', '跑到', '走到', '走向了', '跑去',
                     'walk', 'run', 'go', 'move', 'walks', 'runs', 'goes', 'moves']
    move_targets = ['门口', '森林', '广场', '中心', '左边', '右边', '上方', '下方',
                    '深处', '小路', '奶奶家', 'door', 'forest', 'square', 'center',
                    'left', 'right', 'top', 'bottom', 'deep', 'path']

    for char in characters:
        char_name = char.get('name', '')
        if not char_name:
            continue

        # 检查是否有移动关键词
        has_move = any(keyword.lower() in text.lower() for keyword in move_keywords)
        if has_move:
            # 尝试提取目标位置
            target = ''
            for tgt in move_targets:
                if tgt in text:
                    target = tgt
                    break

            if target:
                actions.append(create_action('move', character=char_name, target=target,
                                           content=f"{char_name}移动到{target}"))
            else:
                # 如果没有明确目标，使用默认目标
                actions.append(create_action('move', character=char_name, target='广场中心',
                                           content=f"{char_name}开始移动"))

    # 6. 如果没有提取到动作，添加叙述动作
    if not actions:
        # 截取文本前80字作为叙述
        narration = text[:80] if len(text) > 80 else text
        actions.append(create_action('narration', content=narration))
        logger.info(f"规则兜底: 添加叙述动作")

    # 6. 限制最多返回10个动作
    actions = actions[:10]
    logger.info(f"规则兜底完成: 提取到{len(actions)}个动作")

    return actions


def extract_actions_by_ai(text: str, characters: List[Dict], provider) -> List[Dict[str, Any]]:
    """AI提取动作：调用LLM将文本转换为动作序列"""
    if not provider:
        logger.warning("AI动作提取失败: 无provider")
        return None

    # 构建提示
    char_names = [c.get('name', '') for c in characters] if characters else []
    char_list = ', '.join(char_names) if char_names else '无'

    # 优化的提示词：强制JSON格式输出，保持时间顺序
    prompt = f"""
分析以下故事文本，按时间顺序提取动作序列。

角色：{char_list}

要求：
1. 严格按照故事中的时间顺序提取
2. 对话和动作交替进行，保持原顺序
3. 只输出JSON数组

输出格式：
[
  {{"type": "speak", "character": "小红帽", "content": "妈妈，我走了"}},
  {{"type": "speak", "character": "妈妈", "content": "路上小心"}},
  {{"type": "move", "character": "小红帽", "target": "森林", "content": "小红帽走进森林"}}
]

故事：
{text}

输出JSON："""

    try:
        logger.info("开始AI动作提取...")
        result = provider.run(
            prompt=prompt,
            history=[],
            params={'temperature': 0.2, 'max_tokens': 2000}
        )

        if not result.get('success'):
            logger.warning("AI动作提取失败: provider返回失败")
            return None

        text_response = result['text']
        logger.info(f"AI返回原始内容长度: {len(text_response)}")

        # 尝试提取JSON数组
        # 首先移除可能的markdown代码块格式
        text_response = re.sub(r'```json\s*', '', text_response)
        text_response = re.sub(r'\s*```\s*$', '', text_response)

        # 尝试直接解析
        try:
            actions = json.loads(text_response)
        except:
            # 尝试用正则提取
            json_match = re.search(r'\[.*\]', text_response, re.DOTALL)
            if json_match:
                actions = json.loads(json_match.group())
            else:
                logger.warning("AI返回内容中未找到JSON数组")
                return None

        # 验证动作格式
        if not validate_actions(actions):
            logger.warning("AI返回的动作格式不合法")
            return None

        logger.info(f"AI动作提取成功: {len(actions)}个动作")
        return actions

    except json.JSONDecodeError as e:
        logger.warning(f"AI返回内容JSON解析失败: {e}")
    except Exception as e:
        logger.warning(f"AI动作提取异常: {e}")

    return None


# ==================== API端点 ====================

@app.route('/')
def index():
    """根路径"""
    return jsonify({
        'name': '童话镇多智能体系统 API',
        'version': '1.0.0',
        'status': 'running'
    })


@app.route('/api/analyze-text', methods=['POST'])
def analyze_text():
    """分析文本，识别角色、场景和动作序列"""
    data = request.get_json() or {}
    text = data.get('text', '')
    scene = data.get('scene', '')

    # 打印并返回接收到的内容
    logger.info(f"收到文本: {text}")
    logger.info(f"收到场景: {scene}")

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400

    # 获取LLM提供者
    provider = get_llm_provider()

    # 提取角色（优先使用AI）
    characters = extract_characters_from_text(text, provider)

    # 检测场景
    detected_scene = detect_scene_from_text(text)
    if scene:
        detected_scene = scene

    # 提取剧情点
    sentences = [s.strip() for s in text.replace('。', '.').replace('！', '!').replace('？', '?').split('.') if s.strip()]
    plot_points = []
    for i, sentence in enumerate(sentences[:5]):
        plot_points.append({
            'id': i + 1,
            'content': sentence[:100],
            'importance': random.random()
        })

    # ===== AI 动作提取 =====
    actions = None
    extraction_method = "unknown"

    # 优先尝试AI提取（确保AI优先）
    if provider:
        logger.info("===== 优先使用AI提取动作 =====")
        actions = extract_actions_by_ai(text, characters, provider)

        if actions and len(actions) > 0:
            logger.info(f"✅ AI提取动作成功: {len(actions)}个动作")
            extraction_method = "AI"
        else:
            logger.warning("❌ AI动作提取失败（可能原因：API调用失败、返回格式错误、动作验证失败）")
            logger.info("===== 切换到规则兜底提取 =====")

    # 兜底：规则提取（只有AI不可用或失败时才执行）
    if not actions or len(actions) == 0:
        actions = extract_actions_by_rules(text, characters)
        logger.info(f"📋 规则兜底提取动作: {len(actions)}个动作")
        extraction_method = "rules"

    logger.info(f"动作提取完成，使用方法: {extraction_method}")

    # 保存角色到数据存储并更新 GameState
    saved_characters = []
    for char in characters:
        saved_char = data_store.add_character(char)
        saved_characters.append(saved_char)

    # 更新 GameState 的角色列表
    gs = get_game_state()
    if gs:
        gs.characters = [
            {
                'name': char['name'],
                'persona': char.get('description', ''),
                'goal': '',
                'position': char.get('position', {}),
                'emotion': char.get('emotion', 'neutral')
            }
            for char in characters
        ]

    # ===== 使用剧情导演控制流程 =====
    director_response = None
    director = get_plot_director()

    if director and actions:
        try:
            logger.info(f"开始剧情导演处理，共 {len(actions)} 个动作")

            # 生成后续选项（可以用 AI 生成，这里先用默认）
            next_options = generate_next_options(text, characters)

            # 导演这个回合
            director_response = director.direct_turn(
                raw_actions=actions,
                narrative=f"场景：{detected_scene}",
                next_options=next_options
            )

            logger.info("剧情导演处理完成")
        except Exception as e:
            logger.error(f"剧情导演处理失败: {e}")
            director_response = None

    # 返回时带上收到的原始内容（方便调试）
    response_data = {
        'success': True,
        'received': {
            'text': text,
            'scene': scene
        },
        'characters': saved_characters,
        'scene': detected_scene,
        'plotPoints': plot_points,
        'actions': actions  # 保留原始动作用于调试
    }

    # 如果有导演响应，添加标准化的指令包
    if director_response:
        response_data['director_output'] = director_response
        logger.info("已添加导演输出到响应")

    # ===== 剧本分段处理 =====
    story_segments = None
    if StorySegmenter and actions and len(actions) > 0:
        try:
            segmenter = StorySegmenter()
            segments = segmenter.segment_story(
                raw_text=text,
                actions=actions,
                characters=characters,
                current_scene=detected_scene
            )

            if len(segments) > 1:
                # 需要分段的情况
                story_segments = [seg.to_dict() for seg in segments]

                # 为每个分段生成独立的导演输出（如果导演可用）
                segmented_director_outputs = []
                for seg in segments:
                    if director:
                        try:
                            seg_director_output = director.direct_turn(
                                raw_actions=seg.actions,
                                narrative=f"场景：{seg.scene_context} - {seg.narrative}",
                                next_options=generate_next_options(seg.narrative, characters)
                            )
                            segmented_director_outputs.append({
                                'segment_id': seg.segment_id,
                                'director_output': seg_director_output
                            })
                        except Exception as e:
                            logger.error(f"段落 {seg.segment_id} 导演处理失败: {e}")
                            segmented_director_outputs.append({
                                'segment_id': seg.segment_id,
                                'error': str(e)
                            })
                    else:
                        segmented_director_outputs.append({
                            'segment_id': seg.segment_id,
                            'director_output': None
                        })

                response_data['story_segments'] = story_segments
                response_data['segmented_director_outputs'] = segmented_director_outputs
                response_data['segmentation_info'] = {
                    'total_segments': len(segments),
                    'total_actions': len(actions),
                    'needs_segmentation': True,
                    'message': f'剧本已自动分为 {len(segments)} 个段落进行演出'
                }

                logger.info(f"✅ 剧本已分段：共 {len(segments)} 个段落")
            else:
                # 不需要分段
                response_data['segmentation_info'] = {
                    'total_segments': 1,
                    'total_actions': len(actions),
                    'needs_segmentation': False,
                    'message': '剧本较短，无需分段'
                }
        except Exception as e:
            logger.error(f"剧本分段失败: {e}")
            response_data['segmentation_error'] = str(e)

    return jsonify(response_data)


def generate_next_options(text: str, characters: List[Dict]) -> List[Dict[str, str]]:
    """生成后续剧情选项（可以扩展为调用 AI 生成）"""
    # 简单实现：基于文本内容生成几个通用选项
    options = [
        {'label': '继续对话', 'action_input': 'continue conversation'},
        {'label': '询问更多细节', 'action_input': 'ask for details'},
    ]

    # 根据文本内容添加特定选项
    if any(word in text for word in ['走', '去', '移动']):
        options.append({'label': '前往其他地方', 'action_input': 'go elsewhere'})

    if any(word in text for word in ['说', '问', '告诉']):
        options.append({'label': '提出新问题', 'action_input': 'ask new question'})

    options.append({'label': '结束互动', 'action_input': 'end interaction'})

    return options[:4]  # 最多返回4个选项


@app.route('/api/characters', methods=['GET'])
def get_characters():
    """获取所有角色"""
    characters = data_store.get_all_characters()
    return jsonify({
        'success': True,
        'characters': characters,
        'count': len(characters)
    })


@app.route('/api/characters/<int:char_id>', methods=['GET'])
def get_character(char_id):
    """获取单个角色"""
    character = data_store.get_character(char_id)
    if not character:
        return jsonify({'success': False, 'error': '角色不存在'}), 404
    return jsonify({
        'success': True,
        'character': character
    })


@app.route('/api/characters/<int:char_id>/move', methods=['POST'])
def move_character(char_id):
    """移动角色"""
    character = data_store.get_character(char_id)
    if not character:
        return jsonify({'success': False, 'error': '角色不存在'}), 404

    data = request.get_json() or {}
    x = data.get('x', character['position']['x'])
    y = data.get('y', character['position']['y'])

    # 限制移动范围 (5% - 95%)
    x = max(5, min(95, x))
    y = max(10, min(85, y))

    # 更新位置
    character['position'] = {'x': x, 'y': y}
    data_store.update_character(char_id, {'position': character['position']})

    return jsonify({
        'success': True,
        'character': character,
        'oldPosition': character['position']
    })


@app.route('/api/characters/<int:char_id>/environment', methods=['GET'])
def get_character_environment(char_id):
    """获取角色环境信息"""
    character = data_store.get_character(char_id)
    if not character:
        return jsonify({'success': False, 'error': '角色不存在'}), 404

    all_characters = data_store.get_all_characters()

    # 计算附近的角色
    nearby_characters = []
    char_x = character['position']['x']
    char_y = character['position']['y']
    vision_radius = 150  # 视野半径（百分比距离）

    for other in all_characters:
        if other['id'] != char_id:
            dist = ((other['position']['x'] - char_x)**2 + (other['position']['y'] - char_y)**2)**0.5
            if dist <= vision_radius:
                nearby_characters.append({
                    'id': other['id'],
                    'name': other['name'],
                    'role': other['role'],
                    'position': other['position'],
                    'distance': round(dist, 2)
                })

    return jsonify({
        'success': True,
        'character': {
            'id': character['id'],
            'name': character['name'],
            'position': character['position']
        },
        'environment': {
            'nearbyCharacters': nearby_characters,
            'terrain': {
                'type': detect_scene_from_text(''),
                'description': '童话镇广场',
                'features': ['草地', '树木', '花丛']
            },
            'weather': {
                'condition': 'sunny',
                'temperature': 25,
                'timeOfDay': 'day'
            }
        }
    })


@app.route('/api/dialogue/send', methods=['POST'])
def send_dialogue():
    """发送对话，获取角色回复"""
    data = request.get_json() or {}
    character_id = data.get('characterId')
    message = data.get('message', '')
    session_id = data.get('session_id')

    if not character_id:
        return jsonify({'success': False, 'error': '缺少角色ID'}), 400
    if not message:
        return jsonify({'success': False, 'error': '消息不能为空'}), 400

    # 支持字符串ID和整数ID
    char_id_int = None
    if isinstance(character_id, str) and character_id.startswith('char-'):
        char_id_int = int(character_id.replace('char-', ''))
    elif isinstance(character_id, int):
        char_id_int = character_id
    else:
        # 尝试直接解析
        try:
            char_id_int = int(character_id)
        except:
            pass

    character = data_store.get_character(char_id_int) if char_id_int else None

    # 如果找不到，尝试遍历查找
    if not character:
        for cid, char in data_store.characters.items():
            if char.get('id_str') == character_id:
                character = char
                char_id_int = cid
                break

    if not character:
        return jsonify({'success': False, 'error': '角色不存在'}), 404

    # 保存用户消息
    data_store.add_dialogue(char_id_int, 'user', message)

    # 获取对话历史
    dialogues = data_store.get_dialogues(char_id_int, limit=10)

    # 获取记忆系统历史
    ms = get_memory_store()
    extra_history = None
    if ms and session_id:
        try:
            history = ms.get_history(session_id, limit=5)
            extra_history = []
            for entry in history:
                extra_history.append({'role': 'user', 'content': entry.user_input})
                extra_history.append({'role': 'assistant', 'content': entry.model_reply})
        except:
            pass

    # 构建上下文 - 明确用户是玩家，不是故事角色
    gs = get_game_state()
    if gs:
        # 只设置当前角色，且不包含与其他角色的关系描述
        current_char_desc = character.get('description', '').split('，')[0].split(',')[0]  # 只取第一部分，去掉关系描述
        gs.characters = [{
            'name': character['name'],
            'persona': current_char_desc,
            'goal': ''
        }]
        # 重置故事背景，避免包含所有角色的信息
        original_background = gs.story_background
        gs.story_background = "童话镇是一个充满魔法和奇遇的地方。"

        # 获取完整上下文（传入记忆历史）
        context = gs.to_context(extra_history)

        # 恢复原始故事背景
        gs.story_background = original_background

        if context:
            context += f"\n\n【角色扮演规则】"
            context += f"\n1. 你现在是故事中的一个角色：{character['name']}（{current_char_desc}）"
            context += f"\n2. 正在与你对话的是【玩家/用户】，不是你故事中的任何角色！"
            context += f"\n3. 玩家是独立的第三方，不参与故事中的角色关系！"
            context += f"\n4. 例如：如果你是奶奶，不要把玩家当成小红帽；如果你妈妈，不要把玩家当成孩子！"
            context += f"\n\n玩家说: {message}\n请以{character['name']}的身份，自然地回复玩家："
        else:
            context = f"【角色扮演规则】\n"
            context += f"1. 你正在扮演：{character['name']}（{current_char_desc}）\n"
            context += f"2. 【重要】正在与你对话的是【玩家/用户】，不是你故事中的任何角色！\n"
            context += f"3. 玩家是独立的第三方，不参与故事中的角色关系！\n\n"
            context += f"玩家说: {message}\n{character['name']}的回答: "
    else:
        current_char_desc = character.get('description', '').split('，')[0].split(',')[0]
        context = f"【角色扮演规则】\n"
        context += f"1. 你正在扮演：{character['name']}（{current_char_desc}）\n"
        context += f"2. 【重要】正在与你对话的是【玩家/用户】，不是你故事中的任何角色！\n"
        context += f"3. 玩家是独立的第三方，不参与故事中的角色关系！\n"
        context += f"4. 例如：如果你是奶奶，不要把玩家当成小红帽！\n\n"
        for d in dialogues[:-1]:
            role_name = "玩家" if d['role'] == 'user' else character['name']
            context += f"{role_name}: {d['content']}\n"
        context += f"\n玩家说: {message}\n{character['name']}的回答: "

    # 尝试使用LLM
    provider = get_llm_provider()
    response_text = ""
    provider_output = {}

    if provider:
        try:
            result = provider.run(
                prompt=context,
                history=[],
                params={'temperature': 0.8, 'max_tokens': 200}
            )
            if result.get('success'):
                response_text = result['text']
                provider_output = result
        except Exception as e:
            print(f"LLM调用失败: {e}")

    # 如果LLM失败，使用默认回复
    if not response_text:
        default_responses = [
            f"我明白了，{message}",
            "这很有趣！让我想想...",
            "我同意你的看法。",
            "好的，我知道了。",
            f"{message}吗？真有意思！",
            "让我们继续这个故事吧。"
        ]
        response_text = random.choice(default_responses)

    # 保存角色回复
    data_store.add_dialogue(char_id_int, 'assistant', response_text)

    # 记录到 GameState
    if gs:
        gs.add_turn(message, provider_output if provider_output else {'text': response_text})

    # 保存到记忆系统
    ms = get_memory_store()
    saved_session_id = session_id
    if ms:
        if not session_id:
            saved_session_id = ms.create_session()
        ms.add_turn(saved_session_id, message, response_text)

    return jsonify({
        'success': True,
        'character': character,
        'response': response_text,
        'dialogueHistory': dialogues,
        'session_id': saved_session_id
    })


@app.route('/api/plot/predict', methods=['POST'])
def predict_plot():
    """预测剧情发展方向"""
    data = request.get_json() or {}
    text = data.get('text', '')
    characters = data.get('characters', [])

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400

    # 构建提示
    char_names = [c['name'] for c in characters] if characters else ['角色']
    context = f"故事中的人物: {', '.join(char_names)}\n"
    context += f"故事内容: {text[:500]}...\n\n"
    context += "请预测这个故事可能的剧情发展方向，"
    context += "给出3-4个可能的结局选项。\n"
    context += "请以JSON数组格式返回，每个选项包含: title(标题), description(描述), probability(概率0-1)"

    # 尝试使用LLM
    provider = get_llm_provider()
    predictions = []

    if provider:
        try:
            result = provider.run(
                prompt=context,
                history=[],
                params={'temperature': 0.7, 'max_tokens': 500}
            )
            if result.get('success'):
                import re
                # 尝试解析JSON
                json_match = re.search(r'\[.*\]', result['text'], re.DOTALL)
                if json_match:
                    predictions = json.loads(json_match.group())
        except Exception as e:
            print(f"LLM调用失败: {e}")

    # 如果LLM失败，使用默认预测
    if not predictions:
        predictions = [
            {
                'id': 1,
                'title': '冒险路线',
                'description': '主角踏上冒险旅程，遇到各种挑战和机遇',
                'probability': 0.35
            },
            {
                'id': 2,
                'title': '友谊路线',
                'description': '通过合作和友谊解决问题',
                'probability': 0.28
            },
            {
                'id': 3,
                'title': '冲突路线',
                'description': '面临内部冲突和外部威胁',
                'probability': 0.22
            },
            {
                'id': 4,
                'title': '成长路线',
                'description': '角色在挑战中成长和改变',
                'probability': 0.15
            }
        ]

    return jsonify({
        'success': True,
        'predictions': predictions
    })


@app.route('/api/game/state', methods=['GET'])
def get_game_state_info():
    """获取游戏状态"""
    gs = get_game_state()
    if not gs:
        return jsonify({'success': False, 'error': '游戏状态未初始化'}), 500

    return jsonify({
        'success': True,
        'state': gs.to_dict(),
        'summary': gs.get_summary()
    })


@app.route('/api/game/reset', methods=['POST'])
def reset_game_state():
    """重置游戏状态"""
    global game_state
    gs = get_game_state()
    if gs:
        gs.reset()
    return jsonify({'success': True, 'message': '游戏状态已重置'})


# ==================== 会话管理 API ====================

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """创建新会话"""
    ms = get_memory_store()
    if not ms:
        return jsonify({'success': False, 'error': '记忆系统未初始化'}), 500

    session_id = ms.create_session()
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': '会话创建成功'
    })


@app.route('/api/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """获取会话历史"""
    ms = get_memory_store()
    if not ms:
        return jsonify({'success': False, 'error': '记忆系统未初始化'}), 500

    limit = request.args.get('limit', type=int)
    try:
        history = ms.get_history(session_id, limit)
        return jsonify({
            'success': True,
            'session_id': session_id,
            'history': [
                {
                    'timestamp': entry.timestamp,
                    'user_input': entry.user_input,
                    'model_reply': entry.model_reply,
                    'tokens': entry.tokens
                }
                for entry in history
            ],
            'count': len(history)
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404


@app.route('/api/session/<session_id>/summary', methods=['GET'])
def get_session_summary(session_id):
    """获取会话摘要"""
    ms = get_memory_store()
    if not ms:
        return jsonify({'success': False, 'error': '记忆系统未初始化'}), 500

    summary = ms.summarize_history(session_id)
    return jsonify({
        'success': True,
        'session_id': session_id,
        'summary': summary
    })


# ==================== 多角色协作 API ====================

@app.route('/api/multi-agent/act', methods=['POST'])
def multi_agent_act():
    """多角色同时行动"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    characters = data.get('characters', [])
    user_input = data.get('input', '')

    if not characters:
        return jsonify({'success': False, 'error': '需要指定角色'}), 400

    ms = get_memory_store()
    gs = get_game_state()
    provider = get_llm_provider()

    # 获取历史对话
    history = []
    if ms and session_id:
        history = ms.get_history(session_id, limit=5)
        # 转换为 extra_history 格式
        extra_history = []
        for entry in history:
            extra_history.append({'role': 'user', 'content': entry.user_input})
            extra_history.append({'role': 'assistant', 'content': entry.model_reply})
    else:
        extra_history = None

    # 更新游戏状态的角色
    if gs:
        gs.characters = [
            {'name': c.get('name', ''), 'persona': c.get('description', ''), 'goal': c.get('goal', '')}
            for c in characters
        ]
        context = gs.to_context(extra_history)
    else:
        context = f"角色: {', '.join([c.get('name', '') for c in characters])}\n\n用户: {user_input}"

    # 调用 LLM
    response_text = ""
    if provider and context:
        try:
            # 构建多角色系统提示
            multi_context = f"{context}\n\n用户输入: {user_input}\n请为每个角色生成回应。"
            result = provider.run(
                prompt=multi_context,
                history=[],
                params={'temperature': 0.8, 'max_tokens': 500}
            )
            if result.get('success'):
                response_text = result['text']
        except Exception as e:
            print(f"多角色LLM调用失败: {e}")

    # 如果没有LLM响应，使用默认回复
    if not response_text:
        responses = []
        for char in characters:
            responses.append({
                'character': char.get('name', '角色'),
                'dialogue': f"我听到了：{user_input}",
                'action': '倾听',
                'emotion': 'neutral'
            })
        return jsonify({
            'success': True,
            'actions': responses,
            'session_id': session_id
        })

    # 保存到记忆
    if ms and session_id:
        ms.add_turn(session_id, user_input, response_text)

    # 解析LLM响应（简单解析）
    actions = []
    for char in characters:
        actions.append({
            'character': char.get('name', '角色'),
            'dialogue': response_text[:100] if response_text else '',
            'action': '对话',
            'emotion': 'neutral'
        })

    return jsonify({
        'success': True,
        'actions': actions,
        'response': response_text,
        'session_id': session_id
    })


@app.route('/api/execute-turn', methods=['POST'])
def execute_turn():
    """
    执行一个完整的剧情回合

    请求体：
    {
        "text": "用户输入的剧情文本",
        "scene": "场景名称（可选）",
        "characters": [{"name": "角色名", ...}],  // 可选，不传则自动识别
        "session_id": "会话ID（可选）"
    }

    返回标准化的导演指令包
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    scene = data.get('scene', '')
    characters_input = data.get('characters', [])
    session_id = data.get('session_id')

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400

    logger.info(f"执行回合请求: {text[:50]}...")

    # 1. 提取或更新角色
    if characters_input:
        characters = characters_input
        # 更新数据存储
        for char_data in characters:
            data_store.add_character(char_data)
    else:
        characters = extract_characters_from_text(text)
        for char in characters:
            data_store.add_character(char)

    # 2. 更新 GameState
    gs = get_game_state()
    if gs:
        gs.characters = [
            {
                'name': char['name'],
                'persona': char.get('description', ''),
                'goal': '',
                'position': char.get('position', {}),
                'emotion': char.get('emotion', 'neutral')
            }
            for char in characters
        ]

    # 3. AI 提取动作
    provider = get_llm_provider()
    actions = None

    if provider:
        actions = extract_actions_by_ai(text, characters, provider)
        if actions:
            logger.info(f"AI提取动作成功: {len(actions)}个")

    # 4. 规则兜底
    if not actions:
        actions = extract_actions_by_rules(text, characters)
        logger.info(f"规则提取动作: {len(actions)}个")

    # 5. 使用导演系统处理
    director = get_plot_director()
    if not director:
        return jsonify({
            'success': False,
            'error': '剧情导演未初始化'
        }), 500

    try:
        # 生成后续选项
        next_options = generate_next_options(text, characters)

        # 检测场景
        detected_scene = scene or detect_scene_from_text(text)

        # 导演这个回合
        director_response = director.direct_turn(
            raw_actions=actions,
            narrative=f"场景：{detected_scene}",
            next_options=next_options
        )

        # 记录到 GameState
        gs.add_turn(text, {'text': director_response.get('narrative', '')})

        # 保存到记忆系统
        ms = get_memory_store()
        if ms:
            if not session_id:
                session_id = ms.create_session()
            ms.add_turn(session_id, text, director_response.get('narrative', ''))

        logger.info("回合执行完成")

        # 构建基础响应
        response_data = {
            'success': True,
            'session_id': session_id,
            'director_output': director_response,
            'metadata': {
                'scene': detected_scene,
                'characters_count': len(characters),
                'actions_count': len(actions)
            }
        }

        # ===== 剧本分段处理 =====
        if StorySegmenter and actions and len(actions) > 0:
            try:
                segmenter = StorySegmenter()
                segments = segmenter.segment_story(
                    raw_text=text,
                    actions=actions,
                    characters=characters,
                    current_scene=detected_scene
                )

                if len(segments) > 1:
                    # 需要分段
                    story_segments = [seg.to_dict() for seg in segments]

                    # 为每个分段生成独立的导演输出
                    segmented_director_outputs = []
                    for seg in segments:
                        try:
                            seg_director_output = director.direct_turn(
                                raw_actions=seg.actions,
                                narrative=f"场景：{seg.scene_context} - {seg.narrative}",
                                next_options=generate_next_options(seg.narrative, characters)
                            )
                            segmented_director_outputs.append({
                                'segment_id': seg.segment_id,
                                'director_output': seg_director_output
                            })
                        except Exception as e:
                            logger.error(f"段落 {seg.segment_id} 导演处理失败: {e}")
                            segmented_director_outputs.append({
                                'segment_id': seg.segment_id,
                                'error': str(e)
                            })

                    response_data['story_segments'] = story_segments
                    response_data['segmented_director_outputs'] = segmented_director_outputs
                    response_data['segmentation_info'] = {
                        'total_segments': len(segments),
                        'total_actions': len(actions),
                        'needs_segmentation': True,
                        'message': f'剧本已自动分为 {len(segments)} 个段落进行演出'
                    }

                    logger.info(f"✅ 剧本已分段：共 {len(segments)} 个段落")
                else:
                    response_data['segmentation_info'] = {
                        'total_segments': 1,
                        'total_actions': len(actions),
                        'needs_segmentation': False,
                        'message': '剧本较短，无需分段'
                    }
            except Exception as e:
                logger.error(f"剧本分段失败: {e}")
                response_data['segmentation_error'] = str(e)

        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行回合失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'执行失败: {str(e)}'
        }), 500


@app.route('/api/game-state', methods=['GET'])
def get_current_game_state():
    """获取当前游戏状态"""
    gs = get_game_state()
    if not gs:
        return jsonify({
            'success': False,
            'error': '游戏状态未初始化'
        }), 500
    
    return jsonify({
        'success': True,
        'game_state': gs.to_dict(),
        'summary': gs.get_summary()
    })


@app.route('/api/reset-game', methods=['POST'])
def reset_game():
    """重置游戏状态"""
    gs = get_game_state()
    if gs:
        gs.reset()
        
        # 重置导演
        global plot_director
        if plot_director:
            plot_director = PlotDirector(gs)
        
        logger.info("游戏状态已重置")
    
    return jsonify({
        'success': True,
        'message': '游戏已重置'
    })


# ==================== AI图片生成 API ====================

@app.route('/api/images/generate-map', methods=['POST'])
def generate_map_image_api():
    """
    生成地图背景图片
    
    请求体：
    {
        "prompt": "图片生成提示词",
        "api_key": "nanobanana API密钥",
        "image_size": "2K",      // 可选：1K、2K、4K
        "aspect_ratio": "16:9"   // 可选：1:1、3:4、4:3、9:16、16:9
    }
    
    返回：
    {
        "success": true,
        "image_url": "生成的图片URL",
        "prompt": "使用的提示词"
    }
    """
    data = request.get_json() or {}
    prompt = data.get('prompt', '')
    api_key = data.get('api_key', '')
    image_size = data.get('image_size', '2K')
    aspect_ratio = data.get('aspect_ratio', '16:9')
    
    if not prompt:
        return jsonify({'success': False, 'error': '提示词不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_map_image:
        return jsonify({'success': False, 'error': '图片生成器未加载'}), 500
    
    try:
        logger.info(f"开始生成地图图片: {prompt[:30]}...")
        result = generate_map_image(api_key, prompt, image_size, aspect_ratio)
        
        if result.get('success'):
            logger.info(f"地图图片生成成功: {result['image_url']}")
            return jsonify({
                'success': True,
                'image_url': result['image_url'],
                'prompt': result['prompt'],
                'image_size': result['image_size'],
                'aspect_ratio': result['aspect_ratio']
            })
        else:
            logger.error(f"地图图片生成失败: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"生成地图图片异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/images/generate-character', methods=['POST'])
def generate_character_image_api():
    """
    生成角色人物图片（透明底）
    
    请求体：
    {
        "prompt": "图片生成提示词（应包含transparent background）",
        "api_key": "nanobanana API密钥",
        "image_size": "2K",      // 可选：1K、2K、4K
        "aspect_ratio": "3:4"    // 可选：1:1、3:4、4:3、9:16、16:9
    }
    
    返回：
    {
        "success": true,
        "image_url": "生成的图片URL",
        "prompt": "使用的提示词"
    }
    """
    data = request.get_json() or {}
    prompt = data.get('prompt', '')
    api_key = data.get('api_key', '')
    image_size = data.get('image_size', '2K')
    aspect_ratio = data.get('aspect_ratio', '3:4')
    
    if not prompt:
        return jsonify({'success': False, 'error': '提示词不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_character_image:
        return jsonify({'success': False, 'error': '图片生成器未加载'}), 500
    
    try:
        # 确保提示词包含透明背景要求
        if 'transparent' not in prompt.lower() and 'cutout' not in prompt.lower():
            prompt += ', transparent background, PNG format, cutout character'
        
        logger.info(f"开始生成角色图片: {prompt[:30]}...")
        result = generate_character_image(api_key, prompt, image_size, aspect_ratio)
        
        if result.get('success'):
            logger.info(f"角色图片生成成功: {result['image_url']}")
            return jsonify({
                'success': True,
                'image_url': result['image_url'],
                'prompt': result['prompt'],
                'image_size': result['image_size'],
                'aspect_ratio': result['aspect_ratio']
            })
        else:
            logger.error(f"角色图片生成失败: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"生成角色图片异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/images/generate-all', methods=['POST'])
def generate_all_images_api():
    """
    生成所有图片（地图 + 所有角色）
    
    请求体：
    {
        "text": "剧情文本",
        "characters": [
            {"name": "角色1", "description": "...", "emotion": "happy"},
            {"name": "角色2", "description": "...", "emotion": "neutral"}
        ],
        "api_key": "nanobanana API密钥"
    }
    
    返回：
    {
        "success": true,
        "map": {"image_url": "...", "prompt": "..."},
        "characters": [{"name": "...", "image_url": "...", "prompt": "..."}, ...],
        "scene_type": "场景类型"
    }
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    characters_input = data.get('characters', [])
    api_key = data.get('api_key', '')
    
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_all_prompts or not generate_map_image or not generate_character_image:
        return jsonify({'success': False, 'error': '必要模块未加载'}), 500
    
    try:
        # 1. 生成所有提示词
        characters = characters_input if characters_input else extract_characters_from_text(text)
        prompts_result = generate_all_prompts(text, characters)
        
        # 2. 生成地图图片
        map_result = generate_map_image(api_key, prompts_result['map']['prompt'])
        
        if not map_result.get('success'):
            return jsonify({
                'success': False,
                'error': f'地图生成失败: {map_result.get("error")}'
            }), 500
        
        # 3. 生成角色图片
        character_images = []
        for char_prompt in prompts_result['characters']:
            char_result = generate_character_image(api_key, char_prompt['prompt'])
            
            if char_result.get('success'):
                character_images.append({
                    'name': char_prompt['character_name'],
                    'image_url': char_result['image_url'],
                    'prompt': char_result['prompt'],
                    'emotion': char_prompt['emotion']
                })
            else:
                # 某个角色生成失败，继续尝试其他角色
                logger.warning(f"角色 {char_prompt['character_name']} 生成失败: {char_result.get('error')}")
                character_images.append({
                    'name': char_prompt['character_name'],
                    'error': char_result.get('error', '生成失败'),
                    'prompt': char_prompt['prompt']
                })
        
        logger.info(f"批量图片生成完成: 地图1张, 角色{len(character_images)}张")
        
        return jsonify({
            'success': True,
            'map': {
                'image_url': map_result['image_url'],
                'prompt': map_result['prompt'],
                'scene_type': prompts_result['scene_type']
            },
            'characters': character_images,
            'scene_type': prompts_result['scene_type'],
            'total_characters': len(character_images)
        })
        
    except Exception as e:
        logger.error(f"批量生成图片异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/images/check-balance', methods=['POST'])
def check_image_balance():
    """
    查询nanobanana账户余额
    
    请求体：
    {
        "api_key": "nanobanana API密钥"
    }
    
    返回：
    {
        "success": true,
        "balance": 余额数值
    }
    """
    data = request.get_json() or {}
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not create_image_generator:
        return jsonify({'success': False, 'error': '图片生成器未加载'}), 500
    
    try:
        generator = create_image_generator(api_key)
        result = generator.get_balance()
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'balance': result.get('balance', result)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '查询失败')
            }), 500
            
    except Exception as e:
        logger.error(f"查询余额异常: {e}")
        return jsonify({
            'success': False,
            'error': f'查询失败: {str(e)}'
        }), 500


# ==================== 素材管理 API ====================

@app.route('/api/assets/save-map', methods=['POST'])
def save_map_asset_api():
    """
    保存地图背景素材
    
    请求体：
    {
        "image_url": "图片URL",
        "scene_name": "场景名称"
    }
    
    返回：
    {
        "success": true,
        "asset_id": "素材ID",
        "url": "素材相对路径",
        "local_path": "本地路径"
    }
    """
    data = request.get_json() or {}
    image_url = data.get('image_url', '')
    scene_name = data.get('scene_name', '')
    
    if not image_url:
        return jsonify({'success': False, 'error': '图片URL不能为空'}), 400
    
    if not save_map_asset:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        result = save_map_asset(image_url, scene_name)
        logger.info(f"保存地图素材: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"保存地图素材失败: {e}")
        return jsonify({
            'success': False,
            'error': f'保存失败: {str(e)}'
        }), 500


@app.route('/api/assets/save-character', methods=['POST'])
def save_character_asset_api():
    """
    保存角色人物素材
    
    请求体：
    {
        "image_url": "图片URL",
        "character_name": "角色名称",
        "emotion": "情绪（可选，默认neutral）"
    }
    
    返回：
    {
        "success": true,
        "asset_id": "素材ID",
        "url": "素材相对路径",
        "local_path": "本地路径"
    }
    """
    data = request.get_json() or {}
    image_url = data.get('image_url', '')
    character_name = data.get('character_name', '')
    emotion = data.get('emotion', 'neutral')
    
    if not image_url:
        return jsonify({'success': False, 'error': '图片URL不能为空'}), 400
    
    if not character_name:
        return jsonify({'success': False, 'error': '角色名称不能为空'}), 400
    
    if not save_character_asset:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        result = save_character_asset(image_url, character_name, emotion)
        logger.info(f"保存角色素材: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"保存角色素材失败: {e}")
        return jsonify({
            'success': False,
            'error': f'保存失败: {str(e)}'
        }), 500


@app.route('/api/assets/save-all', methods=['POST'])
def save_all_assets_api():
    """
    批量保存所有素材（地图 + 角色）
    
    请求体：
    {
        "map": {
            "image_url": "地图图片URL",
            "scene_type": "场景类型"
        },
        "characters": [
            {"name": "角色1", "image_url": "...", "emotion": "happy"},
            {"name": "角色2", "image_url": "...", "emotion": "neutral"}
        ]
    }
    
    返回：
    {
        "success_count": 成功数量,
        "failed_count": 失败数量,
        "map": 地图保存结果,
        "characters": 角色保存结果列表
    }
    """
    data = request.get_json() or {}
    map_info = data.get('map', {})
    characters_info = data.get('characters', [])
    
    if not map_info.get('image_url') and not characters_info:
        return jsonify({'success': False, 'error': '至少需要提供地图或角色信息'}), 400
    
    if not save_all_assets:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        result = save_all_assets(map_info, characters_info)
        logger.info(f"批量保存素材完成: {result['success_count']}成功, {result['failed_count']}失败")
        return jsonify(result)
    except Exception as e:
        logger.error(f"批量保存素材失败: {e}")
        return jsonify({
            'success': False,
            'error': f'保存失败: {str(e)}'
        }), 500


@app.route('/api/assets/list-maps', methods=['GET'])
def list_map_assets_api():
    """
    获取所有地图素材列表
    
    返回：
    {
        "success": true,
        "assets": [
            {"asset_id": "...", "url": "...", "modified_at": "...", "size": ...},
            ...
        ]
    }
    """
    if not create_asset_manager:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        manager = create_asset_manager()
        assets = manager.list_map_assets()
        return jsonify({
            'success': True,
            'assets': assets
        })
    except Exception as e:
        logger.error(f"获取地图素材列表失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取失败: {str(e)}'
        }), 500


@app.route('/api/assets/list-characters', methods=['GET'])
def list_character_assets_api():
    """
    获取所有角色素材列表
    
    返回：
    {
        "success": true,
        "assets": [
            {"asset_id": "...", "character_name": "...", "emotion": "...", "url": "...", ...},
            ...
        ]
    }
    """
    if not create_asset_manager:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        manager = create_asset_manager()
        assets = manager.list_character_assets()
        return jsonify({
            'success': True,
            'assets': assets
        })
    except Exception as e:
        logger.error(f"获取角色素材列表失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取失败: {str(e)}'
        }), 500


@app.route('/api/assets/delete', methods=['POST'])
def delete_asset_api():
    """
    删除素材
    
    请求体：
    {
        "asset_id": "素材ID（文件名）",
        "asset_type": "map" 或 "character"（默认character）
    }
    
    返回：
    {
        "success": true,
        "message": "删除成功"
    }
    """
    data = request.get_json() or {}
    asset_id = data.get('asset_id', '')
    asset_type = data.get('asset_type', 'character')
    
    if not asset_id:
        return jsonify({'success': False, 'error': '素材ID不能为空'}), 400
    
    if not create_asset_manager:
        return jsonify({'success': False, 'error': '素材管理器未加载'}), 500
    
    try:
        manager = create_asset_manager()
        success = manager.delete_asset(asset_id, asset_type)
        
        if success:
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '素材不存在'
            }), 404
    except Exception as e:
        logger.error(f"删除素材失败: {e}")
        return jsonify({
            'success': False,
            'error': f'删除失败: {str(e)}'
        }), 500


# ==================== AI图片提示词生成 API ====================

@app.route('/api/image-prompts/generate-map', methods=['POST'])
def generate_map_image_prompt():
    """
    生成地图/场景背景的AI图片提示词
    
    请求体：
    {
        "text": "剧情文本",
        "scene": "场景名称（可选）"
    }
    
    返回：
    {
        "success": true,
        "prompt": "AI图片生成提示词",
        "negative_prompt": "负面提示词",
        "scene_type": "场景类型",
        "time_of_day": "时间",
        "weather": "天气"
    }
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    scene_name = data.get('scene', '')
    
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400
    
    if not generate_map_prompt:
        return jsonify({'success': False, 'error': '提示词生成器未加载'}), 500
    
    try:
        result = generate_map_prompt(text, scene_name)
        logger.info(f"生成地图提示词: {result['prompt'][:50]}...")
        
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"生成地图提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/image-prompts/generate-character', methods=['POST'])
def generate_character_image_prompt():
    """
    生成角色人物的AI图片提示词（透明底）
    
    请求体：
    {
        "character": {
            "name": "角色名称",
            "description": "角色描述（可选）",
            "role": "角色类型（可选）",
            "emotion": "情绪（可选，默认neutral）"
        },
        "transparent": true  // 是否需要透明背景（默认true）
    }
    
    返回：
    {
        "success": true,
        "prompt": "AI图片生成提示词",
        "negative_prompt": "负面提示词",
        "character_name": "角色名称",
        "emotion": "情绪",
        "transparent": true
    }
    """
    data = request.get_json() or {}
    character_info = data.get('character', {})
    transparent = data.get('transparent', True)
    
    if not character_info or not character_info.get('name'):
        return jsonify({'success': False, 'error': '角色信息不能为空'}), 400
    
    if not generate_character_prompt:
        return jsonify({'success': False, 'error': '提示词生成器未加载'}), 500
    
    try:
        result = generate_character_prompt(character_info, transparent)
        logger.info(f"生成角色提示词: {result['character_name']} - {result['prompt'][:50]}...")
        
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"生成角色提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/image-prompts/generate-all', methods=['POST'])
def generate_all_image_prompts():
    """
    生成所有图片提示词（地图 + 所有角色）
    
    请求体：
    {
        "text": "剧情文本",
        "characters": [
            {"name": "角色1", "description": "...", "emotion": "happy"},
            {"name": "角色2", "description": "...", "emotion": "neutral"}
        ]
    }
    
    返回：
    {
        "success": true,
        "map": {地图提示词信息},
        "characters": [角色提示词信息列表],
        "scene_type": "场景类型",
        "total_characters": 角色数量
    }
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    characters = data.get('characters', [])
    
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400
    
    if not generate_all_prompts:
        return jsonify({'success': False, 'error': '提示词生成器未加载'}), 500
    
    try:
        # 如果没有传入角色，先从文本中提取
        if not characters:
            characters = extract_characters_from_text(text)
        
        result = generate_all_prompts(text, characters)
        logger.info(f"生成所有提示词: 场景={result['scene_type']}, 角色数={result['total_characters']}")
        
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"生成提示词失败: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/continue-story', methods=['POST'])
def continue_story():
    """故事续写：根据当前文本续写故事"""
    data = request.get_json() or {}
    text = data.get('text', '')

    logger.info(f"收到续写请求，文本长度: {len(text)}")

    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'}), 400

    provider = get_llm_provider()

    if not provider:
        return jsonify({
            'success': False,
            'error': 'AI提供者未配置，无法续写故事'
        }), 500

    prompt = f"""请根据以下故事内容，继续续写故事。

要求：
1. 保持原有故事的风格和语气
2. 续写内容要自然流畅，与原文衔接
3. 续写长度适中（约200-400字）
4. 只输出续写的内容，不要包含原文
5. 不要添加任何解释或说明

原文：
{text}

续写内容："""

    try:
        logger.info("开始AI故事续写...")
        result = provider.run(
            prompt=prompt,
            history=[],
            params={'temperature': 0.8, 'max_tokens': 1000}
        )

        if not result.get('success'):
            logger.warning("AI故事续写失败")
            return jsonify({
                'success': False,
                'error': 'AI续写失败'
            }), 500

        continued_text = result['text'].strip()
        
        if not continued_text:
            return jsonify({
                'success': False,
                'error': 'AI返回的续写内容为空'
            }), 500

        full_story = text + '\n\n' + continued_text

        logger.info(f"故事续写成功，续写长度: {len(continued_text)}")

        return jsonify({
            'success': True,
            'original_text': text,
            'continued_text': continued_text,
            'full_story': full_story
        })

    except Exception as e:
        logger.error(f"故事续写异常: {e}")
        return jsonify({
            'success': False,
            'error': f'续写失败: {str(e)}'
        }), 500


# ==================== 调试测试 API ====================

@app.route('/api/test/config', methods=['GET'])
def test_config():
    """测试配置加载"""
    if config:
        return jsonify({
            'success': True,
            'ARK_API_KEY_exists': bool(config.get('ARK_API_KEY')),
            'ARK_API_KEY_length': len(config.get('ARK_API_KEY', '')),
            'DOUBAO_IMAGE_URL': config.get('DOUBAO_IMAGE_URL'),
            'DOUBAO_IMAGE_MODEL': config.get('DOUBAO_IMAGE_MODEL'),
            'config_keys': list(config.all().keys())
        })
    else:
        return jsonify({'success': False, 'error': 'config is None'})


# ==================== 故事选择 API ====================

@app.route('/api/story/sample', methods=['GET'])
def get_sample_story():
    """
    获取示例故事（小红帽故事）
    
    返回：
    {
        "success": true,
        "story": "示例故事文本",
        "title": "故事标题"
    }
    """
    sample_story = """很久很久以前，在一个美丽的童话镇里，住着一个小女孩叫小红帽。有一天，妈妈让小红帽给住在森林深处的奶奶送蛋糕。

小红帽戴着红色的帽子，提着篮子出发了。她穿过村庄，走进了茂密的森林。

在森林里，小红帽遇到了一只大灰狼。大灰狼问她："小姑娘，你要去哪里呀？"

小红帽天真地回答："我要去奶奶家送蛋糕。"

大灰狼眼珠一转，想到了一个坏主意。他让小红帽去采花，自己却抄近路先到了奶奶家。"""
    
    return jsonify({
        'success': True,
        'story': sample_story,
        'title': '小红帽',
        'description': '经典童话小红帽的故事开头'
    })


# ==================== 豆包AI像素画风图片生成 API ====================

@app.route('/api/doubao/images/generate-pixel-background', methods=['POST'])
def generate_pixel_background_api():
    """
    使用豆包AI生成像素画风的背景图片
    
    请求体：
    {
        "scene_description": "场景描述",
        "api_key": "火山引擎方舟API Key（可选，不填则使用配置文件中的密钥）"
    }
    
    返回：
    {
        "success": true,
        "image_url": "生成的图片URL",
        "prompt": "使用的提示词"
    }
    """
    data = request.get_json() or {}
    scene_description = data.get('scene_description', '')
    api_key = data.get('api_key', '')
    
    # 如果没有传入API密钥，尝试从配置中获取
    if not api_key:
        api_key = config.get('ARK_API_KEY', '') if config else ''
    
    if not scene_description:
        return jsonify({'success': False, 'error': '场景描述不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_pixel_background:
        return jsonify({'success': False, 'error': '豆包图片生成器未加载'}), 500
    
    try:
        logger.info(f"开始使用豆包AI生成像素背景: {scene_description[:30]}...")
        result = generate_pixel_background(api_key, scene_description)
        
        if result.get('success'):
            logger.info(f"像素背景生成成功: {result['image_url']}")
            return jsonify({
                'success': True,
                'image_url': result['image_url'],
                'prompt': result['prompt'],
                'scene_description': scene_description
            })
        else:
            logger.error(f"像素背景生成失败: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"生成像素背景异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/doubao/images/generate-pixel-character', methods=['POST'])
def generate_pixel_character_api():
    """
    使用豆包AI生成像素画风的角色人物图片
    
    请求体：
    {
        "character_name": "角色名称",
        "character_description": "角色描述（可选）",
        "api_key": "火山引擎方舟API Key（可选，不填则使用配置文件中的密钥）"
    }
    
    返回：
    {
        "success": true,
        "image_url": "生成的图片URL",
        "prompt": "使用的提示词",
        "character_name": "角色名称"
    }
    """
    data = request.get_json() or {}
    character_name = data.get('character_name', '')
    character_description = data.get('character_description', '')
    api_key = data.get('api_key', '')
    
    # 如果没有传入API密钥，尝试从配置中获取
    if not api_key:
        api_key = config.get('ARK_API_KEY', '') if config else ''
    
    if not character_name:
        return jsonify({'success': False, 'error': '角色名称不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_pixel_character:
        return jsonify({'success': False, 'error': '豆包图片生成器未加载'}), 500
    
    try:
        logger.info(f"开始使用豆包AI生成像素角色: {character_name}")
        result = generate_pixel_character(api_key, character_name, character_description)
        
        if result.get('success'):
            logger.info(f"像素角色生成成功: {result['image_url']}")
            return jsonify({
                'success': True,
                'image_url': result['image_url'],
                'prompt': result['prompt'],
                'character_name': character_name,
                'character_description': character_description
            })
        else:
            logger.error(f"像素角色生成失败: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"生成像素角色异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/api/doubao/images/generate-all', methods=['POST'])
def generate_all_pixel_images_api():
    """
    使用豆包AI批量生成像素画风的背景和角色图片
    
    请求体：
    {
        "text": "故事文本",
        "characters": [
            {"name": "角色1", "description": "描述1"},
            {"name": "角色2", "description": "描述2"}
        ],
        "api_key": "火山引擎方舟API Key（可选）"
    }
    
    返回：
    {
        "success": true,
        "background": {"image_url": "...", "prompt": "..."},
        "characters": [{"name": "...", "image_url": "...", "prompt": "..."}, ...],
        "scene_type": "场景类型"
    }
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    characters_input = data.get('characters', [])
    api_key = data.get('api_key', '')
    
    # 如果没有传入API密钥，尝试从配置中获取
    if not api_key:
        api_key = config.get('ARK_API_KEY', '') if config else ''
    
    if not text:
        return jsonify({'success': False, 'error': '故事文本不能为空'}), 400
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API密钥不能为空'}), 400
    
    if not generate_pixel_background or not generate_pixel_character:
        return jsonify({'success': False, 'error': '豆包图片生成器未加载'}), 500
    
    try:
        # 1. 检测场景类型（用于返回信息，不用于生成图片）
        scene_type = detect_scene_from_text(text)
        
        # 2. 使用DeepSeek分析用户输入文本，生成背景图片提示词
        background_prompt = None
        if DeepSeekProvider:
            llm = get_llm_provider()
            if llm:
                # 提示DeepSeek从故事文本中提取场景描述
                analysis_prompt = f"""分析以下故事文本，提取其中的场景环境描述：

{text}

请输出详细的场景描述，包含地点、环境、氛围等信息，用于生成像素画风的背景图片。不要提及"童话镇"。输出格式：直接输出场景描述文本。"""
                
                try:
                    result = llm.call(analysis_prompt)
                    if result and result.get('text'):
                        background_prompt = result['text'].strip()
                        logger.info(f"DeepSeek分析结果: {background_prompt}")
                    else:
                        logger.warning("DeepSeek未返回有效结果")
                except Exception as e:
                    logger.warning(f"调用DeepSeek失败: {e}")
        
        # 如果DeepSeek未返回有效结果，使用通用场景描述（不再使用"童话镇广场"）
        if not background_prompt or background_prompt.strip() == '' or background_prompt == '童话镇广场':
            # 根据场景类型生成通用描述，避免使用"童话镇广场"
            scene_descriptions = {
                '森林': '神秘的森林，树木茂密，阳光透过树叶洒落',
                '城堡': '宏伟的城堡，高耸的塔楼，古老的城墙',
                '村庄': '宁静的村庄，茅草屋顶的小屋，蜿蜒的小路',
                '河流': '清澈的河流，河畔风光，芦苇摇曳',
            }
            background_prompt = scene_descriptions.get(scene_type, 'fantasy landscape with magical atmosphere')
            logger.info(f"使用通用场景描述: {background_prompt}")
        
        # 3. 生成背景图片（使用生成的提示词）
        logger.info(f"生成像素背景: {background_prompt}")
        background_result = generate_pixel_background(api_key, background_prompt)
        
        if not background_result.get('success'):
            return jsonify({
                'success': False,
                'error': f'背景生成失败: {background_result.get("error")}'
            }), 500
        
        # 4. 如果没有传入角色，从文本中提取
        characters = characters_input if characters_input else extract_characters_from_text(text)
        
        # 5. 生成角色图片
        character_images = []
        for char in characters:
            char_name = char.get('name', '')
            char_desc = char.get('description', '')
            
            logger.info(f"生成像素角色: {char_name}")
            char_result = generate_pixel_character(api_key, char_name, char_desc)
            
            if char_result.get('success'):
                character_images.append({
                    'name': char_name,
                    'image_url': char_result['image_url'],
                    'prompt': char_result['prompt'],
                    'description': char_desc,
                    'role': char.get('role', ''),
                    'position': char.get('position', {}),
                    'emotion': char.get('emotion', 'neutral')
                })
            else:
                logger.warning(f"角色 {char_name} 生成失败: {char_result.get('error')}")
                character_images.append({
                    'name': char_name,
                    'error': char_result.get('error', '生成失败'),
                    'description': char_desc
                })
        
        logger.info(f"批量像素图片生成完成: 背景1张, 角色{len(character_images)}张")
        
        return jsonify({
            'success': True,
            'background': {
                'image_url': background_result['image_url'],
                'prompt': background_result['prompt'],
                'scene_type': scene_type
            },
            'characters': character_images,
            'scene_type': scene_type,
            'total_characters': len(character_images)
        })
        
    except Exception as e:
        logger.error(f"批量生成像素图片异常: {e}")
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


# ==================== 错误处理 ====================
@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'API端点不存在'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500


# ==================== 启动配置 ====================
if __name__ == '__main__':
    print("=" * 50)
    print("童话镇多智能体系统")
    print("=" * 50)

    # 检查配置
    if config:
        valid, errors = config.validate()
        if not valid:
            print("警告: 配置验证失败")
            for err in errors:
                print(f"  - {err}")
            print("将使用模拟响应模式")
    else:
        print("警告: 配置模块不可用，将使用模拟响应模式")

    # 启动服务器
    print("\n启动Flask服务器...")
    print("后端地址: http://localhost:5000")
    print("前端地址: http://localhost:8080 (需要另外启动)")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)