"""统一日志配置模块。

提供 setup_logging() 一次性配置所有 logger，包括：
- 统一的日志格式（时间戳 + 级别 + 模块 + request_id + 消息）
- 仅文件输出（logs/backend.log）
- 第三方 logger 降级为 WARNING
- request_id 通过 contextvars 注入到日志格式中
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar
from pathlib import Path

# 用于在异步请求中传递 request_id
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class _RequestIdFilter(logging.Filter):
    """将 request_id 注入到日志记录中。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("")
        return True


# 统一日志格式
LOG_FORMAT = (
    "[%(asctime)s] "           # 时间戳
    "[%(levelname)-8s] "       # 级别（左对齐 8 字符）
    "[%(name)s] "              # 模块名
    "[%(request_id)s] "        # request_id
    "%(message)s"              # 消息
)

# 时间戳格式（精确到毫秒）
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file: str = "logs/backend.log", level: str = "INFO") -> None:
    """初始化统一日志配置。

    Args:
        log_file: 日志文件路径。
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）。
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            },
        },

        "filters": {
            "request_id": {
                "()": "app.logging_config._RequestIdFilter",
            },
        },

        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(log_path),
                "encoding": "utf-8",
                "formatter": "standard",
                "filters": ["request_id"],
            },
        },

        "root": {
            "level": level,
            "handlers": ["file"],
        },

        # 第三方 logger 强制 WARNING，消除噪音
        "loggers": {
            "uvicorn": {"level": "WARNING", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": False},
            "uvicorn.error": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
        },
    })
