"""
漫画/插图生成：使用 TTAPI Midjourney API 或 Gemini 模型生成动漫风格图像。
支持配置几格、风格、黑白线稿、参考图（上传或后台配置）+ LLM 再次生成/优化 Prompt。
TTAPI 提供异步实现，避免阻塞事件循环；超时由配置与 asyncio.wait_for 统一处理。
"""
import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

from utils.logging import get_logger

logger = get_logger(__name__)

# 支持的兴趣爱好：从中取一生成兴趣相关人物角色并写入图片生成提示词
SUPPORTED_INTERESTS = [
    "奥特曼", "海底小纵队", "小猪佩奇", "超级飞侠", "汪汪队",
    "机器人", "太空", "外星人", "未来世界",
    "恐龙", "动物世界", "植物", "海洋生物",
    "公主", "王子", "魔法", "城堡",
    "足球", "篮球", "游泳", "跑步",
    "医生", "警察", "消防员", "科学家",
    "美食", "汽车", "积木", "音乐",
]


def _pick_character_interest(interests: Optional[List[str]]) -> str:
    """从兴趣爱好列表中取一个用于指定连环画角色；优先取在 SUPPORTED_INTERESTS 中的第一项。"""
    if not interests:
        return ""
    for tag in interests:
        if tag and str(tag).strip() and str(tag).strip() in SUPPORTED_INTERESTS:
            return str(tag).strip()
    return str(interests[0]).strip() if interests else ""


def _load_illustration_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "content_generation.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("illustration") or {}


