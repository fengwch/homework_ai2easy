"""字体解析 + 字形覆盖探针。

只做「文件存在」检查是不够的：路径存在不代表它能画中文，
缺字时 Pillow 会安静地画出豆腐块或空白，图上看不出来、程序不报错，
直到打印出来才发现整张纸缺了「签字」两个字。
"""

from __future__ import annotations

import os

from collections.abc import Sequence
from pathlib import Path

from PIL import ImageFont

from homework_compass.errors import FontError

DEFAULT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",                  # macOS 14 及更早
    "/System/Library/Fonts/Hiragino Sans GB.ttc",          # macOS 26 实测可用
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    # 非 macOS 常见路径：Linux 发行版与 CI 镜像
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

# 探针取日常作业里真会出现的字，不是 "abcdefghijklmnopqrstuvwxyz"。
# 「签」「卡」「册」这类字最容易被供应商字体子集化掉。
SAMPLE_GLYPHS = "今日作业数学语文英语练习册家长签字打卡彩泥剪刀"

# 解析期探针字号：够大能看出豆腐块，又不必按目标字号渲染。
PROBE_PX = 40


def _bitmap(f: ImageFont.FreeTypeFont, ch: str) -> tuple[tuple[int, int], bytes]:
    mask = f.getmask(ch, mode="L")
    return mask.size, bytes(mask)


def check_glyph_coverage(f: ImageFont.FreeTypeFont, samples: str = SAMPLE_GLYPHS) -> None:
    """两个判据：墨迹非空；不同汉字不能画出一模一样的东西（豆腐块的特征）。"""
    for ch in samples:
        size, data = _bitmap(f, ch)
        if not size or not size[0] or not size[1] or not any(data):
            raise FontError(
                f"字形覆盖探针失败：字体不覆盖「{ch}」（渲染结果空白），无法出图。")
    first = _bitmap(f, samples[0])[1]
    for ch in samples[1:]:
        if _bitmap(f, ch)[1] == first:
            raise FontError(
                f"字形覆盖探针失败：「{ch}」与「{samples[0]}」渲染完全相同，"
                "几乎可以断定是 .notdef 豆腐块。请更换字体。")


def resolve_font_path(candidates: Sequence[str] | None = None) -> str:
    """按优先级挑第一个「真的能画中文」的字体，不是第一个存在的文件。

    回退链里混进一个缺汉字的字体时（路径存在、渲染是豆腐块），
    直接返回它会让 load_font 当场炸掉，明明下一个候选是好的。

    显式 candidates 优先；否则 HW_FONT 环境变量排在最前（部署时把字体随包发，
    不依赖服务器装没装中文字体），其次才是系统常见路径。
    """
    if candidates:
        tried = list(candidates)
    else:
        tried = list(DEFAULT_CANDIDATES)
        env_font = (os.environ.get("HW_FONT") or "").strip()
        if env_font:
            tried.insert(0, env_font)
    problems: list[str] = []
    for p in tried:
        if not Path(p).is_file():
            problems.append(f"{p}（不存在）")
            continue
        try:
            check_glyph_coverage(ImageFont.truetype(p, size=PROBE_PX))
        except (FontError, OSError) as e:
            problems.append(f"{p}（{e}）")
            continue
        return p
    raise FontError(
        "找不到可用的中文字体，无法保证「正文≥14pt 清晰可读」。已尝试：" + "、".join(problems))


_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
# 默认字体解析一次就够：resolve 会真的加载字体试渲染，每次 load_font 重跑它
# 等于每取一个字号就多花一次字体加载。clear_cache() 时一并复位。
_DEFAULT_PATH: str | None = None


def load_font(px: int, *, path: str | None = None) -> ImageFont.FreeTypeFont:
    global _DEFAULT_PATH
    px = max(int(px), 8)
    if path is None:
        _DEFAULT_PATH = _DEFAULT_PATH or resolve_font_path()
        path = _DEFAULT_PATH
    key = (path, px)
    if key not in _CACHE:
        f = ImageFont.truetype(path, size=px)
        check_glyph_coverage(f)      # 指定 path 时绕过了 resolve，这里补一次
        _CACHE[key] = f
    return _CACHE[key]


def clear_cache() -> None:
    """测试与配置变更用；生产代码不该调它。"""
    global _DEFAULT_PATH
    _DEFAULT_PATH = None
    _CACHE.clear()
