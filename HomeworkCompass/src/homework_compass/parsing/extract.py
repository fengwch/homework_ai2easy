"""抽取层：只负责给出候选，不负责给出真相。可信度由 validate 的机械校验决定。

三个实现走同一协议，校验层不知道上游是谁——poc 里的 `--no-llm` if 分支
到此变成正式设计：降级路径与主路径共用同一套校验。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Protocol

from homework_compass.errors import ExtractionError
from homework_compass.parsing.screening import is_junk_fragment
from homework_compass.parsing.segmentation import SENT_SPLIT, is_noise, strip_lead
from homework_compass.parsing.vocabulary import BOILERPLATE

SUBJECTS = ["语文", "数学", "英语", "科学", "美术", "音乐", "体育",
            "道德与法治", "道法", "劳动", "阅读", "写字"]
# 科目后面紧跟这些字时它是定语不是科目（「美术材料」≠ 美术课）。
_SUBJECT_BLOCK = ("材料", "用具", "工具", "课本", "书", "老师")
# 标签后面必须跟分隔符才算标签。「各位家长好」里的「各位家长」不是标签——
# 把它剥掉只剩「好」，套话判定就认不出来，客套句照样会印上纸。
_LABEL = re.compile("^(" + "|".join(re.escape(w)
                   for w in sorted(BOILERPLATE, key=len, reverse=True)) + r")[：:，,\s]+")


class Extractor(Protocol):
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict: ...


def clean_line(line: str) -> str:
    prev = None
    s = (line or "").strip()
    while prev != s:
        prev = s
        s = strip_lead(s)
        s = _LABEL.sub("", s).strip()
        s = s.lstrip("：:，,、 ")
    return s


def find_subject(line: str) -> tuple[int, str]:
    hits = []
    for s in SUBJECTS:
        start = line.find(s)
        while start != -1:
            if not line[start + len(s):].startswith(_SUBJECT_BLOCK):
                hits.append((start, s))
                break
            start = line.find(s, start + 1)
    return min(hits) if hits else (-1, "")


def naive_extract(raw: str) -> dict:
    """离线兜底：按句拆条、行内最早出现的科目词归为科目。刻意做笨。"""
    items = []
    for piece in SENT_SPLIT.split(raw or ""):
        line = clean_line(piece)
        if not line or is_noise(line):
            continue
        # 「像不像一条作业」的闸门：纯数字、纯符号、单字残片、纯页码
        # 都不该进清单。丢掉的片段不静默吞掉——交给覆盖率检查回问家长。
        if is_junk_fragment(line):
            continue
        pos, subject = find_subject(line)
        task = line if pos < 0 else (line[:pos] + line[pos + len(subject):]).strip("：:，,、 ")
        if not task:
            task, subject = line, ""
        items.append({"subject": subject, "task": task, "quantity": "", "requirements": []})
    return {"items": items, "extras": [], "unresolved": []}


class NaiveExtractor:
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        return naive_extract(raw_text)


class StubExtractor:
    """测试注入。给一个 dict 就一直返回它，给列表则依次返回、最后一个重复用。"""

    def __init__(self, payload: dict | list[dict]) -> None:
        self._queue = [payload] if isinstance(payload, dict) else list(payload)
        if not self._queue:
            raise ValueError("StubExtractor 至少需要一个 payload")

    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        return self._queue[0] if len(self._queue) == 1 else self._queue.pop(0)


DEFAULT_TEXT_MODEL = "qwen-plus"
DEFAULT_OCR_MODEL = "qwen-vl-ocr"

# 提示词把模型当成不可靠的抄写员：只许摘录，不许补全，不许判断优先级。
SYSTEM_PROMPT = """你是小学作业文本结构化解析器。你的输出会被程序逐字核对原文，因此：