def _refine_prompt_with_llm(
    raw_prompt: str,
    style: str = "children",
    line_art: bool = False,
    panels_hint: str = "单幅",
    reference_hint: str = "",
    prompt_template: str = "",
    panels_in_image: int = 0,
    panels_layout: str = "",
    include_dialogue: bool = False,
    character_interest: str = "",
    provider: str = "ttapi_midjourney",
) -> str:
    """
    使用 LLM 根据图片生成需求配置，将传入的提示词再次生成为绘图 API 可用的英文 Prompt。
    若配置了 prompt_template（如连载漫画模板），则要求 LLM 按模板结构输出。
    """
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        api_key = os.getenv("DASHSCOPE_API_KEY")
        model_name = os.getenv("MODEL_NAME", "qwen-plus")
        if not api_key:
            return _fallback_prompt(raw_prompt, style, line_art)

        model = ChatTongyi(model=model_name)
        style_desc = "children's illustration, cute, colorful, suitable for 3-12 years old"
        if style == "anime":
            style_desc = "anime style, Japanese animation, clean lines, vibrant colors"
        elif style == "cartoon":
            style_desc = "cartoon style, Western cartoon, expressive characters"
        elif style == "line_art":
            style_desc = "black and white line art, clean line drawing, no color, manga style sketch"
            line_art = True
        if line_art:
            style_desc = "black and white line art only, no color, clean outline drawing"

        template_instruction = ""
        if prompt_template and prompt_template.strip():
            template_instruction = f"""
输出格式要求（必须遵守）：按以下模板结构填写内容，保留模板中的占位说明（如 --ar 16:9 --style raw --v 6.0）：
{prompt_template.strip()}
请将 [manga style]、[page layout]、[scene description]、[characters]、[emotion/action]、[detailed instructions] 等替换为与中文描述对应的英文内容，其他部分原样保留。只输出一行，不要解释。
"""

        panel_instruction = ""
        if panels_in_image:
            if include_dialogue:
                panel_instruction = (
                    "8. 若为多格连环画，请在英文提示中按 'Panel 1: ...; Panel 2: ...' 或 "
                    "'1) ... 2) ...' 的形式依次描述每一格的画面和其中的旁白/对话内容，但整体仍是一条提示词"
                    "（不要换行，不要额外解释）。"
                )
            else:
                panel_instruction = (
                    "8. 若为多格连环画，请强调：画面中**不要出现任何对话框、文字气泡或旁白文字**；"
                    "同时在每一格画面的下方预留一条较高的空白横条（留白区域），专门用于后续叠加中文旁白或文字说明，"
                    "请确保这一空白条内完全没有任何文字和图案，只需在提示中说明保留此空白区域即可。"
                )

        # 角色来源要求：从儿童兴趣爱好衍生的角色，需在英文提示中明确指定并保持一致
        interest_instruction = (
            "角色要求：连环画中的主角和重要角色，需要来自儿童的兴趣爱好设定；"
            "请从中文描述中识别这些兴趣角色，在英文提示中用清晰的英文名称和简短外观特征描述，并在所有分格中保持角色形象前后一致。"
        )
        if character_interest and character_interest.strip():
            interest_instruction = (
                f"主角/角色设定（必须遵守）：本次指定兴趣爱好为「{character_interest.strip()}」。"
                "请根据该兴趣生成一个与之相关的人物角色（如该主题下的英雄、伙伴或典型形象），"
                "在英文提示中明确写出该角色的英文名称与外观特征，并在所有分格中保持该角色一致。"
            )
        # 根据绘图 provider 选择不同的英文说明，避免无关的引擎名称
        engine_label = "image generation model"
        p = (provider or "").strip().lower()
        if p == "ttapi_midjourney":
            engine_label = "Midjourney image generation"
        elif p == "gemini":
            engine_label = "Gemini image model"

        prompt_text = f"""你是一位 AI 绘图提示词助手。根据「图片生成需求配置」将下面的中文插图描述改写成一句英文 {engine_label} 可用的提示词。

要求：
1. 输出仅一句英文，不要编号、不要解释。
2. 风格要求：{style_desc}
3. 画面：{panels_hint}，适合儿童观看，无暴力恐怖。
4. 保留场景与角色动作的核心含义，保证角色一致性与场景连贯性。
{f'5. 参考说明：{reference_hint}' if reference_hint else ''}
{f'6. 多格分镜：单张图内包含 {panels_in_image} 格连环画，布局 {panels_layout}（如 2x3 即两行三列），参考中国传统寓言连环画（如郑人买履）的构图与分镜方式。' if panels_in_image and panels_layout else ''}
{f'7. 每格内需有个性化人物对话或场景对话，使画面有故事感：使用中文描述话框、旁白或角色说的话（必须遵守）。' if include_dialogue else ''}
{f'8. （必须严格遵守）若存在对话框或人物对白，请先将对白内容用简体中文准确表述，再据此生成英文提示词中的对话与表情描述，不要英文对话框或人物对白台词。' if include_dialogue else ''}
{interest_instruction}
{panel_instruction}
{template_instruction}

中文描述：
{raw_prompt}

直接输出一句英文提示词："""

        chain = ChatPromptTemplate.from_messages([("human", "{prompt}")]) | model | StrOutputParser()
        out = chain.invoke({"prompt": prompt_text}).strip()
        if out and len(out) > 10:
            # 不再截断，保留完整英文提示词，便于分格校验与日志查看
            return out
    except Exception as e:
        logger.warning("LLM 优化插图 Prompt 失败，使用回退", exc_info=e)
    return _fallback_prompt(raw_prompt, style, line_art)


def _fallback_prompt(raw_prompt: str, style: str, line_art: bool) -> str:
    """回退：简单拼接风格关键词。"""
    parts = [raw_prompt[:200]]
    if style == "anime":
        parts.append("anime style, cute, colorful")
    elif style == "line_art" or line_art:
        parts.append("black and white line art, clean outline")
    else:
        parts.append("children illustration, cartoon, colorful")
    return ", ".join(parts)


def _append_cref_and_version(prompt: str, reference_image_url: str) -> str:
    """当配置了参考图时，为 TTAPI Midjourney 追加 --cref 与 --v 6.0（--cref 需与 --v 6.0 同用）。"""
    if not reference_image_url or not reference_image_url.strip():
        return prompt
    out = prompt.strip()
    if reference_image_url.strip() not in out:
        out = f"{out} --cref {reference_image_url.strip()} --cw 100"
    if "--v 6" not in out and "--v 5" not in out:
        out = f"{out} --v 6.0"
    return out


