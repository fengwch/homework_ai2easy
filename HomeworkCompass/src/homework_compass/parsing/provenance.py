"""溯源引擎：判断「这个字段值在原文里到底有没有出处」。

分级从代价最低到最高短路判定。TOKENS_MATCH 与 PARTIAL 存在的理由都是真实误判：
生图模型和文本模型都会顺手把 P12-13 规范成 P12–P13、把「练习册」说成「完成练习册」，
一刀切的子串判定会把正确数据扔进待确认，比漏判更烦人。
放宽的边界是数字与字母词元——页码和数量永远零容错。

三条必须知道的实现约束：

1. **词元必须全部命中原文**（spec §5.2）。norm 把 "P12-13" 压成 "p1213"，
   于是 "p12"、"p1" 这类前缀也都是原文的子串；不先卡词元，截断的页码会被
   判成逐字命中。子串/子序列判定只在词元过关之后才允许生效。
2. **词元允许是原文相邻词元的拼接**。模型把 "P12-13" 写成 "P1213" 时，
   词元是 "1213" 而原文是 "12"+"13"；按「必须原样出现」判，会把正确数据
   扔进 pending——那比漏判更烦人（spec §5.3）。
3. **纯汉字值会退化**：词元集对纯汉字是空的，TOKENS_MATCH 于是退化成
   「每个字都在原文出现过」，NORMALIZED 则是「整串是原文的子序列」。
   这是词元级判定的固有代价——中文没有空格可切，只能靠字集合。
   这两级都会进 report.advisories（标黄、不阻断），家长扫一眼即可。

列表序号（"1." "2、"）不算内容：序号里的数字进了词元集，截断的页码就会
因为命中序号数字而蒙混过关，所以比对前先把序号去掉（见 strip_markers）。

已知边界（都是宁可放过、不可误剥那一侧）：

- 「抄写生字，（2）遍」这种「标点 + 括号数量」仍会被剥掉（括号前不是汉字）。
  改窄到「标点前不剥」，序号就会重新 legitimize 截断页码；两头不能两全，
  按 spec 的排序保留当前行为。代价是这种原文里的数量会被删出词元集，
  真作业可能被判成无出处。
- 「生字2)遍」这种紧跟汉字的右括号形不会被剥（它与「今天作业1)数学」的序号
  形状无法区分）。代价：这种写法的序号里的数字会留在词元集里。
"""

from __future__ import annotations

import re
from enum import Enum

from homework_compass.models import TraceLevel

# 只保留汉字、字母、数字；标点、emoji、空白、装饰符一律剥离
_KEEP = re.compile(r"[^一-鿿0-9a-zA-Z]+")
_TOK = re.compile(r"[a-z]+|\d+")
_CJK = re.compile(r"[一-鿿]")

# 列表序号：数字 + 序号分隔符 + 紧跟汉字。三种形状分开写：
# 括号形「（1）数学」的前括号必须站在非汉字边界上，否则「抄写生字（2）遍」
# 里的数量会被当成序号剥掉（剥掉就等于删掉一个真实数字，真作业反被判成杜撰）；
# 裸数字形「1.数学」允许紧跟汉字（「今天作业1.数学」也得剥，否则序号里的
# 「1」会让截断的页码「P1」蒙混过关）；
# 半角/全角右括号形「1)数学」「1）数学」没有前括号，得单开一支——但它不能吃掉
# 「(2)」这类真实数量，所以额外把前括号列进否定边界（跟在括号后的数字一律不剥）。
_ENUM_MARK = re.compile(
    r"(?<![A-Za-z0-9一-鿿-])[（(]\d{1,2}[)）]\s*(?=[\u4e00-\u9fff])"
    r"|(?<![A-Za-z0-9一-鿿\-(（(])\d{1,2}[)）]\s*(?=[\u4e00-\u9fff])"
    r"|(?<![A-Za-z0-9-])\d{1,2}[.、．]\s*(?=[\u4e00-\u9fff])"
)

# task 描述里允许补动词的最低汉字重合度。低于此值视为整条编造。
_PARTIAL_CJK_FLOOR = 0.6


class TracePolicy(Enum):
    ZERO_TOLERANCE = "zero_tolerance"
    ALLOW_VERB_COMPLETION = "allow_verb_completion"


# 哪个字段能放宽到「允许补动词」，是产品判断，不是实现细节。
FIELD_POLICY: dict[str, TracePolicy] = {
    "subject": TracePolicy.ZERO_TOLERANCE,
    "quantity": TracePolicy.ZERO_TOLERANCE,
    "requirements": TracePolicy.ZERO_TOLERANCE,
    "extras": TracePolicy.ZERO_TOLERANCE,
    "task": TracePolicy.ALLOW_VERB_COMPLETION,
}


