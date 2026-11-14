"""每日作业目标生成器核心包。

库只返回结构，不做任何终端交互（CLI 在 `homework_compass.cli`）。
对外只暴露 `pipeline` 的动词、数据模型与异常层级；内部模块（parsing / layout /
config / llm_client）是实现细节，不进 `__all__`。
"""

from homework_compass.errors import (
    ApiError, ConfigError, ExtractionError, FontError, HomeworkError, LayoutError,
    NeedsConfirmation,
)
from homework_compass.models import (
    HomeworkItem, ParsedHomework, PendingItem, RenderResult,
)
from homework_compass.pipeline import (
    correct, dismiss, load_hw, parse_homework, render, save_hw, text_from_image,
)

__all__ = ["parse_homework", "correct", "dismiss", "render", "save_hw", "load_hw",
           "text_from_image", "ParsedHomework", "HomeworkItem", "PendingItem",
           "RenderResult", "HomeworkError", "ExtractionError", "NeedsConfirmation",
           "LayoutError", "FontError", "ApiError", "ConfigError"]
