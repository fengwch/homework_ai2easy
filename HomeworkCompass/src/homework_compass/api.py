"""HomeworkCompass HTTP 服务：把 pipeline 的 5 个动词包成 REST。

状态不落服务端：每次请求带完整 ParsedHomework JSON 往返（家长点「确认」
时前端把改过的 hw 原样发回来）。这样服务可多实例、无 Redis，且与
「pending 非空拒绝出图」的闸门天然一致——闸门在 pipeline.render 里。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from homework_compass import (
    ApiError, ExtractionError, FontError, HomeworkError, LayoutError,
    NeedsConfirmation, correct, dismiss, parse_homework, render, text_from_image,
)
from homework_compass.parsing.extract import LlmExtractor
from homework_compass.parsing.validate import drop_item
from homework_compass.errors import ConfigError
from homework_compass.layout.skeleton import SKELETONS
from homework_compass.models import from_json, to_json

app = FastAPI(title="HomeworkCompass", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

OUT_DIR = Path(tempfile.gettempdir()) / "homework-compass"
from homework_compass.layout.themes import get_themes, theme_for_interests  # noqa: E402

SKINS = [t.key for t in get_themes()]
# 主题底图目录：优先 HW_BASE_DIR（部署时指向解压出来的 assets/bases），
# 否则按源码布局回退到仓库的 assets/bases。
_BASE_DIR = Path(os.environ.get("HW_BASE_DIR") or
                 Path(__file__).resolve().parents[2] / "assets" / "bases")

_ERROR_STATUS = {
    NeedsConfirmation: 409, ConfigError: 500, FontError: 500, LayoutError: 500,
    ExtractionError: 502, ApiError: 502,
}


class ParseRequest(BaseModel):
    text: str
    date: str = ""
    name: str = ""
    llm: bool = False          # True 时用 qwen-plus 结构化（花钱，但条目质量高得多）


class CorrectRequest(BaseModel):
    hw: dict
    seq: int
    field: str
    value: str


class DropItemRequest(BaseModel):
    hw: dict
    seq: int


class HomeworkPatchRequest(BaseModel):
    """家长可直接改的顶层字段。slogan 不走 correct()：它是标题文案，不参与原文溯源。"""

    hw: dict
    slogan: str | None = None
    student_name: str | None = None
    reward: str | None = None


class DismissRequest(BaseModel):
    hw: dict
    pending_id: str


class RenderRequest(BaseModel):
    hw: dict
    skeleton: str = "quest-map"
    skin: str = "dinosaur"


def _run(fn, *args, **kwargs):
    """pipeline 异常 -> 带中文原因的 HTTP 错误；未预期的照常 500。"""
    try:
        return fn(*args, **kwargs)
    except HomeworkError as e:
        status = next((s for cls, s in _ERROR_STATUS.items() if isinstance(e, cls)), 500)
        raise HTTPException(status, str(e)) from e


@app.get("/api/health")
def health():
    return {"code": 0, "data": {"ok": True}}


@app.post("/api/parse/image")
async def parse_image_endpoint(file: UploadFile = File(...), date: str = "",
                               name: str = "", llm: bool = False):
    return await parse_image(file, date, name, llm=llm)


@app.get("/api/options")
def options():
    return {"code": 0, "data": {
        "skeletons": sorted(SKELETONS),
        "skins": SKINS,
        "themes": [{"key": t.key, "cn": t.cn, "interests": t.interest_list} for t in get_themes()],
    }}


@app.get("/api/themes/suggest")
def suggest(interests: str = ""):
    """按孩子兴趣返回推荐主题顺序。interests 逗号分隔。"""
    tags = [x.strip() for x in interests.split(",") if x.strip()]
    ordered = theme_for_interests(tags)
    by_key = {t.key: {"key": t.key, "cn": t.cn, "interests": t.interest_list} for t in get_themes()}
    return {"code": 0, "data": [by_key[k] for k in ordered]}


@app.post("/api/parse")
def parse(req: ParseRequest):
    # 默认走离线兜底（不花钱）；前端传 llm=true 才走大模型。
    extractor = LlmExtractor() if req.llm else None
    hw = _run(parse_homework, req.text, date=req.date, name=req.name, extractor=extractor)
    return {"code": 0, "data": to_json(hw)}


async def parse_image(file: UploadFile, date: str = "", name: str = "",
                      llm: bool = False):
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        text, kind = _run(text_from_image, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    hw = _run(parse_homework, text, date=date, name=name, source_kind=kind,
              extractor=LlmExtractor() if llm else None)
    # OCR 文本一并返回：家长要核对识别结果（方案文档「OCR 置信度低」状态）
    return {"code": 0, "data": {**to_json(hw), "ocr_text": text}}


@app.post("/api/correct")
def do_correct(req: CorrectRequest):
    hw = _run(from_json, req.hw)
    return {"code": 0, "data": to_json(_run(correct, hw, req.seq, req.field, req.value))}


@app.post("/api/dismiss")
def do_dismiss(req: DismissRequest):
    hw = _run(from_json, req.hw)
    return {"code": 0, "data": to_json(_run(dismiss, hw, req.pending_id))}


@app.post("/api/drop")
def do_drop(req: DropItemRequest):
    return {"code": 0, "data": to_json(_run(drop_item, _run(from_json, req.hw), req.seq))}


@app.post("/api/patch")
def do_patch(req: HomeworkPatchRequest):
    """改标题口号/姓名：直接写回 ParsedHomework，再交给 render 排版。"""
    hw = _run(from_json, req.hw)
    if req.slogan is not None:
        hw.slogan = req.slogan.strip()
    if req.student_name is not None:
        hw.student_name = req.student_name.strip()
    if req.reward is not None:
        hw.reward = req.reward.strip()
    return {"code": 0, "data": to_json(hw)}


@app.post("/api/render")
def do_render(req: RenderRequest):
    hw = _run(from_json, req.hw)
    result = _run(render, hw, skeleton=req.skeleton, skin=req.skin,
                   base_dir=_BASE_DIR, out_dir=OUT_DIR)
    return {"code": 0, "data": {
        "url": f"/api/image/{result.path.name}",
        "width": result.width, "height": result.height, "dpi": result.dpi[0],
        "used_placeholder": result.used_placeholder,
        "issues": [{"zone": i.zone, "text": i.text, "reason": i.reason} for i in result.issues],
    }}


@app.get("/api/image/{name}")
def image(name: str):
    path = (OUT_DIR / name).resolve()
    if path.parent != OUT_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "图片不存在")
    return FileResponse(path, media_type="image/png")