1. 所有字段值（subject/task/quantity/requirements/extras）必须【逐字摘录】原文，
   不得改写、补全、解释、合并或翻译。原文没出现过的词，一个都不许写。
   注意：纯数字（如「23」）、纯符号、单个残字、孤立日期**不是作业条目**，
   直接放进 unresolved，不要作为 item 输出。
2. 原文含糊、被截断、看不懂归属的片段，原样放进 unresolved，不要猜。
3. 不要输出 priority，优先级由程序按关键词判定，你写了也会被覆盖。
   subject 同样受逐字核对：原文这一段**没有出现**任何科目名（语文/数学/英语…）时，
   subject 必须留空字符串，不要根据上下文（如「儿歌」「拼读」）推断成语文/英语——
   推断出来的科目会被程序当成杜撰并逐条退回给家长确认。
4. type 只能取 written/oral/reading/checkin/material 之一，判断不了就写 unknown。
5. estimated_minutes 是「建议值」，不确定就写 null，不要为了填满而编。
6. 只输出一个 JSON 对象，不要解释、不要代码块围栏。

输出 JSON 结构：
{"date": null, "items": [{"subject": "", "task": "", "quantity": "",
"requirements": [], "estimated_minutes": null, "type": "written"}],
"extras": [], "unresolved": []}"""

USER_TEMPLATE = """请把下面的老师作业原文解析成 JSON。日期为 {date}，学生姓名「{name}」。
再次强调：字段值必须是原文里能找到的字，找不到出处的内容请放进 unresolved。

原文：
\"\"\"{raw}\"\"\""""

OCR_SYSTEM_PROMPT = "你是 OCR 转写器，只输出图中文字原文。"
OCR_USER_TEXT = "按原样识别图片中的全部文字，保留原有编号、换行和符号，不要解释或补全。"


def _strip_fences(s: str) -> str:
    s = (s or "").strip()
    # 模型时而写 ```json 、时而写 ```JSON，大小写不定，一并剥。
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.S | re.I)
    return m.group(1) if m else s


class LlmExtractor:
    """原文 -> 候选结构（未经校验，不可直接上图）。

    transport 参数不是为了好看：它是让单元测试不打网络，
    而真正的调用质量留在 `-m network` 里由人工留证据。
    """

    def __init__(self, *, model: str = DEFAULT_TEXT_MODEL, transport=None) -> None:
        self.model = model
        self._transport = transport

    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        # 传输层放到函数里 import：离线路径（NaiveExtractor）根本不碰网络模块。
        from homework_compass import llm_client as lc
        if not raw_text or not raw_text.strip():
            raise ExtractionError("作业原文为空。")
        text = lc.chat(
            [{"type": "text", "text": USER_TEMPLATE.format(
                date=date or "今天", name=name or "（未填）", raw=raw_text)}],
            self.model, system=SYSTEM_PROMPT,
            response_format={"type": "json_object"},   # 提示词已含 JSON，否则接口报错
            transport=self._transport,
        )
        try:
            parsed = json.loads(_strip_fences(text))
        except json.JSONDecodeError as e:
            raise ExtractionError(f"模型没返回合法 JSON：{text[:400]}") from e
        if not isinstance(parsed, dict):
            raise ExtractionError(f"模型返回的不是对象：{text[:200]}")
        return parsed


def ocr_to_text(image_path: Path, *, model: str = DEFAULT_OCR_MODEL, timeout: int = 120,
                transport=None) -> str:
    """截图/照片 -> 文本，之后进入与纯文本完全相同的解析+校验管线。

    它只返回文本：强制 OCR_UNVERIFIED 的责任在 validate(source_kind=SourceKind.OCR)，
    上游谁都不许自己放行。
    """
    from homework_compass import llm_client as lc
    if not image_path.is_file():
        raise ExtractionError(f"图片不存在：{image_path}")
    mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    content = [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        {"type": "text", "text": OCR_USER_TEXT},
    ]
    return lc.chat(content, model, system=OCR_SYSTEM_PROMPT, timeout=timeout,
                   transport=transport).strip()
