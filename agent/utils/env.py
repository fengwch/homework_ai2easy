"""
安全加载 .env：解析失败时仅打日志不抛错，避免单行格式问题导致进程退出。
"""
from pathlib import Path
from typing import Optional, Union


def safe_load_dotenv(path: Optional[Union[str, Path]] = None) -> bool:
    """
    加载 .env 文件。若某行无法解析（如含未引号的 =），只打警告并继续，不抛异常。
    path: 可为 .env 路径；为 None 时由 python-dotenv 按默认规则查找。
    返回是否成功加载（未抛错即视为成功）。
    """
    try:
        from dotenv import load_dotenv
        if path is not None:
            load_dotenv(Path(path))
        else:
            load_dotenv()
        return True
    except Exception as e:
        try:
            import logging
            logging.getLogger("ai_agent.env").warning(
                "无法完整解析 .env 文件（请检查含等号的值是否用引号包裹）: %s", e
            )
        except Exception:
            pass
        return False