def strip_markers(text: str) -> str:
    """去掉列表序号：「1.数学」→「数学」。

    序号不是内容。序号里的数字进了词元集，截断的页码就会蒙混过关——
    原文「1.数学练习册P12-13」里写「P1」，若「1」还在词元集里就查不出问题。

    规则要窄，宁可漏剥不可错剥：「P12-13.」句末的「13.」是页码的一部分
    （前面是连字符），「1、2页」的「1、」后面是数字（那是页码范围，不是条目序号），
    「抄写生字（2）遍」的「（2）」是数量（前面是汉字），三种都不能剥。
    剥错了就等于删掉一个真实数字，词元集随之少一个，
    「抄写生字2遍」这种真作业反而会被判成杜撰。
    已知漏网：「抄写生字，（2）遍」这种「标点 + 括号数量」仍会被剥（见模块说明）；
    「生字2)遍」这种紧跟汉字的右括号形也不剥（与序号无法区分）。
    """
    return _ENUM_MARK.sub("", text or "")


def norm(s: object) -> str:
    """去掉标点、emoji、空白与装饰符，只留汉字/字母/数字，并转小写。

    去标点是为了让「P12-13」与「P12–P13」可比；代价是分隔符信息全丢，
    所以词元必须从原文切，不能从 norm 后的串切。
    """
    return _KEEP.sub("", str(s or "")).lower()


def is_subseq(needle: str, hay: str) -> bool:
    """needle 的字符按顺序出现在 hay 中即可（允许中间插入别的字符）。

    空 needle 返回 False：空串不是「出现在 hay 里」。要判空请调用方自己判。
    """
    if not needle:
        return False
    it = iter(hay)
    return all(c in it for c in needle)


class Provenance:
    """预先算好原文的三种形态，供批量溯源判定。

    词元必须从「原文」而非 norm 后的字符串里切：norm 会把 P12-13 粘成 p1213，
    导致模型写的 P12–P13 切成 {p,12,13} 却对不上 {p,1213}。
    """

    def __init__(self, raw_text: str) -> None:
        self.raw = raw_text or ""
        # 序号先去掉：它不是内容，留着会让截断的页码蒙混过关
        clean = strip_markers(self.raw)
        self.norm = norm(clean)
        self.token_seq = _TOK.findall(clean.lower())
        self.tokens = set(self.token_seq)
        self.cjk = set(_CJK.findall(clean))

    def _has_token(self, token: str) -> bool:
        """这个词元在原文里有没有出处。

        - 原样出现 → 有；
        - 是原文相邻词元的拼接（"1213" = "12" + "13"，模型去掉了分隔符）→ 有；
        - 找不到，或只是某个原文词元的一截（"1" vs "12"）→ 没有。
        """
        if token in self.tokens:
            return True
        seq = self.token_seq
        for i in range(len(seq)):
            acc = ""
            for j in range(i, len(seq)):
                acc += seq[j]
                if acc == token:
                    return True
                if len(acc) >= len(token):
                    break
        return False

    def _sourced(self, tokens: list[str]) -> bool:
        """值的每个词元都要有出处（spec §5.2：数字与字母词元必须全部命中原文）。"""
        return all(self._has_token(t) for t in tokens)

    def trace(self, value: object, *,
              policy: TracePolicy = TracePolicy.ZERO_TOLERANCE) -> TraceLevel:
        """判定字段值在原文里的出处等级。

        空值一律 UNSOURCED：空是「没有这个字段」，不是「这个字段被杜撰」——
        要把空字段当正常处理的调用方自己判空后跳过。

        ZERO_TOLERANCE（subject/quantity/requirements/extras）差一个字就不采信；
        ALLOW_VERB_COMPLETION 只给 task 档：允许补动词（原文「练习册」→
        「完成练习册」），但前提是数字与字母词元全部命中且汉字重合度 ≥ 0.6，
        所以「P14-15」这种改页码、「观察日记一篇」这种整条编造仍会被拦住。
        """
        # 值侧也按同样的规则剥：模型逐字摘录原文时会带上「1.」，
        # 只剥源侧会把这种忠实的摘录判成无出处
        s = strip_markers(str(value or ""))
        v = norm(s)
        if not v:
            return TraceLevel.UNSOURCED
        vt = _TOK.findall(s.lower())
        vc = set(_CJK.findall(s))
        # 词元闸在前：数字/字母词元没全部命中原文，就不许走子串/子序列判定。
        # norm 把 "P12-13" 压成 "p1213"，没有这道闸，"P1"（P12-13 的截断）
        # 会被子串判定当成逐字命中，页码错了还满身正装。
        if self._sourced(vt):
            if v in self.norm:
                return TraceLevel.VERBATIM
            if is_subseq(v, self.norm):
                return TraceLevel.NORMALIZED
            if vc <= self.cjk:
                return TraceLevel.TOKENS_MATCH
        if policy is TracePolicy.ALLOW_VERB_COMPLETION and self._sourced(vt) and vc:
            if len(vc & self.cjk) / len(vc) >= _PARTIAL_CJK_FLOOR:
                return TraceLevel.PARTIAL
        return TraceLevel.UNSOURCED
