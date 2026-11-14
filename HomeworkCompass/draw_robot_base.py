"""一次性脚本：画「可爱桌面机器人」主题 A4 底图，坐标直接取 quest-map 骨架契约。

只画装饰（路径、机器人、齿轮、星点、空框），框内一律纯白留白。
产物：assets/base_robot_quest-map.png（2480x3508 @300dpi）
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, "src")
from homework_compass.layout.skeleton import A4_DPI, A4_H, A4_W, get_skeleton  # noqa: E402

NAVY = (44, 62, 80)
MINT = (211, 234, 217)
MINT_D = (138, 185, 150)
MINT_L = (232, 246, 235)
CREAM = (255, 248, 232)
CORAL = (245, 145, 112)
BG = (246, 251, 247)

img = Image.new("RGB", (A4_W, A4_H), BG)
d = ImageDraw.Draw(img, "RGBA")

sk = get_skeleton("quest-map")
Z = {z.key: z.rect for z in sk.zones}
ST = [Z[f"station-{i}"] for i in range(1, 7)]


def center(box):
    x0, y0, x1, y1 = box
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def I(*v):
    """rounded_rectangle 只收整数：半径与描边宽度都得是 int。"""
    return [int(round(x)) for x in v]


def catmull(pts, n=36):
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


def dotted_path(pts, step=30, r=7, fill=(168, 213, 181, 220)):
    """沿折线等距撒点：按累计弧长走，视觉才匀。"""
    acc, prev = 0.0, pts[0]
    for p in pts[1:]:
        seg = math.dist(prev, p)
        if seg == 0:
            continue
        t = 0.0
        while acc + (seg - t) >= step:
            t += step - acc
            acc = 0.0
            x = prev[0] + (p[0] - prev[0]) * t / seg
            y = prev[1] + (p[1] - prev[1]) * t / seg
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        acc += seg - t
        prev = p


def star(cx, cy, r, fill, outline=None, w=4):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.44
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill, outline=outline, width=w)


def gear(cx, cy, r, teeth=9, fill=MINT_D):
    pts = []
    for i in range(teeth * 2):
        ang = i * math.pi / teeth
        rr = r if i % 2 == 0 else r * 0.76
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill, outline=NAVY, width=5)
    d.ellipse([cx - r * .34, cy - r * .34, cx + r * .34, cy + r * .34],
              fill=BG, outline=NAVY, width=4)


def robot(cx, cy, s=1.0):
    """一只正经的桌面机器人：圆角机身 + 奶油面板 + 大眼 + 天线 + 轮子。"""
    bw, bh = 236 * s, 206 * s
    for dx in (-62 * s, 62 * s):
        d.ellipse([cx + dx - 32 * s, cy + bh / 2 + 4 * s,
                   cx + dx + 32 * s, cy + bh / 2 + 68 * s],
                  fill=NAVY, outline=NAVY)
        d.ellipse([cx + dx - 13 * s, cy + bh / 2 + 23 * s,
                   cx + dx + 13 * s, cy + bh / 2 + 49 * s], fill=MINT_L)
    for sgn in (-1, 1):
        ax = cx + sgn * (bw / 2 + 20 * s)
        d.rounded_rectangle(I(ax - 21 * s, cy - 24 * s, ax + 21 * s, cy + 74 * s),
                            radius=int(21 * s), fill=CREAM, outline=NAVY,
                            width=int(7 * s))
        d.ellipse([ax - 26 * s, cy - 52 * s, ax + 26 * s, cy], fill=MINT,
                  outline=NAVY, width=int(7 * s))
    d.rounded_rectangle(I(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2),
                        radius=int(72 * s), fill=MINT, outline=NAVY,
                        width=int(9 * s))
    d.rounded_rectangle(I(cx - bw / 2 + 26 * s, cy - bh / 2 + 24 * s,
                          cx + bw / 2 - 26 * s, cy + bh / 2 - 34 * s),
                        radius=int(48 * s), fill=CREAM, outline=NAVY,
                        width=int(6 * s))
    for dx in (-46 * s, 46 * s):
        d.ellipse([cx + dx - 27 * s, cy - 34 * s, cx + dx + 27 * s, cy + 20 * s],
                  fill=NAVY)
        d.ellipse([cx + dx - 12 * s, cy - 27 * s, cx + dx + 4 * s, cy - 11 * s],
                  fill=(255, 255, 255, 235))
    for dx in (-88 * s, 88 * s):
        d.ellipse([cx + dx - 15 * s, cy + 14 * s, cx + dx + 15 * s, cy + 44 * s],
                  fill=(245, 145, 112, 110))
    d.arc([cx - 26 * s, cy + 6 * s, cx + 26 * s, cy + 46 * s], 20, 160,
          fill=NAVY, width=int(6 * s))
    d.line([cx, cy - bh / 2, cx, cy - bh / 2 - 52 * s], fill=NAVY, width=int(7 * s))
    d.ellipse([cx - 17 * s, cy - bh / 2 - 86 * s, cx + 17 * s, cy - bh / 2 - 52 * s],
              fill=CORAL, outline=NAVY, width=int(6 * s))
    d.ellipse([cx - 9 * s, cy + bh / 2 - 28 * s, cx + 9 * s, cy + bh / 2 - 10 * s],
              fill=CORAL, outline=NAVY, width=int(4 * s))


# 1) 虚线路径：串起 6 关
dotted_path(catmull([center(b) for b in ST]))

# 2) 装饰只放在关卡之间的空档里，绝不压框
robot(645, 1112, 1.02)          # 第 1、3 关之间（左侧空档 492px）
robot(1835, 1552, 0.92)         # 第 2、4 关之间（右侧空档）
robot(645, 1996, 1.02)          # 第 3、5 关之间（左侧空档）

gear(1835, 2434, 62)            # 第 4、6 关之间
gear(1948, 2500, 40, teeth=8, fill=MINT)
gear(645, 2856, 58)
gear(760, 2916, 36, teeth=8, fill=MINT)

# 顶部横幅下方那条 99px 的窄带：小星星 + 波浪点
for x, r in ((520, 26), (1240, 34), (1960, 26)):
    star(x, 424, r, CORAL, NAVY, 5)
for x in range(700, 1800, 84):
    d.ellipse([x - 6, 452, x + 6, 464], fill=(168, 213, 181, 200))
for x in range(560, 1940, 420):
    d.ellipse([x - 4, 400, x + 4, 408], fill=(168, 213, 181, 160))

# 3) 空框：白底 + 细描边（文字层会在上面盖 190 alpha 白面板）
for box in ST:
    d.rounded_rectangle(box, radius=38, fill=(255, 255, 255),
                        outline=MINT_D, width=5)

d.rounded_rectangle(Z["title"], radius=42, fill=(255, 255, 255),
                    outline=MINT_D, width=5)
for key in ("extras", "reward"):
    d.rounded_rectangle(Z[key], radius=34, fill=(255, 255, 255),
                        outline=MINT_D, width=5)

# 4) 标题条两端的小天线，让主题从顶部就成立
for bx in (Z["title"][0] - 6, Z["title"][2] + 6):
    d.ellipse([bx - 13, 236, bx + 13, 262], fill=CORAL, outline=NAVY, width=5)
    d.line([bx, 262, bx, 300], fill=NAVY, width=5)

Path("assets").mkdir(exist_ok=True)
out = Path("assets/base_robot_quest-map.png")
img.save(out, dpi=(A4_DPI, A4_DPI))
print(f"写入 {out}  {img.size}")

# 5) 自检：每个空框内部必须是纯白（内缩 14px 避开描边）
for name, (x0, y0, x1, y1) in sorted(Z.items()):
    crop = img.crop((x0 + 14, y0 + 14, x1 - 14, y1 - 14)).convert("L")
    px = list(crop.getdata())
    nonwhite = sum(1 for v in px if v < 250)
    print(f"  {name:12s} 非白 {nonwhite:6d}/{len(px):6d}  "
          f"min={min(px):3d} mean={sum(px) // len(px):3d}")
