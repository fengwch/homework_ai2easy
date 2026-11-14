"""把原文切成可核对的片段，并判定哪些整段都是套话。

与溯源判定分开成两个文件：poc 里两者同居一室，改切分就会碰坏判定，
反之亦然；这两件事的变化方向本来就不一样。
"""

from __future__ import annotations

import re

from homework_compass.parsing.provenance import norm
from homework_compass.parsing.screening import is_junk_fragment
from homework_compass.parsing.vocabulary import BOILERPLATE, CONNECTORS

SENT_SPLIT = re.compile(r"[；;。\n\r！？!?]+")
_CHUNK_SPLIT = re.compile(r"[，,、\s/／|｜：:]+")
_PIECE_SPLIT = re.compile(r"[，,、\s！!。~～：:]+")
_ENUM_LEAD = re.compile(r"^\s*[（(\[]?\d{1,2}[)）\].、,，]|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]+")
_LEAD_DECOR = re.compile(r"^[^0-9a-zA-Z一-鿿]+")
_HEADER = re.compile(r"(作业|任务|内容|安排|清单|事项)(如下|如下所示|以下)")
# 日期脚手架只在标题句残余判定里用，绝不能全局当套话：「明天交」是真截止时间。
_DATE_SCAFFOLD = re.compile(r"[（(][^）)]*[）)]|\d{1,4}[月日号]|今[天日]|明[天日]|昨[天日]|的")
_DATE_ONLY = re.compile(r"[（(]?(?:\d{1,4}月\d{1,2}[日号]|\d{1,4}[日号]|[0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,2}|今[天日]|明[天日]|昨[天日])[）)]?")

_BOILER_NORM = {norm(x) for x in BOILERPLATE}
_BOILER_BY_LEN = sorted(_BOILER_NORM, key=len, reverse=True)
_CONN_NORM = {norm(x) for x in CONNECTORS}
_CONN_BY_LEN = sorted((x for x in CONNECTORS if x), key=len, reverse=True)
# 套话后面只允许跟极短的语气尾巴，才算同一句客套。「收到」是套话，
# 「收到书本后签字」是真作业——放开的长度就是吞掉作业的面积。
_MODAL = "好啦呀哦呢嘛啊哈"


def _is_boilerplate_piece(pn: str) -> bool:
    if not pn:
        return True
    if pn in _BOILER_NORM or pn in _CONN_NORM:
        return True
    # 「各位家长好」这类带语气后缀的变体，不能因为多一个字就被当成作业内容
    for p in _BOILER_BY_LEN:
        if pn.startswith(p) and pn != p:
            tail = pn[len(p):]
            if tail and len(tail) <= 2 and all(ch in _MODAL for ch in tail):
                return True
    return False


def strip_lead(text: str) -> str:
    """反复剥行首装饰、序号与话语连接词，直到稳定。

    连「另外」这类虚词也要剥：否则原文「另外明天记得穿校服」成了新片段，
    而抽取结果里的「明天记得穿校服」明明已覆盖它，却会因多两个字误报遗漏。
    """
    s = text or ""
    prev = None
    while prev != s:
        prev = s
        s = _LEAD_DECOR.sub("", s).strip()
        s = _ENUM_LEAD.sub("", s).strip()
        for c in _CONN_BY_LEN:
            if s.startswith(c):
                s = s[len(c):].strip("，,、：: \t")
                break
    return s


def is_noise(text: str) -> bool:
    """整段都是客套/标题/连接词则 True。含一个实义片段就不算噪声——宁可多问不可漏报。"""
    s = strip_lead(text)
    pieces = [p for p in _PIECE_SPLIT.split(s) if norm(p)]
    if not pieces:
        return True
    if all(_is_boilerplate_piece(norm(p)) for p in pieces):
        return True
    joined = "".join(pieces)
    # 纯日期/纯日期+标点：老师通知里的「（11月6日）」这类抬头，不含任何任务。
    # 只认「整段就是一个日期」，一旦后面跟了实词就放过——「明天交」是真截止时间。
    if _DATE_ONLY.fullmatch(joined):
        return True
    if _HEADER.search(joined):
        residual = _DATE_SCAFFOLD.sub("", _HEADER.sub("", joined))
        residual = "".join(p for p in _PIECE_SPLIT.split(residual)
                           if not _is_boilerplate_piece(norm(p)))
        if not norm(residual):
            return True
    return False


def split_fragments(raw: str) -> list[str]:
    """句子粒度：用于给家长展示上下文。"""
    out = []
    for piece in SENT_SPLIT.split(raw or ""):
        p = strip_lead(piece).strip("　 ").lstrip("：:")
        if p and norm(p) and not is_noise(p):
            out.append(p)
    return out


def split_chunks_with_context(text: str) -> list[tuple[str, str]]:
    """词块粒度用于检测，句子粒度用于展示。

    只用粗粒度，一个已认领的词就能掩盖整句遗漏；只用细粒度，
    家长看到「今晚十点前完成」这种孤零片段会不知道该归给哪一项。
    """
    out = []
    for frag in split_fragments(text):
        for c in _CHUNK_SPLIT.split(frag):
            c = strip_lead(c).strip("　 ：:")
            if not norm(c) or is_noise(c):
                continue
            # 单字块默认丢弃（「的」「了」到处都是）；但单个动作词（「背」「写」）
            # 是极简作业通知的真实条目，丢了就是静默吞掉一项作业。
            if len(norm(c)) < 2 and not is_junk_fragment(c):
                out.append((c, frag))
                continue
            if len(norm(c)) >= 2:
                out.append((c, frag))
    return out


def split_chunks(text: str) -> list[str]:
    return [c for c, _ in split_chunks_with_context(text)]
