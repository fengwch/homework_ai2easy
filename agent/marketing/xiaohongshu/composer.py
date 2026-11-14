"""软文正文组装与合规自检。"""
from __future__ import annotations

import glob
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from marketing.xiaohongshu.theme import load_campaign, project_root, resolve_theme_context


def _pick_title(campaign: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    templates = campaign.get("title_templates") or ["辅导作业太累？试试把题目变成故事"]
    name = campaign.get("product_name", "作业辅导AI助手")
    t = random.choice(templates)
    return t.replace("{product_name}", name)


def _build_body(campaign: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    name = campaign.get("product_name", "作业辅导AI助手")
    bt = campaign.get("body_template") or {}
    parts = [
        bt.get("hook", "").strip(),
        bt.get("turn", "").format(product_name=name).strip(),
        bt.get("steps", "").strip(),
        bt.get("feeling", "").strip(),
        bt.get("closing", "").strip(),
    ]
    extra = ""
    if ctx.get("sample_interest"):
        extra = f"\n\n（本期素材灵感：孩子喜欢的主题「{ctx['sample_interest']}」+ 学科「{ctx.get('sample_subject', '数学')}」，具体以你娃情况为准。）"
    text = "\n\n".join(p for p in parts if p) + extra
    text += "\n\n—— 工具为辅助，效果因家庭而异；AI 内容请家长适当核对。#广告 若为合作推广请按平台要求标注。"
    return text.strip()


def _normalize_hashtags(tags: List[str]) -> str:
    out = []
    for t in tags:
        t = t.strip()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        out.append(t)
    return " ".join(out)


def compliance_check(text: str, forbidden: List[str]) -> Tuple[bool, List[str]]:
    hits = []
    lower = text
    for w in forbidden:
        if w and w in lower:
            hits.append(w)
    return len(hits) == 0, hits


def collect_assets(campaign: Dict[str, Any]) -> Dict[str, List[str]]:
    root = project_root()
    assets = campaign.get("assets") or {}
    cover_dir = root / (assets.get("cover_dir") or "imgs/intruduce")
    covers: List[str] = []
    if cover_dir.is_dir():
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            covers.extend(sorted(glob.glob(str(cover_dir / ext))))
    story_glob = assets.get("story_glob") or "imgs/story/**/*.png"
    stories = sorted(glob.glob(str(root / story_glob), recursive=True))
    if not stories:
        alt = assets.get("story_glob_alt")
        if alt:
            stories = sorted(glob.glob(str(root / alt), recursive=True))
    max_n = int(assets.get("max_story_images") or 4)
    return {
        "cover_candidates": covers[:3],
        "story_images": stories[:max_n],
    }


def compose_note(
    campaign_path: Optional[Path] = None,
    *,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """
    生成标题、正文、标签、素材清单。
    use_llm=True 时尝试用 ChatTongyi 润色（需已安装 langchain-community 与 DASHSCOPE_API_KEY）。
    """
    campaign = load_campaign(campaign_path)
    ctx = resolve_theme_context(campaign)
    title = _pick_title(campaign, ctx)
    body = _build_body(campaign, ctx)
    tags = campaign.get("hashtags") or []
    hashtag_line = _normalize_hashtags(tags)

    ok, hits = compliance_check(title + "\n" + body, campaign.get("forbidden_phrases") or [])
    assets = collect_assets(campaign)

    if use_llm:
        body = _maybe_llm_polish(title, body, campaign)
        ok, hits = compliance_check(title + "\n" + body, campaign.get("forbidden_phrases") or [])

    return {
        "title": title,
        "body": body,
        "hashtags": hashtag_line,
        "compliance_ok": ok,
        "compliance_hits": hits,
        "assets": assets,
        "theme_context": ctx,
    }


def _maybe_llm_polish(title: str, body: str, campaign: Dict[str, Any]) -> str:
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage
    except ImportError:
        return body
    import os

    if not os.environ.get("DASHSCOPE_API_KEY"):
        return body
    model_name = os.environ.get("MODEL_NAME", "qwen-turbo")
    model = ChatTongyi(model=model_name)
    system = (
        "你是家长向的小红书软文编辑。保持事实不夸大、不用禁用词、不提绝对化提分承诺。"
        f"产品名：{campaign.get('product_name', '')}。"
    )
    msg = HumanMessage(
        content=f"{system}\n\n请略压缩润色以下正文，保留五段结构意图，800 字内：\n标题：{title}\n\n{body}"
    )
    try:
        out = model.invoke([msg])
        text = getattr(out, "content", None) or str(out)
        return text.strip() or body
    except Exception:
        return body
