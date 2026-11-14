"""版式骨架：留白区的归一化坐标是本文件唯一的事实来源。

生图提示词由这些坐标自动拼装，Pillow 文字层读同一批坐标，
因此「AI 画出来的框」和「我们写字的位置」物理上不可能对不上——
这是双层架构最大的风险点（留白与落位漂移）的结构性解法。

build_prompt 在本版没有被任何生产路径调用，但绝不能删：它就是上述不变量的
另一半。删掉它，坐标契约退化成「只有文字层用得上的坐标表」，
接生图的那个 spec 必然另写一份提示词，契约当场失效。

坐标约定：x/y/w/h 均为 0..1 的归一化值，原点左上角，对应 A4 竖版 300dpi。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

A4_W = 2480
A4_H = 3508
A4_DPI = 300

# 10mm 换算到 300dpi：10 / 25.4 * 300 ≈ 118.1px。spec §6.3 的硬底线。
MIN_MARGIN_PX = 10 * A4_DPI / 25.4


class ZoneKind(str, Enum):
    TITLE = "title"
    STATION = "station"
    EXTRAS = "extras"
    REWARD = "reward"


@dataclass(frozen=True, slots=True)
class Zone:
    key: str
    kind: ZoneKind
    x: float
    y: float
    w: float
    h: float
    px: int = 0  # station 专用：序号
    role: str = ""

    def __post_init__(self) -> None:
        # 页边距在构造期就查：靠人核对坐标表迟早会漂，漂到打印纸上才发现。
        if self.x < 0 or self.y < 0:
            raise ValueError(f"{self.key}: 坐标越界（x={self.x}, y={self.y}）")
        for axis, pos, size, span in (("x", self.x, self.w, A4_W),
                                      ("y", self.y, self.h, A4_H)):
            for edge, dist in (("起始", pos), ("结束", 1.0 - pos - size)):
                if dist * span < MIN_MARGIN_PX:
                    raise ValueError(
                        f"{self.key}: {axis} {edge}页边距 {round(dist * span)}px "
                        f"低于 10mm（{round(MIN_MARGIN_PX)}px）要求")

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """归一化坐标 -> A4 300dpi 像素矩形 (left, top, right, bottom)。"""
        return (
            round(self.x * A4_W),
            round(self.y * A4_H),
            round((self.x + self.w) * A4_W),
            round((self.y + self.h) * A4_H),
        )


@dataclass(frozen=True, slots=True)
class Skeleton:
    name: str
    cn_name: str
    desc: str
    zones: list[Zone] = field(default_factory=list)

    @property
    def stations(self) -> list[Zone]:
        return sorted((z for z in self.zones if z.kind is ZoneKind.STATION),
                      key=lambda z: z.px)


def quest_map(n_stations: int = 6) -> Skeleton:
    """S 形关卡路径：左右交错向下，终点宝箱在右下。

    poc 允许 3-8 关，但 7 关起最后一排会跑出 page（pitch 0.126 × 高度 0.112 +
    10mm 边距），而 poc 没有边距校验所以一直没人发现。spec §6.1 只要 6 个
    关卡位，§6.3 又要求项数超限就报错而不是静默截断，所以上限收到 6。
    """
    if not 3 <= n_stations <= 6:
        raise ValueError(
            "quest-map 只放得下 3-6 个关卡：第 6 关底边 87.7% 已经贴着易漏项带"
            "（90.5%），再加一排就破 10mm 页边距。更多项请换骨架或分页（spec §6.3）。")

    top, pitch, h = 0.135, 0.126, 0.112
    w, xl, xr = 0.40, 0.06, 0.54
    zones = [Zone("title", ZoneKind.TITLE, 0.080, 0.035, 0.840, 0.072,
                  role="日期+姓名+口号")]

    for i in range(1, n_stations + 1):
        x = xl if i % 2 == 1 else xr
        zones.append(
            Zone(
                key=f"station-{i}",
                kind=ZoneKind.STATION,
                x=x,
                y=top + (i - 1) * pitch,
                w=w,
                h=h,
                px=i,
                role=f"第 {i} 关作业卡片",
            )
        )

    zones.append(Zone("extras", ZoneKind.EXTRAS, 0.060, 0.905, 0.580, 0.055,
                      role="易漏项警示条"))
    zones.append(Zone("reward", ZoneKind.REWARD, 0.680, 0.905, 0.260, 0.055,
                      role="奖励留白区"))

    return Skeleton(
        name="quest-map",
        cn_name="闯关游戏地图",
        desc="S 形关卡路径，每项作业是一个关卡，终点是宝箱奖励",
        zones=zones,
    )


SKELETONS: dict[str, Callable[[], Skeleton]] = {"quest-map": quest_map}


def get_skeleton(name: str) -> Skeleton:
    """所有外部输入的骨架名都走这里，不直接 `SKELETONS[...]`。

    CLI 退出码契约里 4 = 参数错误；KeyError 会被当成意外崩溃，
    既进不了 except 分支，也告诉不了人到底能用什么。
    """
    try:
        return SKELETONS[name]()
    except KeyError:
        raise ValueError(f"未知骨架 {name!r}，可选：{sorted(SKELETONS)}") from None


def skin_palette(skin: str) -> dict[str, str]:
    """皮肤只影响少量配色线索；关键信息靠形状区分，保证黑白打印可读。"""
    palettes = {
        "dinosaur": {"accent": "#3F7D3A", "panel": "#FFFFFF"},
        "space": {"accent": "#2C3E7A", "panel": "#FFFFFF"},
        "ocean": {"accent": "#1F6FA8", "panel": "#FFFFFF"},
        "pixel": {"accent": "#4A4A4A", "panel": "#FFFFFF"},
        "candy": {"accent": "#A8467B", "panel": "#FFFFFF"},
    }
    return palettes.get(skin, {"accent": "#33415C", "panel": "#FFFFFF"})


def build_prompt(skeleton: Skeleton, skin: str) -> str:
    """把坐标契约翻译成生图提示词：底图必须只有装饰，且留出这些空框。

    签名里只有骨架与皮肤，作业文字永远进不来——「底图不含文字、
    文字层后画」不是靠自觉，是靠这里没有可传入文字的入口。
    """
    skin_cn = {
        "dinosaur": "恐龙",
        "space": "太空宇航",
        "ocean": "海底世界",
        "pixel": "像素游戏",
        "candy": "糖果甜品",
    }.get(skin, skin)

    lines = [
        f"儿童每日作业目标图模板底图，{skeleton.cn_name}版式（{skeleton.desc}），"
        f"主题皮肤：{skin_cn}风格。",
        "A4 竖版，扁平矢量卡通插画，粗描边，明亮但柔和的儿童配色，"
        "大量留白，画面元素沿四周分布，中心区域保持干净。",
        "构图要求：一条 S 形虚线路径从顶部蜿蜒到底部，路径上均匀分布 "
        f"{len(skeleton.stations)} 个关卡框，路径终点是一个礼盒宝箱；"
        "顶部有一条横幅装饰带，底部有两条短装饰条。",
        "以下每个区域都必须是【空的、内部纯白无内容】的圆角框，"
        "框内不得绘制任何文字、图形、图标或纹理，那是留给后期排版的留白："
        "（坐标为整张画布的百分比，横向 x%–x%、纵向 y%–y%）",
    ]

    for z in skeleton.zones:
        x1, y1 = round(z.x * 100, 1), round(z.y * 100, 1)
        x2, y2 = round((z.x + z.w) * 100, 1), round((z.y + z.h) * 100, 1)
        tag = f"第 {z.px} 号关卡框" if z.kind is ZoneKind.STATION else z.role
        lines.append(f"- {tag}：横向 {x1}%–{x2}%，纵向 {y1}%–{y2}%")

    lines += [
        "严格禁止：画面中不出现任何汉字、英文字母、数字、标点、伪文字或乱码符号，"
        "所有框内一律空白；不要水印、不要签名、不要 logo。",
        "四周各保留至少 3% 的干净页边距，避免装饰被裁切；黑白打印友好。",
    ]
    return "\n".join(lines)


def zones_report(skeleton: Skeleton) -> str:
    """打印坐标契约，便于人工核对底图留白是否与文字对位。"""
    rows = []
    for z in skeleton.zones:
        l, t, r, b = z.rect
        rows.append(
            f"{z.key:<12} {z.kind.value:<8} px{z.px or '-':>3}  "
            f"({l:>4},{t:>4})-({r:>4},{b:>4})  {(r-l):>4}x{(b-t):>4}"
        )
    return "\n".join(rows)
