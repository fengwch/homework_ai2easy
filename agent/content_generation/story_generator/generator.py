"""
故事生成：根据儿童档案与题目列表生成个性化故事、插图提示、解题引导。
使用 ChatTongyi/Qwen，模型与 API Key 从 .env 读取。
"""
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

from content_generation.story_generator.templates import TEMPLATES, DEFAULT_THEME
from utils.logging import get_logger

logger = get_logger(__name__)


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "content_generation.yaml"
    if not config_path.exists():
        return {"story": {"min_chars": 300, "max_chars": 500, "default_theme": DEFAULT_THEME}}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _select_theme(interests: List[str]) -> str:
    if not interests:
        return DEFAULT_THEME
    for tag in interests:
        if tag in TEMPLATES:
            return tag
    return interests[0] if interests else DEFAULT_THEME


def _questions_for_prompt(questions: List[Dict[str, Any]]) -> str:
    parts = []
    for i, q in enumerate(questions[:10], 1):
        stem = (q.get("structuredData") or {}).get("stem") or q.get("originalText", "")
        parts.append(f"{i}. {stem[:200]}")
    return "\n".join(parts)


def _questions_for_frontend(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转为前端 contents/{story_id}.questions 格式：content, options, answer, analysis。"""
    out = []
    for q in questions:
        sd = q.get("structuredData") or {}
        opts = sd.get("options") or []
        options_str = [f"{o.get('option', '')}. {o.get('text', '')}" for o in opts]
        out.append({
            "id": q.get("id", ""),
            "questionNumber": q.get("questionNumber", 0),
            "content": sd.get("stem") or q.get("originalText", "")[:500],
            "options": options_str if options_str else [],
            "answer": sd.get("answer", ""),
            "analysis": sd.get("analysis", ""),
        })
    return out


def _estimate_reading_time(story: str) -> int:
    """粗略按字数估算阅读分钟数。"""
    n = len(re.sub(r"\s", "", story))
    return max(1, (n + 199) // 200)


def generate_story(
    child_profile: Dict[str, Any],
    questions: List[Dict[str, Any]],
    subject: str = "数学",
    assignment_id: Optional[str] = None,
    story_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成个性化故事、插图提示、解题引导。
    返回与 Agent API POST /content/generate 响应一致的结构。
    """
    config = _load_config()
    story_cfg = config.get("story") or {}
    illu_cfg = config.get("illustration") or {}
    min_chars = story_cfg.get("min_chars", 300)
    max_chars = story_cfg.get("max_chars", 500)
    default_theme = story_cfg.get("default_theme", DEFAULT_THEME)
    panels_per_prompt = illu_cfg.get("panels_per_prompt", 3)
    panels_in_image = illu_cfg.get("panels_in_image", 6)
    panels_layout = illu_cfg.get("panels_layout", "2x3")
    include_dialogue = illu_cfg.get("include_dialogue", True)

    interests = child_profile.get("interests") or []
    theme = _select_theme(interests)
    character_name = child_profile.get("name") or "小明"
    age = child_profile.get("age") or 8
    grade = child_profile.get("grade") or "三年级"
    logger.info("开始故事生成", extra={"theme": theme, "character_name": character_name, "questions_count": len(questions)})

    template = TEMPLATES.get(theme, TEMPLATES[DEFAULT_THEME])
    questions_text = _questions_for_prompt(questions)

    # 插图配置说明：用于让故事结构与后续配图（分镜数、是否含对话框）对齐
    illustration_note = (
        f"本故事将配图：共约 {panels_per_prompt} 组插图，每组插图为多格连环画（{panels_in_image} 格，布局 {panels_layout}，如两行三列）。"
        if panels_in_image and panels_layout else f"本故事将配图：共约 {panels_per_prompt} 组插图。"
    )
    if include_dialogue:
        illustration_note += "插图中可包含人物对话或旁白（对话框/文字）。"
    else:
        illustration_note += "插图中不绘制对话框或旁白文字，画面以动作与场景为主，便于后续在留白处添加旁白。"

    prompt = f"""你是一位儿童故事创作助手。请根据以下信息生成一个适合{age}岁儿童（{grade}）的短故事，将作业题目自然地融入故事情节。

故事主题：{theme}
主角姓名：{character_name}
学科：{subject}
题目内容摘要：
{questions_text}

配图说明：{illustration_note}

要求：
1. 将题目转化为故事中的任务或问题，不改变数学本质和难度。
2. 语言生动有趣，用词简单，适合儿童阅读。
3. 内容健康正面，无暴力、恐怖等不适合儿童的内容。
4. 故事长度：{min_chars}-{max_chars}字。
5. 结构分为四段：开头（引入角色）→ 发展（遇到题目/挑战）→ 高潮（思考与解决）→ 结尾（总结或收获）；每段尽量有清晰可画的场景，便于对应上述 {panels_per_prompt} 组插图。
6. 在故事末尾可加一行【学习要点】列出本故事涉及的知识点（简短 bullet）。

请直接输出故事正文，不要输出“故事：”等前缀。"""

    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        api_key = os.getenv("DASHSCOPE_API_KEY")
        model_name = os.getenv("MODEL_NAME", "qwen-plus")
        if not api_key:
            story = f"（请配置 DASHSCOPE_API_KEY 以生成故事）\n\n{character_name}今天要做一道题：{questions_text[:200]}……\n\n【学习要点】\n• 请完成作业并思考解题方法。"
        else:
            model = ChatTongyi(model=model_name)
            chain = ChatPromptTemplate.from_messages([("human", "{prompt}")]) | model | StrOutputParser()
            story = chain.invoke({"prompt": prompt}).strip()
            logger.debug("故事正文生成完成", extra={"length": len(story)})
    except Exception as e:
        logger.warning("故事生成异常，使用占位文案", exc_info=e)
        story = f"（故事生成暂时不可用：{e}）\n\n{character_name}和朋友们一起学习：{questions_text[:150]}……\n\n【学习要点】\n• 认真读题，动脑思考。"

    # 插图提示：按段落或关键情节生成
    try:
        from content_generation.illustration_gen.prompts import generate_illustration_prompts
        illustration_prompts = generate_illustration_prompts(story, theme=theme, character_name=character_name)
    except Exception:
        illustration_prompts = [f"{theme}主题，{character_name}在学习", f"{character_name}思考问题"]

    # 解题引导：可为每道题生成，此处先返回空列表，由主后端或单独接口按题请求
    solution_guide = None  # 若需要可在此调用 solution_generator 汇总

    sid = story_id or f"story-{uuid.uuid4().hex[:8]}"
    title = f"{character_name}的{subject}奇遇记"
    summary = f"基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。"
    logger.info("故事生成完成", extra={"story_id": sid, "theme": theme})

    return {
        "storyId": sid,
        "title": title,
        "summary": summary,
        "story": story,
        "questions": _questions_for_frontend(questions),
        "illustration_prompts": illustration_prompts,
        "estimated_reading_time": _estimate_reading_time(story),
        "theme": theme,
        "solution_guide": solution_guide,
    }
