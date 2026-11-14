"""作业性判定：这一段文字「像不像一条作业」。

与 `segmentation.is_noise` 分工明确：

- `is_noise` 判「是不是套话/连接词」——「各位家长好」「收到请回复」。
- 本模块判「是不是一条能交给孩子做的任务」——纯数字「23」、纯符号「&」、
  单个残字「敬」、纯日期「11月6日」。

两者合起来才构成「这段该进清单吗」的完整判据。分开是因为它们回答的是
不同的问题，词表和规则各自演进的速度也不同。

判定只做减法：不确定的一律留下。宁可让家长多删一条，也不悄悄丢掉真作业。
"""

from __future__ import annotations

import re

from homework_compass.parsing.provenance import norm

# 去掉标点后只剩这些的东西，都是「没有内容」：
#   纯数字（页码残片、序号）  纯字母（拼音残片）
#   纯符号                   单个汉字（残字、OCR 误识别的碎片）
_EMPTYISH = re.compile(r"^[\dA-Za-z]*$")

# 单个汉字里，哪些本身就是一个完整动作。作业通知极简写法很常见：
# 「背」「写」「读」「算」。「敬」这种就不在其中——它是「敬请家长签字」的残片。
_ACTION_HANZI = frozenset({
    "背", "写", "读", "算", "听", "说", "看", "做", "画", "唱", "跳",
    "复习", "预习", "抄", "默", "练", "签", "交", "带", "订", "改",
})

# 动作词 + 后接内容（「背古诗」「读课文」）——短但明确是任务。
_ACTION_PREFIX = re.compile(
    r"^(背|写|读|算|听|说|看|做|画|唱|跳|抄|默|练|订|改|完成|复习|预习|朗读|拼读|抄写|默写|听读|完成练习册)")

# 纯页码/题号区间：「p51-52」「47-53」「第3题」——它们是某条作业的量，
# 单独出现说明原文被截断了，不能当成一条任务。
_BARE_NUMBERISH = re.compile(
    r"^(?:p|pg|第)?\d+(?:\s*[-~—－]\s*\d+)?(?:页|题|课|单元|单元)?$", re.I)

# 纯日期/时间：已在 segmentation 里判过一部分，这里兜住剩下的写法。
_DATE_LIKE = re.compile(
    r"^(?:\d{1,4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,4}[月]\d{1,2}[日号]?|\d{1,2}[:：]\d{2}"
    r"|周[一二三四五六日天]|星期[一二三四五六日天])$")


def is_junk_fragment(text: str) -> bool:
    """这段文字是不是「不成其为一条作业」的碎片。

    True 表示该丢（进 pending 回问家长，不静默吞掉）；
    False 表示保留——包括所有拿不准的情况。
    """
    s = (text or "").strip()
    if not s:
        return True

    # 去掉标点后为空：只有符号/空白
    n = norm(s)
    if not n:
        return True

    # 单个汉字：只有动作词才算完整任务（背、写、读…），其余是残片
    if len(n) == 1 and re.fullmatch(r"[一-鿿]", n):
        return n not in _ACTION_HANZI

    # 纯数字/纯字母（页码残片、拼音残片）：单独出现说明原文被截断
    if _EMPTYISH.fullmatch(n):
        return True

    # 纯日期时间
    if _DATE_LIKE.fullmatch(n):
        return True

    # 纯页码/题号区间：它是某条作业的「量」，不是一条作业
    if _BARE_NUMBERISH.fullmatch(n):
        return True

    # 短且不是动作词开头：两三个字的碎片（「敬」「的」「共」）
    if len(n) <= 3 and not _ACTION_PREFIX.match(s):
        return True

    return False
