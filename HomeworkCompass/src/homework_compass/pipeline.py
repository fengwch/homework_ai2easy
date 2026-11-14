"""对外 API：四个动词——parse_homework / correct / dismiss / render。

本模块只编排，不含规则：一条校验判据、一处落位计算都不许写在这里，
否则「库的第一个使用者是 CLI、第二个是 Web」就变成一句空话。

降级路径（不花钱、不联网）是默认路径：extractor 不传就用 NaiveExtractor。
想调真实模型的使用方必须显式注入 LlmExtractor —— 让花钱成为显式决定。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from homework_compass.errors import NeedsConfirmation
from homework_compass.layout import compose as compose_mod
from homework_compass.layout.skeleton import A4_DPI, get_skeleton
from homework_compass.layout import themes as themes_mod
from homework_compass.models import (
    ParsedHomework, RenderResult, SourceKind, from_json, to_json,
)
from homework_compass.parsing.extract import (
    DEFAULT_OCR_MODEL, Extractor, NaiveExtractor, ocr_to_text,
)
from homework_compass.parsing.validate import (
    correct as _correct,
    dismiss as _dismiss,
    validate,
)

__all__ = ["parse_homework", "correct", "dismiss", "render", "save_hw", "load_hw",
           "text_from_image"]


def parse_homework(raw_text: str, *, extractor: Extractor | None = None,
                   date: str = "", name: str = "",
                   source_kind: SourceKind = SourceKind.TEXT) -> ParsedHomework:
    ex = extractor or NaiveExtractor()
    return validate(raw_text, ex(raw_text, date=date, name=name),
                    date=date, name=name, source_kind=source_kind)


def correct(hw: ParsedHomework, seq: int, field: str, value: str) -> ParsedHomework:
    return _correct(hw, seq, field, value)


def dismiss(hw: ParsedHomework, pending_id: str) -> ParsedHomework:
    return _dismiss(hw, pending_id)


def text_from_image(image: Path, *, model: str | None = None) -> tuple[str, SourceKind]:
    """照片 -> 文本。返回 kind 是为了让调用方明白：这条路必须过家长确认。

    `ocr_to_text` 在模块顶层 import（不是函数体内），否则它不可被测试替换。
    """
    return ocr_to_text(image, model=model or DEFAULT_OCR_MODEL), SourceKind.OCR


def resolve_base(skin: str, base_dir: Path) -> Path | None:
    """按主题皮肤找对应的底图；目录里没有就用占位图。

    主题底图由 tools/gen_bases.py 生成，文件名 <theme>_quest-map.png。
    只有文件真实存在才返回，否则 None（走占位），不因为缺某张图就出不了图。
    """
    t = themes_mod.get_theme(skin)
    if t is None:
        return None
    p = Path(base_dir) / t.base_file
    return p if p.is_file() else None


def render(hw: ParsedHomework, *, skeleton: str = "quest-map", skin: str = "dinosaur",
           base: Path | None = None, base_dir: Path = Path("assets/bases"),
           out_dir: Path = Path("out"),
           panel_alpha: int = 190,
           fonts: Sequence[str] | None = None) -> RenderResult:
    """pending 非空就拒绝出图（spec §5.3 的闸门），版面问题则如实带进 issues。"""
    if hw.pending:
        raise NeedsConfirmation(
            "存在待家长确认项，按「宁缺毋编」拒绝出图：\n"
            + "\n".join(f"  - [{p.reason.value}] {p.text}" for p in hw.pending))
    skel = get_skeleton(skeleton)
    base_image = None
    if base is not None:
        with Image.open(base) as im:      # 句柄不挂到出图之后：Windows 上会锁文件
            base_image = im.copy()
    elif resolve_base(skin, base_dir) is not None:
        with Image.open(resolve_base(skin, base_dir)) as im:
            base_image = im.copy()
    img, issues = compose_mod.compose(hw, skel, skin=skin, base=base_image,
                                      panel_alpha=panel_alpha, fonts=fonts)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"homework_{_slug(hw.date)}_{_slug(skeleton)}_{_slug(skin)}.png"
    img.save(path, format="PNG", dpi=(A4_DPI, A4_DPI))
    return RenderResult(path=path, width=img.size[0], height=img.size[1],
                        dpi=(A4_DPI, A4_DPI), issues=issues,
                        used_placeholder=base_image is None)


def _slug(text: str) -> str:
    """文件名只留安全字符：date 可能来自模型或 --date，含 `/` 或 `..` 会写到 out_dir 之外。"""
    safe = re.sub(r"[^\w-]+", "-", str(text or "")).strip("-")
    return safe or "undated"


def save_hw(hw: ParsedHomework, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_json(hw), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


def load_hw(path: Path) -> ParsedHomework:
    return from_json(json.loads(Path(path).read_text(encoding="utf-8")))
