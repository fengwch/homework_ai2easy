"""
题目解析：将 OCR 全文拆分为题目列表，并识别题型、知识点、难度。
可与 LLM 结合（use_llm 从 config 读取），输出与前端 questions 结构一致。
支持标记「如图」题并记录 figureRefLineIndex，供插图按题截取时对齐 OCR 行位置。
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# 题干中表示“有图”的关键词，用于标记需截插图的题目
FIGURE_REF_KEYWORDS = ("如图", "见图", "看图", "如下图", "如图所示", "见下图")


def _load_ocr_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "ocr_config.yaml"
    if not config_path.exists():
        return {"question_parsing": {"use_llm": False, "subject_hint": "数学"}}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _parse_questions_rule_based(text: str, subject: str) -> List[Dict[str, Any]]:
    """简单规则：按题号拆分，题型/知识点用默认值。"""
    questions = []
    # 按 1. 2. 3. 或 一、 二、 拆分
    blocks = re.split(r"\n\s*(\d+)[\.．、]\s*", "\n" + text.strip())
    if len(blocks) <= 1:
        blocks = re.split(r"\n\s*[一二三四五六七八九十]+[\.．、]\s*", "\n" + text.strip())
    i = 1
    for j in range(1, len(blocks), 2):
        num = blocks[j].strip() if blocks[j].strip().isdigit() else str(i)
        content = (blocks[j + 1] if j + 1 < len(blocks) else blocks[j]).strip()
        if not content:
            continue
        q_type = "multiple_choice" if re.search(r"[A-D][\.．、\s]", content) or "A." in content or "A．" in content else "fill_blank"
        structured = _structured_from_raw(content, q_type)
        # 展示/答题用文本不包含答案（答题时不显示答案）；标准答案保存在 structuredData.answer
        display_text = _content_without_answer(content)
        if not display_text and structured.get("stem"):
            display_text = structured["stem"]
        questions.append({
            "id": f"q{i}",
            "questionNumber": i,
            "questionType": q_type,
            "originalText": display_text or content,
            "structuredData": structured,
            "knowledgePoints": [{"subject": subject, "topic": "综合", "subtopic": "", "difficulty": "medium"}],
            "metadata": {"wordCount": len(display_text or content), "hasImage": False, "hasFormula": bool(re.search(r"[∑∫√≈≠≤≥]", content)), "confidence": 0.85},
        })
        i += 1
    if not questions and text.strip():
        content = text.strip()
        structured = _structured_from_raw(content, "fill_blank")
        display_text = _content_without_answer(content) or structured.get("stem") or content
        questions.append({
            "id": "q1",
            "questionNumber": 1,
            "questionType": "fill_blank",
            "originalText": display_text,
            "structuredData": structured,
            "knowledgePoints": [{"subject": subject, "topic": "综合", "subtopic": "", "difficulty": "medium"}],
            "metadata": {"wordCount": len(display_text), "hasImage": False, "hasFormula": False, "confidence": 0.8},
        })
    return questions


def _extract_answer(content: str) -> str:
    """从题目文本中提取答案（答案：、参考答案：、答： 等），供请求端保存为标准答案。"""
    if not content or not content.strip():
        return ""
    # 答案：B / 参考答案：2 / 答：A / 正确答案：C（整词匹配）
    patterns = [
        r"(?:答案|参考答案|正确答案)\s*[：:]\s*([A-Da-d])",
        r"(?:答案|参考答案|正确答案)\s*[：:]\s*(\d+)",
        r"答\s*[：:]\s*([A-Da-d\d]+)",
        r"答案\s*[：:]\s*([^\n，,。]+?)(?=[\n。]|$)",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            ans = m.group(1).strip()
            if len(ans) <= 20:  # 避免整段解析错误
                return ans
    return ""


def _content_without_answer(content: str) -> str:
    """
    从题目内容中删除答案部分，得到供展示/答题用的文本（不显示答案）。
    与 _extract_answer 使用的模式一致，删除整行或行末答案后缀。
    """
    if not content or not content.strip():
        return content
    # 删除整行：答案：xxx / 参考答案：xxx / 答：xxx / 正确答案：xxx
    text = re.sub(r"\n\s*(?:答案|参考答案|正确答案|答)\s*[：:]\s*[^\n]+\n?", "\n", content)
    text = re.sub(r"^\s*(?:答案|参考答案|正确答案|答)\s*[：:]\s*[^\n]+\n?", "", text)
    # 删除行末或句末的答案：xxx（无换行结尾）
    text = re.sub(r"\s*(?:答案|参考答案|正确答案)\s*[：:]\s*[A-Da-d0-9]+\.?\s*$", "", text)
    text = re.sub(r"\s*答\s*[：:]\s*[A-Da-d0-9]+\.?\s*$", "", text)
    return text.strip()


def _structured_from_raw(content: str, q_type: str) -> Dict[str, Any]:
    stem = content
    options = []
    answer = _extract_answer(content)
    analysis = ""
    # 从题干中去掉“答案：xxx”等行或句末答案，避免重复展示
    stem = re.sub(r"\n?\s*(?:答案|参考答案|正确答案|答)\s*[：:]\s*[^\n]+\n?", "\n", stem).strip()
    stem = re.sub(r"\s*(?:答案|参考答案|正确答案)\s*[：:]\s*[A-Da-d0-9]+\.?\s*$", "", stem)
    stem = re.sub(r"\s*答\s*[：:]\s*[A-Da-d0-9]+\.?\s*$", "", stem).strip()
    if q_type == "multiple_choice":
        opt_match = re.findall(r"([A-D])[\.．、\s]*([^\nA-D]+)", content)
        if opt_match:
            for opt, txt in opt_match:
                options.append({"option": opt, "text": txt.strip()})
            stem = re.sub(r"\s*[A-D][\.．、][^\n]+", "", stem).strip()
            stem = re.sub(r"^\d+[\.．、]\s*", "", stem).strip()
        if not answer and re.search(r"\b([A-D])\s*[。.]?\s*$", stem):
            m = re.search(r"\b([A-D])\s*[。.]?\s*$", stem)
            if m:
                answer = m.group(1).upper()
    return {"stem": stem[:500], "options": options, "answer": answer, "analysis": analysis}


def _parse_questions_llm(text: str, subject: str) -> List[Dict[str, Any]]:
    """使用 LLM 解析题型、知识点、难度及 structuredData。"""
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("DASHSCOPE_API_KEY")
        model_name = os.getenv("MODEL_NAME", "qwen-plus")
        if not api_key:
            return _parse_questions_rule_based(text, subject)
        model = ChatTongyi(model=model_name)
        prompt = ChatPromptTemplate.from_messages([
            ("human", """你是一个题目解析助手。根据下面 OCR 识别出的作业文本，按题号拆分为多道题目，并为每道题输出结构化信息。