def _ensure_panels_in_prompt(prompt: str, panels_in_image: int) -> str:
    """
    根据配置的 panels_in_image 对 LLM 生成的英文提示词做一次简单校验/强化：
    - 若已经包含 Panel 1..N，则直接返回；
    - 否则在末尾追加一句“with exactly N panels in the comic strip layout”来强调分格数量。
    """
    if not panels_in_image or panels_in_image <= 0:
        return prompt
    text = prompt or ""
    try:
        has_all = all(f"Panel {i}" in text for i in range(1, panels_in_image + 1))
    except Exception:
        return text
    if has_all:
        return text
    suffix = f" with exactly {panels_in_image} panels in the comic strip layout"
    if suffix not in text:
        text = f"{text} {suffix}"
    return text


def _generate_ttapi(prompt: str, mode: str = "fast", timeout: int = 300) -> List[str]:
    """同步：调用 TTAPI Midjourney /imagine，轮询 /fetch。供非异步场景使用。"""
    import requests
    api_key = os.getenv("TTAPI_API_KEY") or os.getenv("MIDJOURNEY_API_KEY")
    if not api_key:
        logger.warning("未配置 TTAPI_API_KEY，跳过 Midjourney 生成")
        return []

    base = os.getenv("TTAPI_BASE_URL", "https://api.ttapi.io")
    imagine_url = f"{base}/midjourney/v1/imagine"
    fetch_url = f"{base}/midjourney/v1/fetch"
    headers = {"TT-API-KEY": api_key, "Content-Type": "application/json"}
    poll_deadline = min(timeout, 120)

    try:
        r = requests.post(
            imagine_url,
            headers=headers,
            json={"prompt": prompt, "mode": mode, "timeout": timeout},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "SUCCESS":
            logger.warning("TTAPI imagine 失败: %s", data.get("message"))
            return []
        job_id = (data.get("data") or {}).get("jobId")
        if not job_id:
            return []

        deadline = time.time() + poll_deadline
        while time.time() < deadline:
            time.sleep(5)
            fr = requests.post(fetch_url, headers=headers, json={"jobId": job_id}, timeout=15)
            fr.raise_for_status()
            fd = fr.json()
            if fd.get("status") != "SUCCESS":
                continue
            d = fd.get("data") or {}
            images = d.get("images")
            if images and isinstance(images, list):
                return [img for img in images if isinstance(img, str)][:4]
            progress = d.get("progress") or ""
            if "FAILED" in progress or "failed" in str(d).lower():
                break
        logger.warning("TTAPI fetch 超时或未返回图片 jobId=%s", job_id)
        return []
    except Exception as e:
        logger.exception("TTAPI Midjourney 调用异常: %s", e)
        return []


async def _generate_ttapi_async(
    prompt: str,
    mode: str = "fast",
    timeout: int = 300,
    *,
    imagine_timeout: float = 30.0,
    fetch_timeout: float = 15.0,
    poll_interval: float = 5.0,
) -> List[str]:
    """
    异步调用 TTAPI Midjourney：/imagine 提交任务，轮询 /fetch 直到完成或超时。
    超时后返回空列表并打日志，不抛异常。
    """
    import httpx
    api_key = os.getenv("TTAPI_API_KEY") or os.getenv("MIDJOURNEY_API_KEY")
    if not api_key:
        logger.warning("未配置 TTAPI_API_KEY，跳过 Midjourney 生成")
        return []

    base = os.getenv("TTAPI_BASE_URL", "https://api.ttapi.io").rstrip("/")
    imagine_url = f"{base}/midjourney/v1/imagine"
    fetch_url = f"{base}/midjourney/v1/fetch"
    headers = {"TT-API-KEY": api_key, "Content-Type": "application/json"}
    deadline = time.monotonic() + min(timeout, 300)

    try:
        async with httpx.AsyncClient(timeout=imagine_timeout) as client:
            r = await client.post(
                imagine_url,
                headers=headers,
                json={"prompt": prompt, "mode": mode, "timeout": timeout},
            )
            r.raise_for_status()
            data = r.json()
        if data.get("status") != "SUCCESS":
            logger.warning("TTAPI imagine 失败: %s", data.get("message"))
            return []
        job_id = (data.get("data") or {}).get("jobId")
        if not job_id:
            return []

        async with httpx.AsyncClient(timeout=fetch_timeout) as client:
            while time.monotonic() < deadline:
                await asyncio.sleep(poll_interval)
                fr = await client.post(fetch_url, headers=headers, json={"jobId": job_id})
                fr.raise_for_status()
                fd = fr.json()
                if fd.get("status") != "SUCCESS":
                    continue
                d = fd.get("data") or {}
                images = d.get("images")
                if images and isinstance(images, list):
                    return [img for img in images if isinstance(img, str)][:4]
                progress = d.get("progress") or ""
                if "FAILED" in progress or "failed" in str(d).lower():
                    break
        logger.warning("TTAPI fetch 超时或未返回图片 jobId=%s", job_id)
        return []
    except httpx.TimeoutException as e:
        logger.warning("TTAPI 请求超时: %s", e)
        return []
    except Exception as e:
        logger.exception("TTAPI Midjourney 异步调用异常: %s", e)
        return []


def _generate_gemini(
    prompt: str,
    num_images: int = 1,
    *,
    mode: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    google_search: Optional[bool] = None,
    thinking_level: Optional[str] = None,
    refer_images: Optional[List[str]] = None,
) -> List[str]:
    """
    使用 TTAPI 的 Gemini 图片模型生成图像。
    文档参考: https://docs-zh.mjapiapp.com/api/gemini-image-model
    """
    api_key = os.getenv("TTAPI_API_KEY") or os.getenv("MIDJOURNEY_API_KEY")
    if not api_key:
        logger.warning("未配置 TTAPI_API_KEY，跳过 Gemini 图像生成")
        return []

    base = os.getenv("TTAPI_BASE_URL", "https://api.ttapi.io").rstrip("/")
    endpoint = f"{base}/gemini/image/generate"
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    # 从参数或环境变量中确定模型版本
    mode = mode or os.getenv("TTAPI_GEMINI_MODE", "gemini-2.5-flash-image-preview")

    try:
        import requests

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "mode": mode,
        }
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if image_size:
            payload["image_size"] = image_size
        if google_search is not None:
            payload["google_search"] = bool(google_search)
        if thinking_level:
            payload["thinking_level"] = thinking_level
        if refer_images:
            # 过滤掉空字符串，确保是字符串列表
            payload["refer_images"] = [u for u in refer_images if isinstance(u, str) and u.strip()]

        resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "SUCCESS":
            logger.warning("TTAPI Gemini 生成失败: %s", data.get("message"))
            return []
        d = data.get("data") or {}
        image_url = d.get("image_url")
        if not image_url:
            logger.warning("TTAPI Gemini 未返回 image_url: %s", d)
            return []
        # 日志中输出完整 image_url，便于排查与人工校验
        logger.info("TTAPI Gemini 生成成功 | prompt=%s | image_url=%s", prompt, image_url)
        # 当前接口一次返回一张图；为兼容调用方签名，简单裁剪为所需数量
        return [image_url][: max(1, num_images)]
    except requests.Timeout as e:
        logger.warning("TTAPI Gemini 请求超时: %s", e)
        return []
    except Exception as e:
        logger.warning("TTAPI Gemini 图像生成异常: %s", e)
        return []


