"""
插图提示生成：根据故事内容与主题生成插图描述，供主后端或绘图 API 使用。
当前仅生成插图提示（prompts_only），不调用绘图 API。
"""
import os
import re
from typing import List

from dotenv import load_dotenv

load_dotenv()


def generate_illustration_prompts(
    story: str,
    theme: str = "小动物学习",
    character_name: str = "小明",
    max_prompts: int = 5,
) -> List[str]:
    """
    根据故事正文与主题生成若干条插图提示，风格统一为儿童漫画、色彩鲜艳。
    """
    # 按段落或句号拆分，取前几段作为插图场景
    segments = re.split(r"\n\n+|[。！？]\s*", story.strip())
    segments = [s.strip() for s in segments if len(s.strip()) > 10][:max_prompts]
    if not segments:
        return [f"{theme}主题，{character_name}在学习", f"{character_name}思考问题"]

    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        api_key = os.getenv("DASHSCOPE_API_KEY")
        model_name = os.getenv("MODEL_NAME", "qwen-plus")
        if not api_key:
            return _fallback_prompts(segments, theme, character_name)

        model = ChatTongyi(model=model_name)
        prompt_text = f"""你是一位儿童插画描述助手。根据以下故事片段，为每一段写一句插图描述（用于 AI 绘图或插画师参考）。

要求：
1. 风格：儿童漫画，色彩鲜艳，适合 3-12 岁。
2. 主题：{theme}，主角名为 {character_name}。
3. 每句描述 20-50 字，包含场景和角色动作。
4. 直接输出多行，每行一句描述，不要编号和多余说明。

故事片段：
{chr(10).join(segments)}"""
        chain = ChatPromptTemplate.from_messages([("human", "{prompt}")]) | model | StrOutputParser()
        out = chain.invoke({"prompt": prompt_text}).strip()
        lines = [ln.strip() for ln in out.split("\n") if ln.strip() and len(ln.strip()) > 5]
        # 去掉行首编号
        cleaned = []
        for ln in lines[:max_prompts]:
            ln = re.sub(r"^\d+[\.．、]\s*", "", ln)
            if ln:
                cleaned.append(ln)
        return cleaned if cleaned else _fallback_prompts(segments, theme, character_name)
    except Exception:
        return _fallback_prompts(segments, theme, character_name)


def _fallback_prompts(segments: List[str], theme: str, character_name: str) -> List[str]:
    prompts = [f"{theme}主题，{character_name}：{s[:30]}…" for s in segments[:3]]
    if not prompts:
        prompts = [f"{theme}主题，{character_name}在学习", f"{character_name}思考问题"]
    return prompts