要求：
1. 输出为合法 JSON 数组，且仅输出该数组，不要其他说明。
2. 每道题包含：id（如 q1,q2）、questionNumber、questionType（multiple_choice/fill_blank/calculation/application）、originalText、structuredData（stem、options（选择题为 [{option,text}]）、answer、analysis）、knowledgePoints（[{subject,topic,subtopic,difficulty: easy|medium|hard}]）、metadata（wordCount, hasImage: false, hasFormula, confidence: 0-1）。

OCR 文本（学科：{subject}）：
---
{text}
---
请直接输出 JSON 数组。"""),
        ])
        chain = prompt | model | StrOutputParser()
        out = chain.invoke({"text": text[:8000], "subject": subject})
        out = out.strip()
        if "```" in out:
            out = re.sub(r"^```(?:json)?\s*", "", out)
            out = re.sub(r"\s*```\s*$", "", out)
        arr = json.loads(out)
        if isinstance(arr, list) and len(arr) > 0:
            for i, q in enumerate(arr):
                q.setdefault("id", f"q{i+1}")
                q.setdefault("questionNumber", i + 1)
                q.setdefault("metadata", {}).setdefault("hasImage", False)
                q.setdefault("metadata", {}).setdefault("hasFormula", False)
                # 答题展示不显示答案：若题干含答案则从 originalText 中删除
                sd = q.get("structuredData") or {}
                if sd.get("answer") and q.get("originalText"):
                    q["originalText"] = _content_without_answer(q["originalText"]) or sd.get("stem") or q["originalText"]
            return arr
    except Exception:
        pass
    return _parse_questions_rule_based(text, subject)


def _has_figure_ref(content: str) -> bool:
    """题干是否包含「如图」「见图」等关键词。"""
    if not content:
        return False
    return any(kw in content for kw in FIGURE_REF_KEYWORDS)


def _figure_ref_line_index(question: Dict[str, Any], full_text: str) -> Optional[int]:
    """
    根据题目内容在全文中的起始位置，得到对应的 OCR 行索引（0-based）。
    用于插图截取时按垂直位置将图块分配给题目。
    """
    stem = (question.get("structuredData") or {}).get("stem") or ""
    original = question.get("originalText") or ""
    prefix = (original[:50] if len(original) >= 20 else original) or stem[:50] or stem
    prefix = prefix.strip()
    if not prefix:
        return None
    start = full_text.find(prefix)
    if start < 0 and stem:
        start = full_text.find(stem[:30].strip())
    if start < 0:
        return None
    return full_text[:start].count("\n")


def parse_questions_from_text(
    text: str,
    subject: Optional[str] = None,
    use_llm: Optional[bool] = None,
    ocr_line_texts: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    将 OCR 全文解析为与前端一致的 questions 列表。
    subject、use_llm 未传时从 configs/ocr_config.yaml 读取。
    ocr_line_texts: OCR 按行返回的文本列表，与 text 一致时用于计算 figureRefLineIndex。
    """
    config = _load_ocr_config()
    qp = config.get("question_parsing") or {}
    subj = subject or qp.get("subject_hint") or "数学"
    use = use_llm if use_llm is not None else qp.get("use_llm", False)
    if use:
        questions = _parse_questions_llm(text, subj)
    else:
        questions = _parse_questions_rule_based(text, subj)

    # 标记「如图」题并记录行索引，供插图按题截取
    full_text = "\n".join(ocr_line_texts) if ocr_line_texts else text
    for q in questions:
        meta = q.setdefault("metadata", {})
        meta["hasImageRef"] = _has_figure_ref(q.get("originalText") or "") or _has_figure_ref((q.get("structuredData") or {}).get("stem") or "")
        meta["figureRefLineIndex"] = _figure_ref_line_index(q, full_text) if ocr_line_texts else None
    return questions
