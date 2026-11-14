"""从 campaign 配置与本地素材推导推广主题。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_campaign(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or project_root() / "config" / "xhs_campaign.yaml"
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _introduce_dir(campaign: Dict[str, Any]) -> Path:
    raw = campaign.get("introduce_docs_dir") or "../docs/introduce"
    p = (project_root() / raw).resolve()
    if p.is_dir():
        return p
    # 绝对路径或另一常见布局
    alt = Path("/Users/fengwanchang/Documents/homework_ai2easy/docs/introduce")
    if alt.is_dir():
        return alt
    return p


def read_introduce_snippet(campaign: Dict[str, Any], filename: str = "06-小红书软文素材与模板.md") -> str:
    d = _introduce_dir(campaign)
    fp = d / filename
    if not fp.is_file():
        return ""
    return fp.read_text(encoding="utf-8", errors="replace")[:8000]


def find_latest_video_bundle() -> Optional[Tuple[Path, Dict[str, Any]]]:
    """
    选取 uploads/vedio 下修改时间最新的子目录，解析 info.md 中 JSON 块（若有）。
    返回 (目录, 解析出的元数据 dict)。
    """
    root = project_root() / "uploads" / "vedio"
    if not root.is_dir():
        return None
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    latest = max(dirs, key=lambda p: p.stat().st_mtime)
    meta: Dict[str, Any] = {"dir": str(latest), "info_md": ""}
    info = latest / "info.md"
    if info.is_file():
        text = info.read_text(encoding="utf-8", errors="replace")
        meta["info_md"] = text
        m2 = re.search(r"## 调用参数\s*\n*```json\s*([\s\S]*?)\s*```", text)
        if m2:
            try:
                meta["params"] = json.loads(m2.group(1))
            except json.JSONDecodeError:
                meta["params"] = {}
        if "params" not in meta:
            m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if m:
                try:
                    meta["params"] = json.loads(m.group(1))
                except json.JSONDecodeError:
                    meta["params"] = {}
    return latest, meta


def resolve_theme_context(campaign: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    合并 campaign 与最新视频素材元数据，供 composer 使用。
    """
    c = campaign or load_campaign()
    ctx = {
        "theme_id": c.get("theme_id", ""),
        "angle": c.get("angle", ""),
        "product_name": c.get("product_name", "作业辅导AI助手"),
        "one_liner": c.get("one_liner", ""),
        "introduce_excerpt": read_introduce_snippet(c)[:2000],
    }
    bundle = find_latest_video_bundle()
    if bundle:
        d, meta = bundle
        ctx["latest_video_dir"] = str(d)
        ctx["latest_video_meta"] = meta
        params = meta.get("params") if isinstance(meta.get("params"), dict) else {}
        if params:
            ctx["sample_interest"] = params.get("child_profile", {}).get("interests") or params.get("theme", "")
            ctx["sample_subject"] = params.get("subject", "")
    return ctx
