"""
系统常量定义
所有业务相关的常量统一管理
"""
from typing import Dict, List, Tuple
from enum import Enum, auto


class CommandType(Enum):
    """指令类型枚举"""
    MOVE = "move"
    TALK = "talk"
    EMOTE = "emote"
    SCENE_CHANGE = "scene_change"
    WAIT = "wait"
    USE_ITEM = "use_item"


class ErrorCode(Enum):
    """错误码枚举"""
    SUCCESS = (0, "成功")
    INVALID_INPUT = (1001, "无效的输入")
    PROVIDER_ERROR = (2001, "AI服务错误")
    MEMORY_ERROR = (3001, "记忆存储错误")
    SCRIPT_NOT_FOUND = (4001, "剧本不存在")
    SCRIPT_PARSE_ERROR = (4002, "剧本解析错误")
    CHARACTER_NOT_FOUND = (4003, "角色不存在")
    RATE_LIMIT_EXCEEDED = (5001, "请求频率超限")
    INTERNAL_ERROR = (9001, "内部服务器错误")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class Constants:
    """系统常量"""

    # ========== 角色相关 ==========
    DEFAULT_CHARACTER = "assistant"
    MAX_CHARACTERS = 100
    MAX_CHARACTER_NAME_LEN = 50

    # ========== 剧本相关 ==========
    MAX_SCRIPT_LENGTH = 50000
    MAX_EVENTS_PER_SCRIPT = 500
    MAX_SCENES_PER_SCRIPT = 50

    # ========== 记忆相关 ==========
    MAX_MEMORY_ENTRIES = 1000
    DEFAULT_MEMORY_WINDOW = 10
    MAX_MEMORY_TOKENS = 4000

    # ========== API 相关 ==========
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # ========== 成本估算 ==========
    # 每千token价格（美元）- 仅用于估算
    DEFAULT_COST_PER_1K = 0.002
    COST_MULTIPLIER = 7.2  # 美元转人民币

    # ========== 指令类型 ==========
    COMMAND_TYPES: List[str] = [
        "move", "talk", "emote", "scene_change", "wait", "use_item"
    ]

    # ========== 角色动作 ==========
    CHARACTER_ACTIONS: List[str] = [
        "idle", "walk", "run", "sit", "stand", "wave", "nod", "shake_head"
    ]

    # ========== 情感状态 ==========
    EMOTIONS: List[str] = [
        "neutral", "happy", "sad", "angry", "surprised", "scared", "love", "jealous"
    ]

    # ========== 场景类型 ==========
    SCENE_TYPES: List[str] = [
        "forest", "castle", "village", "cottage", "palace", "garden", "market"
    ]

    # ========== Prompt 模板 ==========
    PROMPT_TEMPLATES: Dict[str, str] = {
        "parse_script": """
你是一个专业的剧本编剧。请将以下小说内容转换为结构化的剧本事件列表。

输出格式要求：
[
    {{"character": "角色名", "action": "动作类型", "target": "目标（可选）", "line": "台词（可选）"}}
]

动作类型只能是：move（移动）、talk（说话）、emote（表情）、scene_change（场景切换）

小说内容：
{novel_text}
""",
        "character_response": """
你是{character_name}。{character_description}

当前场景：{scene}
周围角色：{nearby_characters}

用户对你说：{user_message}

请以{character_name}的身份回应，保持角色性格一致。
"""
    }

    # ========== 文件限制 ==========
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".txt", ".json", ".md"}

    # ========== 缓存配置 ==========
    CACHE_TTL = 300  # 5分钟
    CACHE_MAX_SIZE = 1000

    # ========== 安全配置 ==========
    RATE_LIMIT = 60  # 每分钟最大请求数
    RATE_LIMIT_WINDOW = 60  # 窗口期（秒）


class HttpStatus:
    """HTTP 状态码"""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500


class ResponseMessages:
    """响应消息模板"""
    SUCCESS = "操作成功"
    CREATED = "创建成功"
    UPDATED = "更新成功"
    DELETED = "删除成功"

    ERROR_INVALID_INPUT = "输入参数无效"
    ERROR_NOT_FOUND = "资源不存在"
    ERROR_UNAUTHORIZED = "未授权访问"
    ERROR_FORBIDDEN = "无权执行此操作"
    ERROR_INTERNAL = "服务器内部错误"