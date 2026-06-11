"""
日志配置模块
提供统一的日志管理
"""
import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .settings import config


class JSONFormatter(logging.Formatter):
    """
    JSON格式化器 - 用于生产环境
    输出结构化日志，便于日志分析
    """

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        if hasattr(record, 'latency'):
            log_entry['latency'] = record.latency

        # 异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class SimpleFormatter(logging.Formatter):
    """
    简单格式化器 - 用于开发环境
    输出易读的文本格式
    """

    def format(self, record):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 基础格式
        log_line = f"[{timestamp}] {record.levelname:8s} [{record.name}] {record.getMessage()}"

        # 添加额外字段
        extra_info = []
        if hasattr(record, 'request_id'):
            extra_info.append(f"req_id={record.request_id}")
        if hasattr(record, 'latency'):
            extra_info.append(f"latency={record.latency}ms")

        if extra_info:
            log_line += f" ({', '.join(extra_info)})"

        return log_line


def setup_logging():
    """
    配置全局日志系统
    根据 DEBUG 模式选择不同的格式化器
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)

    # 根据 DEBUG 模式选择格式化器
    if config.DEBUG:
        formatter = SimpleFormatter()
    else:
        formatter = JSONFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # 日志配置完成
    logger = get_logger(__name__)
    logger.info(f"Logging configured - level: {config.LOG_LEVEL}, debug: {config.DEBUG}")

    if config.DEBUG:
        logger.debug("Debug mode enabled")


class LoggerAdapter(logging.LoggerAdapter):
    """
    日志适配器 - 支持添加上下文信息
    """

    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        # 处理额外字段
        if self.extra:
            for key, value in self.extra.items():
                if key not in kwargs:
                    kwargs[key] = value
        return msg, kwargs


def get_logger(name: str, **context) -> logging.Logger:
    """
    获取日志实例

    Args:
        name: 日志名称
        context: 上下文信息（如 request_id）

    Returns:
        logging.Logger 实例
    """
    logger = logging.getLogger(name)

    if context:
        return LoggerAdapter(logger, context)

    return logger


class LogContext:
    """
    日志上下文管理器 - 用于临时添加上下文
    使用方式:
        with LogContext(request_id="123"):
            logger.info("处理请求")
    """

    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_context = {}

    def __enter__(self):
        # 保存并应用上下文
        for key, value in self.context.items():
            if hasattr(logging, key):
                self.old_context[key] = getattr(logging, key)
                setattr(logging, key, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原上下文
        for key, value in self.old_context.items():
            setattr(logging, key, value)