def _build_illustration_params(
    style: Optional[str],
    line_art: Optional[bool],
    panels_per_prompt: Optional[int],
    reference_image_url: Optional[str],
    provider: Optional[str],
    ttapi_mode: Optional[str],
    ttapi_timeout: Optional[int],
    interests: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """从配置与参数合并出插图生成所需参数字典（含 prompt_template、character_interest）。"""
    cfg = _load_illustration_config()
    prov = (provider or cfg.get("provider") or "ttapi_midjourney").strip().lower()
    prompt_template = cfg.get("prompt_template") or ""
    # Gemini/Imagen 不识别 Midjourney 参数，使用 gemini 时去掉 --ar / --style / --v 6.0 等后缀
    if prov == "gemini" and prompt_template:
        prompt_template = re.sub(r"\s*--(?:ar|style|v)\s+[\w./:]+\s*", " ", prompt_template).strip()
    return {
        "style": style or cfg.get("style", "children"),
        "line_art": line_art if line_art is not None else cfg.get("line_art", False),
        "panels": panels_per_prompt or cfg.get("panels_per_prompt", 1),
        "reference_image_url": reference_image_url or cfg.get("reference_image_url") or "",
        "provider": prov,
        "ttapi_mode": ttapi_mode or cfg.get("ttapi_mode", "fast"),
        "ttapi_timeout": ttapi_timeout or cfg.get("ttapi_timeout", 300),
        "prompt_template": prompt_template,
        "panels_in_image": cfg.get("panels_in_image") or 0,
        "panels_layout": (cfg.get("panels_layout") or "").strip(),
        "include_dialogue": cfg.get("include_dialogue", False),
        "character_interest": _pick_character_interest(interests or []),
        # Gemini 相关配置，仅在 provider 为 gemini 时使用
        "gemini_mode": cfg.get("gemini_mode"),
        "gemini_aspect_ratio": cfg.get("gemini_aspect_ratio"),
        "gemini_image_size": cfg.get("gemini_image_size"),
        "gemini_google_search": cfg.get("gemini_google_search"),
        "gemini_thinking_level": cfg.get("gemini_thinking_level"),
        "gemini_refer_images": cfg.get("gemini_refer_images") or [],
    }


def generate_illustration_images(
    prompts: List[str],
    style: Optional[str] = None,
    line_art: Optional[bool] = None,
    panels_per_prompt: Optional[int] = None,
    reference_image_url: Optional[str] = None,
    provider: Optional[str] = None,
    ttapi_mode: Optional[str] = None,
    ttapi_timeout: Optional[int] = None,
    interests: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    同步：根据插图提示列表生成图片。返回 [{"prompt": str, "images": [...]}, ...]
    """
    cfg = _load_illustration_config()
    if cfg.get("prompts_only", True):
        return [{"prompt": p, "images": []} for p in prompts]

    params = _build_illustration_params(
        style, line_art, panels_per_prompt, reference_image_url,
        provider, ttapi_mode, ttapi_timeout, interests,
    )
    # 参考图说明仅在 Midjourney 模式下使用（reference_image_url 通过 --cref 传入）
    reference_hint = ""
    if params["provider"] == "ttapi_midjourney" and params["reference_image_url"]:
        reference_hint = f"reference image style: {params['reference_image_url']}"
    panels_hint = "单幅" if params["panels"] <= 1 else f"{params['panels']} 格漫画"
    if params.get("panels_in_image") and params.get("panels_layout"):
        panels_hint = f"{params['panels_in_image']} 格连环画，布局 {params['panels_layout']}（如 2x3 即两行三列）"

    result = []
    for raw in prompts:
        refined = _refine_prompt_with_llm(
            raw,
            style=params["style"],
            line_art=params["line_art"],
            panels_hint=panels_hint,
            reference_hint=reference_hint,
            prompt_template=params.get("prompt_template", ""),
            panels_in_image=params.get("panels_in_image") or 0,
            panels_layout=params.get("panels_layout") or "",
            include_dialogue=params.get("include_dialogue", False),
            character_interest=params.get("character_interest", ""),
            provider=params.get("provider", "ttapi_midjourney"),
        )
        refined_final = _ensure_panels_in_prompt(refined, params.get("panels_in_image") or 0)
        logger.info("插图生成提示词 | raw=%s | refined=%s", raw, refined_final)
        images = []
        if params["provider"] == "gemini":
            images = _generate_gemini(
                refined_final,
                num_images=min(params["panels"], 4),
                mode=params.get("gemini_mode"),
                aspect_ratio=params.get("gemini_aspect_ratio"),
                image_size=params.get("gemini_image_size"),
                google_search=params.get("gemini_google_search"),
                thinking_level=params.get("gemini_thinking_level"),
                refer_images=params.get("gemini_refer_images"),
            )
        else:
            final_prompt = _append_cref_and_version(refined_final, params["reference_image_url"])
            images = _generate_ttapi(final_prompt, mode=params["ttapi_mode"], timeout=params["ttapi_timeout"])[: params["panels"]]
        result.append({"prompt": refined_final, "raw_prompt": raw, "images": images})
    return result


async def generate_illustration_images_async(
    prompts: List[str],
    style: Optional[str] = None,
    line_art: Optional[bool] = None,
    panels_per_prompt: Optional[int] = None,
    reference_image_url: Optional[str] = None,
    provider: Optional[str] = None,
    ttapi_mode: Optional[str] = None,
    ttapi_timeout: Optional[int] = None,
    interests: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    异步：根据插图提示列表生成图片。TTAPI 使用异步 HTTP，LLM/Gemini 在线程池中执行，避免阻塞事件循环。
    返回 [{"prompt": str, "raw_prompt": str, "images": [url_or_base64, ...]}, ...]
    """
    cfg = _load_illustration_config()
    if cfg.get("prompts_only", True):
        return [{"prompt": p, "raw_prompt": p, "images": []} for p in prompts]

    params = _build_illustration_params(
        style, line_art, panels_per_prompt, reference_image_url,
        provider, ttapi_mode, ttapi_timeout, interests,
    )
    # 参考图说明仅在 Midjourney 模式下使用（reference_image_url 通过 --cref 传入）
    reference_hint = ""
    if params["provider"] == "ttapi_midjourney" and params["reference_image_url"]:
        reference_hint = f"reference image style: {params['reference_image_url']}"
    panels_hint = "单幅" if params["panels"] <= 1 else f"{params['panels']} 格漫画"
    if params.get("panels_in_image") and params.get("panels_layout"):
        panels_hint = f"{params['panels_in_image']} 格连环画，布局 {params['panels_layout']}（如 2x3 即两行三列）"

    result = []
    loop = asyncio.get_running_loop()
    prompt_template = params.get("prompt_template", "")
    character_interest = params.get("character_interest", "")
    provider_name = params.get("provider", "ttapi_midjourney")
    for raw in prompts:
        refined = await loop.run_in_executor(
            None,
            lambda r=raw: _refine_prompt_with_llm(
                r,
                style=params["style"],
                line_art=params["line_art"],
                panels_hint=panels_hint,
                reference_hint=reference_hint,
                prompt_template=prompt_template,
                panels_in_image=params.get("panels_in_image") or 0,
                panels_layout=params.get("panels_layout") or "",
                include_dialogue=params.get("include_dialogue", False),
                character_interest=character_interest,
                provider=provider_name,
            ),
        )
        refined_final = _ensure_panels_in_prompt(refined, params.get("panels_in_image") or 0)
        logger.info("插图生成提示词 | raw=%s | refined=%s", raw, refined_final)
        images = []
        if params["provider"] == "gemini":
            images = await loop.run_in_executor(
                None,
                lambda r=refined_final, n=min(params["panels"], 4): _generate_gemini(
                    r,
                    num_images=n,
                    mode=params.get("gemini_mode"),
                    aspect_ratio=params.get("gemini_aspect_ratio"),
                    image_size=params.get("gemini_image_size"),
                    google_search=params.get("gemini_google_search"),
                    thinking_level=params.get("gemini_thinking_level"),
                    refer_images=params.get("gemini_refer_images"),
                ),
            )
        else:
            final_prompt = _append_cref_and_version(refined_final, params["reference_image_url"])
            images = await _generate_ttapi_async(
                final_prompt,
                mode=params["ttapi_mode"],
                timeout=params["ttapi_timeout"],
            )
        result.append({"prompt": refined_final, "raw_prompt": raw, "images": images[: params["panels"]]})
    return result