"""
统一日志模块：输出到控制台与 logs 目录，日志级别由环境变量 LOG_LEVEL 控制。

用法：
    from utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("something")

环境变量：
    LOG_LEVEL: DEBUG | INFO | WARNING | ERROR，默认 INFO
    LOG_DIR: 日志目录名（相对项目根）或绝对路径，默认 logs
"""
import logging
import os
from pathlib import Path
from typing import Optional

_CONFIGURED = False

# 项目根目录（agent）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _configure_root_logger() -> None:
    """按 LOG_LEVEL、LOG_DIR 配置 root logger，控制台 + 文件，只在首次调用时生效。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = os.getenv("LOG_DIR", "logs").strip()
    if not Path(log_dir).is_absolute():
        log_dir = _PROJECT_ROOT / log_dir
    else:
        log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    # 抑制 dotenv 解析单行失败时的警告（如 .env 某行含未引号的 =）
    for _name in ("dotenv", "dotenv.main"):
        logging.getLogger(_name).setLevel(logging.ERROR)

    if not root.handlers:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(fmt)
        root.addHandler(console)

        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(fmt)
            root.addHandler(file_handler)
        except OSError:
            pass

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取带统一格式的 logger，名称可为模块名。"""
    _configure_root_logger()
    return logging.getLogger(name or "ai_agent")
