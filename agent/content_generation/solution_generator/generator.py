"""
解题引导生成：根据题目与儿童兴趣，用故事角色分步讲解，与故事主题一致。
使用 ChatTongyi/Qwen，模型与 API Key 从 .env 读取。
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

load_dotenv()

from utils.logging import get_logger

logger = get_logger(__name__)


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "content_generation.yaml"
    if not config_path.exists():
        return {"solution_guide": {"max_steps": 5}}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_solution_guide(
    question: Dict[str, Any],
    child_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    生成解题引导：基于兴趣角色、分步讲解。
    返回与 Agent API POST /content/solution-guide 一致的结构：theme, steps, full_text。
    """
    config = _load_config()
    sg_cfg = config.get("solution_guide") or {}
    max_steps = sg_cfg.get("max_steps", 5)

    interests = child_profile.get("interests") or ["小动物学习"]
    theme = interests[0] if interests else "小动物学习"
    character_name = child_profile.get("name") or "小明"
    logger.info("开始解题引导生成", extra={"theme": theme, "question_id": question.get("id")})
    sd = question.get("structuredData") or {}
    stem = sd.get("stem") or question.get("originalText", "")
    answer = sd.get("answer", "")
    analysis = sd.get("analysis", "")
    q_type = question.get("questionType", "fill_blank")

    prompt = f"""你是一位儿童解题引导助手。请用「{theme}」主题下的角色（主角名为 {character_name}）来分步讲解这道题，语言适合小学生理解。

题目：{stem[:400]}
正确答案：{answer}
解析参考：{analysis}

要求：
1. 用故事角色（如{character_name}）的口吻分步讲解，每步一句话或两句话。
2. 步骤数不超过 {max_steps} 步。
3. 不要直接说“答案是X”，而是引导孩子理解过程。
4. 输出格式：每行一步，行首为“步骤N：”或“第N步：”，然后跟讲解内容。不要输出其他说明。"""

    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        api_key = os.getenv("DASHSCOPE_API_KEY")
        model_name = os.getenv("MODEL_NAME", "qwen-plus")
        if not api_key:
            steps = [
                {"order": 1, "text": f"{character_name}说：我们先读懂题目。"},
                {"order": 2, "text": f"题目是：{stem[:80]}…"},
                {"order": 3, "text": f"正确答案是：{answer}。{analysis[:50] if analysis else ''}"},
            ]
            full_text = " ".join(s["text"] for s in steps)
            return {"theme": theme, "steps": steps, "full_text": full_text}

        model = ChatTongyi(model=model_name)
        chain = ChatPromptTemplate.from_messages([("human", "{prompt}")]) | model | StrOutputParser()
        out = chain.invoke({"prompt": prompt}).strip()
        steps = []
        for m in re.finditer(r"(?:步骤|第)\s*(\d+)\s*[：:]\s*([^\n]+)", out):
            steps.append({"order": int(m.group(1)), "text": m.group(2).strip()})
        if not steps:
            lines = [ln.strip() for ln in out.split("\n") if ln.strip()][:max_steps]
            steps = [{"order": i + 1, "text": re.sub(r"^\d+[\.．、]\s*", "", ln)} for i, ln in enumerate(lines)]
        full_text = " ".join(s["text"] for s in steps) or out[:500]
        logger.debug("解题引导生成完成", extra={"steps_count": len(steps)})
        return {"theme": theme, "steps": steps[:max_steps], "full_text": full_text}
    except Exception as e:
        logger.warning("解题引导 LLM 调用异常，使用默认步骤", exc_info=e)
        steps = [
            {"order": 1, "text": f"{character_name}说：我们先读懂题目。"},
            {"order": 2, "text": f"正确答案是：{answer}。{analysis[:80] if analysis else ''}"},
        ]
        return {"theme": theme, "steps": steps, "full_text": " ".join(s["text"] for s in steps)}
