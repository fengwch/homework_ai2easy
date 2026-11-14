"""异常层级。设计原则：错误信息必须可操作，禁止静默放行。"""


class HomeworkError(Exception):
    """所有本项目异常的基类。"""


class ExtractionError(HomeworkError):
    """抽取失败：模型没返回合法结构，或原文为空。"""


class NeedsConfirmation(HomeworkError):
    """存在阻断型待确认项，拒绝出图。"""


class LayoutError(HomeworkError):
    """版面约束不满足：项数超骨架留白、骨架边距不达标等。"""


class FontError(HomeworkError):
    """找不到中文字体，或字体不覆盖所需汉字。"""


class ApiError(HomeworkError):
    """远端接口错误。message 必须包含下一步动作，不得只说「失败」。"""


class ConfigError(HomeworkError):
    """配置文件不合法或含未知键。未知键必须报错，不能静默忽略。"""
