"""
配置管理模块
负责加载环境变量、提供配置访问接口
"""
import os
from typing import Any, Optional, Dict
from pathlib import Path
from dotenv import load_dotenv
import json


class Config:
    """
    配置管理类 - 单例模式
    统一管理所有环境配置，提供类型安全的访问方法
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 加载 .env 文件 - 从 backend 目录加载
        backend_dir = Path(__file__).parent.parent  # config 目录的父目录就是 backend
        env_path = backend_dir / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # 尝试从当前工作目录加载
            load_dotenv()

        self._config: Dict[str, Any] = {}
        self._load_config()
        self._initialized = True

    def _load_config(self):
        """加载所有配置项"""

        # ========== API 配置 ==========
        self._config['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', '')
        self._config['DEEPSEEK_BASE_URL'] = os.getenv(
            'DEEPSEEK_BASE_URL',
            'https://api.deepseek.com/v1'
        )
        self._config['DEEPSEEK_MODEL'] = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

        # ========== 豆包 API 配置 ==========
        self._config['ARK_API_KEY'] = os.getenv('ARK_API_KEY', '')
        self._config['DOUBAO_IMAGE_URL'] = os.getenv(
            'DOUBAO_IMAGE_URL',
            'https://ark.cn-beijing.volces.com/api/v3/images/generations'
        )
        self._config['DOUBAO_IMAGE_MODEL'] = os.getenv(
            'DOUBAO_IMAGE_MODEL',
            'doubao-seedream-4-5-251128'
        )

        # ========== 系统配置 ==========
        self._config['DEBUG'] = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
        self._config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
        self._config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

        # ========== 记忆配置 ==========
        self._config['DEFAULT_MEMORY_LEN'] = int(os.getenv('DEFAULT_MEMORY_LEN', '10'))
        self._config['MAX_HISTORY_TOKENS'] = int(os.getenv('MAX_HISTORY_TOKENS', '4000'))
        self._config['MEMORY_SUMMARY_THRESHOLD'] = int(os.getenv('MEMORY_SUMMARY_THRESHOLD', '20'))

        # ========== 性能配置 ==========
        self._config['REQUEST_TIMEOUT'] = int(os.getenv('REQUEST_TIMEOUT', '60'))
        self._config['MAX_RETRIES'] = int(os.getenv('MAX_RETRIES', '3'))
        self._config['RETRY_DELAY'] = float(os.getenv('RETRY_DELAY', '1.0'))
        self._config['MAX_CONCURRENT'] = int(os.getenv('MAX_CONCURRENT', '10'))

        # ========== 模型参数 ==========
        self._config['DEFAULT_TEMPERATURE'] = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))
        self._config['DEFAULT_MAX_TOKENS'] = int(os.getenv('DEFAULT_MAX_TOKENS', '2000'))

        # ========== 剧本配置 ==========
        self._config['MAX_SCRIPT_LENGTH'] = int(os.getenv('MAX_SCRIPT_LENGTH', '50000'))
        self._config['MAX_EVENTS_PER_SCRIPT'] = int(os.getenv('MAX_EVENTS_PER_SCRIPT', '500'))

        # ========== 成本配置 ==========
        self._config['COST_PER_1K_TOKENS'] = json.loads(
            os.getenv('COST_PER_1K_TOKENS',
                      '{"deepseek-chat": 0.001, "gpt-3.5-turbo": 0.002, "gpt-4": 0.03}')
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)

    def __getattr__(self, name: str) -> Any:
        """支持点语法访问"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"Config has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        """支持字典语法访问"""
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        return key in self._config

    def all(self) -> Dict[str, Any]:
        """获取所有配置（用于调试）"""
        # 隐藏敏感信息
        safe_config = self._config.copy()
        if 'DEEPSEEK_API_KEY' in safe_config:
            safe_config['DEEPSEEK_API_KEY'] = '***HIDDEN***'
        if 'DOUBAO_API_KEY' in safe_config:
            safe_config['DOUBAO_API_KEY'] = '***HIDDEN***'
        return safe_config

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证必要配置是否存在

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 必要配置检查（至少需要一个API密钥）
        deepseek_key = self.get('DEEPSEEK_API_KEY')
        doubao_key = self.get('DOUBAO_API_KEY')
        
        if not deepseek_key or deepseek_key == '':
            errors.append("Missing required config: DEEPSEEK_API_KEY")

        return len(errors) == 0, errors


# 全局单例实例
config = Config()
