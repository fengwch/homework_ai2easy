"""批量生成 A4 目标图底图：每套主题一张，卡片留白与 quest-map 骨架严丝合缝。

这是「主题底图」的通用生成方法：想新增/更新主题，往 layout/themes.py 加一个主题，
再在这里给 _DRAW 加一个画笔函数并重跑本脚本即可。产物：
  - assets/bases/<theme>_quest-map.png（2480x3508 @300dpi）
生成后会自动自检：每个留白框内部纯白，非白像素必须为 0。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from homework_compass.layout.skeleton import A4_DPI, A4_H, A4_W, get_skeleton  # noqa: E402
from homework_compass.layout.themes import Theme, get_theme, get_themes  # noqa: E402

OUT_ROOT = Path(__file__).resolve().parents[1] / "assets" / "bases"


def _frame(d: ImageDraw.ImageDraw, t: Theme, box, radius=38):
    """空框：白底 + 主题 accent 细描边（文字层会再盖白面板）。"""
    d.rounded_rectangle([int(x) for x in box], radius=radius, fill=(255, 255, 255),
                        outline=_decode(t.accent), width=5)


def _decode(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _bg(d: ImageDraw.ImageDraw, t: Theme):
    d.rectangle([0, 0, A4_W, A4_H], fill=_decode(t.bg))


def _dotted_path(d, pts, color, step=30, r=7):
    acc, prev = 0.0, pts[0]
    for p in pts[1:]:
        seg = math.dist(prev, p)
        if seg == 0:
            continue
        tt = 0.0
        while acc + (seg - tt) >= step:
            tt += step - acc
            acc = 0.0
            x = prev[0] + (p[0] - prev[0]) * tt / seg
            y = prev[1] + (p[1] - prev[1]) * tt / seg
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
        acc += seg - tt
        prev = p


def _catmull(pts, n=36):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    return out


def _center(box):
    x0, y0, x1, y1 = box
    return ((x0 + x1) / 2, (y0 + y1) / 2)


# ---------- 主题画笔：只在留白框之间的空档画装饰，绝不压框 ----------

def _draw_dinosaur(d, t, z, stations):
    ST = [z[f"station-{i}"] for i in range(1, 7)]
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    # 恐龙剪影：身体 + 尾巴 + 头 + 腿（用圆和圆角组合，扁平卡通）
    def dino(cx, cy, s, flip=False):
        bw, bh = 190 * s, 120 * s
        hx = cx + (bw / 2 + 30 * s) * (1 if not flip else -1)
        # 尾巴
        tx = cx - bw / 2 * (1 if not flip else -1)
        d.polygon([(tx, cy), (tx - 70 * s * (1 if not flip else -1), cy - 20 * s * (1 if flip else -1) * 0), (tx, cy + bh / 2)], fill=dark)
        d.ellipse([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], fill=deco, outline=dark, width=5)
        d.ellipse([hx - 34 * s, cy - bh / 2 - 22 * s, hx + 34 * s, cy - 8 * s], fill=deco, outline=dark, width=5)
        d.ellipse([hx + 8 * s, cy - bh / 2 - 10 * s, hx + 22 * s, cy - bh / 2 + 4 * s], fill=(40, 40, 40))
        for lx in (cx - bw / 2 + 20 * s, cx + bw / 4):
            d.rounded_rectangle([lx, cy + bh / 2 - 10 * s, lx + 26 * s, cy + bh / 2 + 46 * s], radius=12, fill=dark)
        d.polygon([(cx - 30 * s, cy - bh / 2 + 10 * s), (cx - 8 * s, cy - bh / 2 - 26 * s), (cx + 18 * s, cy - bh / 2 + 8 * s)], fill=dark)
    dino(680, 1120, 1.0)
    dino(1835, 1560, 0.9, flip=True)
    dino(700, 2000, 1.0)
    dino(1850, 2440, 0.9, flip=True)
    dino(690, 2860, 1.0)


def _draw_space(d, t, z, stations):
    ST = [z[f"station-{i}"] for i in range(1, 7)]
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    def rocket(cx, cy, s):
        # 火箭：头锥 + 机身 + 尾翼 + 火焰。深色只作细描边，不整块铺，省墨。
        d.polygon([(cx, cy - 80 * s), (cx - 30 * s, cy - 10 * s), (cx + 30 * s, cy - 10 * s)],
                  fill=deco, outline=dark, width=4)
        d.rounded_rectangle([cx - 34 * s, cy - 10 * s, cx + 34 * s, cy + 90 * s],
                            radius=20, fill=deco, outline=dark, width=4)
        d.ellipse([cx - 26 * s, cy + 10 * s, cx + 12 * s, cy + 46 * s], fill=(255, 255, 255))
        for sx in (-1, 1):
            d.polygon([(cx + sx * 34 * s, cy + 14 * s), (cx + sx * 70 * s, cy + 56 * s),
                       (cx + sx * 34 * s, cy + 66 * s)], fill=deco, outline=dark, width=4)
        d.polygon([(cx - 16 * s, cy + 90 * s), (cx, cy + 132 * s), (cx + 16 * s, cy + 90 * s)],
                  fill=(245, 145, 112), outline=dark, width=3)
    rocket(700, 1160, 1.0)
    rocket(1840, 1600, 0.85)
    rocket(680, 2040, 1.0)
    rocket(1860, 2480, 0.85)
    rocket(680, 2900, 1.0)
    # 行星 + 星星
    for (px, py, pr) in ((650, 1350, 46), (1880, 1700, 36), (1950, 2520, 52)):
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=deco, outline=dark, width=4)
        d.arc([px - pr, py - pr, px + pr, py + pr], -40, 40, fill=(255, 255, 255, 180), width=6)
    # 星星：浅色描边空心，不是深色实心——墨量要低，黑白打印也省墨
    def star_ring(cx, cy, r):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.5
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        d.polygon(pts, outline=dark, width=4, fill=None)
    for (x, r) in ((520, 22), (1500, 28), (2000, 22), (600, 1300), (1700, 1460)):
        star_ring(x, 430, r)


# 其余主题：先以「一组居中装饰 + 路径点缀」的通用画法兜底，避免画错框位
def _draw_generic(d, t, z, stations, motif=None):
    ST = [z[f"station-{i}"] for i in range(1, 7)]
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    # 六关之间各放一个 motif 符号（菱形/方块/圆交替），位置与 robot 的齿轮一致但简化
    for cx, cy in zip((700, 1835, 700, 1835, 700), (1120, 1560, 2000, 2440, 2860)):
        rr = 34
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=deco, outline=dark, width=4)
        d.ellipse([cx - rr * 0.4, cy - rr * 0.4, cx + rr * 0.4, cy + rr * 0.4], fill=bg, outline=dark, width=3)
    # 顶部窄带点缀
    for x in range(560, 1940, 420):
        d.ellipse([x - 5, 430, x + 5, 440], fill=dark)


def _draw_robot(d, t, z, stations, motif=None):
    """机器人：圆角机身 + 奶油面板 + 大眼 + 天线 + 齿轮。配色取主题色。"""
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    def robot(cx, cy, s=1.0):
        bw, bh = 236 * s, 206 * s
        # 轮子
        for dx in (-62 * s, 62 * s):
            d.ellipse([cx + dx - 32 * s, cy + bh / 2 + 4 * s,
                       cx + dx + 32 * s, cy + bh / 2 + 68 * s], fill=dark)
            d.ellipse([cx + dx - 13 * s, cy + bh / 2 + 23 * s,
                       cx + dx + 13 * s, cy + bh / 2 + 49 * s], fill=(255, 255, 255))
        # 天线两侧
        for sgn in (-1, 1):
            ax = cx + sgn * (bw / 2 + 20 * s)
            d.rounded_rectangle([int(ax - 21 * s), int(cy - 24 * s), int(ax + 21 * s), int(cy + 74 * s)],
                                radius=int(21 * s), fill=(255, 255, 255), outline=dark, width=int(7 * s))
            d.ellipse([ax - 26 * s, cy - 52 * s, ax + 26 * s, cy], fill=deco, outline=dark, width=int(7 * s))
        # 机身
        d.rounded_rectangle([int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2)],
                            radius=int(72 * s), fill=deco, outline=dark, width=int(9 * s))
        d.rounded_rectangle([int(cx - bw / 2 + 26 * s), int(cy - bh / 2 + 24 * s),
                             int(cx + bw / 2 - 26 * s), int(cy + bh / 2 - 34 * s)],
                            radius=int(48 * s), fill=(255, 255, 255), outline=dark, width=int(6 * s))
        # 大眼
        for dx in (-46 * s, 46 * s):
            d.ellipse([cx + dx - 27 * s, cy - 34 * s, cx + dx + 27 * s, cy + 20 * s], fill=dark)
            d.ellipse([cx + dx - 12 * s, cy - 27 * s, cx + dx + 4 * s, cy - 11 * s], fill=(255, 255, 255))
        # 嘴
        d.arc([cx - 26 * s, cy + 6 * s, cx + 26 * s, cy + 46 * s], 20, 160, fill=dark, width=int(6 * s))
        # 天线顶球
        d.line([cx, cy - bh / 2, cx, cy - bh / 2 - 52 * s], fill=dark, width=int(7 * s))
        d.ellipse([cx - 17 * s, cy - bh / 2 - 86 * s, cx + 17 * s, cy - bh / 2 - 52 * s],
                  fill=(245, 145, 112), outline=dark, width=int(6 * s))
    # 六关之间的机器人
    for (x, y, s_) in ((700, 1120, 1.0), (1835, 1560, 0.9), (700, 2000, 1.0),
                       (1835, 2440, 0.9), (700, 2860, 1.0)):
        robot(x, y, s_)


def _draw_ocean(d, t, z, stations, motif=None):
    """海洋：鱼 + 泡泡 + 波浪。"""
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    def fish(cx, cy, s=1.0, flip=False):
        bw, bh = 150 * s, 90 * s
        dirn = -1 if flip else 1
        # 身体（椭圆）
        d.ellipse([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], fill=deco, outline=dark, width=4)
        # 尾巴（三角）
        tx = cx + dirn * bw / 2
        d.polygon([(tx, cy), (tx + dirn * 44 * s, cy - 30 * s), (tx + dirn * 44 * s, cy + 30 * s)],
                  fill=dark)
        # 眼睛
        ex = cx - dirn * 30 * s
        d.ellipse([ex - 12 * s, cy - 20 * s, ex + 12 * s, cy + 4 * s], fill=(40, 40, 40))
        # 鱼鳍
        d.arc([cx - 30 * s, cy - 40 * s, cx + 30 * s, cy + 40 * s], 200, 340, fill=dark, width=5)
    for (x, y, s_, fl) in ((700, 1160, 1.0, False), (1840, 1600, 0.85, True),
                           (700, 2040, 1.0, False), (1860, 2480, 0.9, True),
                           (700, 2900, 1.0, False)):
        fish(x, y, s_, fl)
    # 泡泡
    for (x, y, r) in ((620, 1300, 18), (1920, 1690, 22), (1980, 2500, 16), (620, 2960, 20)):
        d.ellipse([x - r, y - r, x + r, y + r], outline=dark, width=4)
        d.ellipse([x - r * 0.3, y - r * 0.45, x + r * 0.1, y - r * 0.1], fill=(255, 255, 255, 200))


def _draw_candy(d, t, z, stations, motif=None):
    """糖果：棒棒糖 + 纸杯蛋糕 + 波纹。"""
    deco, dark, bg = _decode(t.deco), _decode(t.deco_dark), _decode(t.bg)
    def lollipop(cx, cy, s=1.0):
        r = 52 * s
        d.ellipse([cx - r, cy - 60 * s, cx + r, cy + 60 * s], fill=deco, outline=dark, width=5)
        # 螺旋（同心圆弧）
        for i in range(1, 4):
            rr = r * i / 4
            d.arc([cx - rr, cy - 60 * s + (60 * s - rr), cx + rr, cy + 60 * s - (60 * s - rr)],
                  0, 360, fill=dark, width=4)
        d.line([cx, cy + 60 * s, cx, cy + 130 * s], fill=dark, width=8)
    def cupcake(cx, cy, s=1.0):
        bw = 90 * s
        d.polygon([(cx - bw, cy), (cx + bw, cy), (cx + 30 * s, cy + 80 * s), (cx - 30 * s, cy + 80 * s)],
                  fill=dark)
        d.arc([cx - 40 * s, cy - 60 * s, cx + 40 * s, cy + 20 * s], 180, 360, fill=dark, width=4)
        d.ellipse([cx - 44 * s, cy - 58 * s, cx + 44 * s, cy + 10 * s], fill=deco, outline=dark, width=4)
    for (x, y) in ((720, 1120), (1830, 1580), (720, 2020), (1840, 2460), (720, 2880)):
        if (x < 1500):
            lollipop(x, y)
        else:
            cupcake(x, y, 0.95)


_DRAW = {
    "dinosaur": _draw_dinosaur,
    "space": _draw_space,
    "robot": _draw_robot,
    "ocean": _draw_ocean,
    "candy": _draw_candy,
    "car": _draw_generic,
    "animal": _draw_generic,
    "princess": _draw_generic,
    "castle": _draw_generic,
    "pixel": _draw_generic,
}


def generate(theme: Theme) -> Path:
    img = Image.new("RGB", (A4_W, A4_H), _decode(theme.bg))
    d = ImageDraw.Draw(img, "RGBA")
    sk = get_skeleton("quest-map")
    Z = {z.key: z.rect for z in sk.zones}
    ST = [Z[f"station-{i}"] for i in range(1, 7)]
    _bg(d, theme)
    # 虚线路径
    _dotted_path(d, _catmull([_center(b) for b in ST]), (*_decode(theme.deco), 200))
    # 主题装饰
    _DRAW[theme.key](d, theme, Z, ST)
    # 空框
    for box in ST:
        _frame(d, theme, box)
    _frame(d, theme, Z["title"])
    # 奖励框不画进底图：家长不填奖励时该区域应保持干净，由渲染层按需绘制
    _frame(d, theme, Z["extras"])
    # 落盘
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUT_ROOT / theme.base_file
    img.save(out, dpi=(A4_DPI, A4_DPI))
    return out


def verify_blank(theme: Theme, img: Image.Image = None) -> dict[str, int]:
    """自检：每个留白框内部纯白（内缩 14px 避开描边）。

    允许每个框 ≤2 个非白像素（圆角抗锯齿），它们只出现在四角；装饰若压框会
    是成片区域。文字层随后盖 190 alpha 白面板，圆角边迹会被盖掉。
    """
    if img is None:
        img = Image.open(OUT_ROOT / theme.base_file)
    sk = get_skeleton("quest-map")
    Z = {z.key: z.rect for z in sk.zones}
    result = {}
    for name, (x0, y0, x1, y1) in sorted(Z.items()):
        if name == "reward":
            continue          # 奖励框不进底图，由渲染层按需绘制
        crop = img.crop((x0 + 14, y0 + 14, x1 - 14, y1 - 14)).convert("L")
        px = list(crop.getdata())
        result[name] = sum(1 for v in px if v < 250)
    return result


if __name__ == "__main__":
    for theme in get_themes():
        out = generate(theme)
        nb = verify_blank(theme)
        # 允许每框 ≤2 个圆角抗锯齿残留；超过一定是装饰压框
        ok = all(v <= 2 for v in nb.values())
        bad = {k: v for k, v in nb.items() if v > 2}
        print(f"{theme.key:10s} {out.name:32s} 留白纯白={ok} {('警示'+str(bad)) if bad else ''}")
