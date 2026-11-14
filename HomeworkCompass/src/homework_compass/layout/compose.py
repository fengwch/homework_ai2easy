"""文字层：所有中文由 Pillow 精确绘制，保证 100% 准确、可编辑、不发虚。

管线顺序是刻意的：底图先超分到 2480x3508，再在这个原生 300dpi 画布上写字。
反过来（先写字再放大）会让文字发虚，直接违反「正文 ≥14pt 清晰可读」的验收口径。

本模块不碰文件系统、不碰 tty：返回图像与问题清单，落盘由 pipeline 负责。
字体默认按 `fonts` 模块的候选表解析，配置层可以用 `fonts=[…]` 覆盖（spec §6.4）。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import partial

from PIL import Image, ImageDraw

from homework_compass.errors import LayoutError
from homework_compass.layout.fonts import load_font, resolve_font_path
from homework_compass.layout.skeleton import (
    A4_DPI, A4_H, A4_W, Skeleton, Zone, ZoneKind, skin_palette,
)
from homework_compass.models import HomeworkItem, ParsedHomework, RenderIssue

INK = "#1A1A1A"
BODY_PT = 14.0   # 方案文档要求的正文字号下限
NOTE_PT = 10.0
TITLE_PT = 28.0
BODY_FLOOR_PT = 12.0   # 低于此字号就上报，绝不静默截断作业内容
LINE_GAP = 1.28

# 行首禁则：这些标点不能孤零零地出现在一行的开头
NO_LINE_START = "）］｝〉》」』、。，；：？！.,;:!?）"


def pt_to_px(pt: float) -> int:
    return round(pt * A4_DPI / 72.0)


def text_w(s: str, f) -> float:
    return f.getlength(s)


def wrap(text: str, f, max_w: float) -> list[str]:
    """按字符宽度折行，中文无需分词；并做行首禁则处理，避免右括号单独掉到下一行。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if text_w(cur + ch, f) <= max_w or not cur:
            cur += ch
        elif ch in NO_LINE_START and cur:
            # 把前一个字带下来一起换行，保证标点不孤立
            lines.append(cur[:-1])
            cur = cur[-1] + ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def fit_block(text: str, max_w: float, max_h: float, base_px: int,
              floor_px: int, line_gap: float = LINE_GAP,
              *, font=load_font) -> tuple[list[str], int, float]:
    """自动降字号以塞进给定框；返回 (行, 字号px, 行高)。字号触底仍放不下则交调用方上报。"""
    px = base_px
    while True:
        lines = wrap(text, font(px), max_w)
        lh = round(px * line_gap)
        if len(lines) * lh <= max_h or px <= floor_px:
            return lines, px, float(lh)
        px -= 2


def body_px_for(zone_h: int) -> int:
    """给定正文可用高度，返回首行放得下的最大正文字号（px），上限 14pt。

    只做几何换算，不替你判断「这么小还能不能读」——低于
    pt_to_px(BODY_FLOOR_PT) 时由 compose 追加 RenderIssue，交人处理。
    """
    return min(pt_to_px(BODY_PT), max(8, round(zone_h / LINE_GAP)))


def station_text(item: HomeworkItem) -> tuple[str, list[str]]:
    """卡片正文与要求：数量跟在任务后面，与任务重复的要求不再单列。

    校验层已经去过一次重，但 hw.json 可能是 poc 时代写下的（模型层承诺兼容
    那份 JSON），那条路径没有这道保证。印在纸上的重复收不回来，所以这里再挡一次。
    """
    task = f"{item.task}（{item.quantity}）" if item.quantity else item.task
    return task, [r for r in item.requirements if r and r not in item.task]


def draw_zone_guides(img: Image.Image, skeleton: Skeleton) -> None:
    d = ImageDraw.Draw(img)
    for z in skeleton.zones:
        l, t, r, b = z.rect
        d.rectangle([l, t, r, b], outline="#9AA5B1", width=3)


def placeholder_base(skeleton: Skeleton) -> Image.Image:
    """--no-api 用的占位底图：画出留白框本身，用于肉眼核对对位（不含任何美术）。"""
    img = Image.new("RGB", (A4_W, A4_H), "#F3F5F7")
    draw_zone_guides(img, skeleton)
    return img


def upscale_to_a4(base: Image.Image) -> Image.Image:
    if base.size != (A4_W, A4_H):
        base = base.convert("RGB").resize((A4_W, A4_H), Image.LANCZOS)
    return base.convert("RGB")


def _font_loader(candidates: Sequence[str] | None):
    """配置里给了候选表就按它解析（spec §6.4）；没给就用 fonts 模块的默认解析（带记忆）。"""
    if not candidates:
        return load_font
    return partial(load_font, path=resolve_font_path(list(candidates)))


def compose(
    hw: ParsedHomework,
    skeleton: Skeleton,
    *,
    skin: str = "dinosaur",
    base: Image.Image | None = None,
    panel_alpha: int = 190,
    fonts: Sequence[str] | None = None,
) -> tuple[Image.Image, list[RenderIssue]]:
    """底图 + 结构化作业数据 -> A4 300dpi 成品图。返回 (图像, 问题清单)。"""
    canvas = upscale_to_a4(base if base is not None else placeholder_base(skeleton)).copy()
    # 超分已经把画布固定成 A4；这一步是给「以后有人改成先写字再放大」踩刹车
    assert canvas.size == (A4_W, A4_H)

    font = _font_loader(fonts)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    accent = skin_palette(skin)["accent"]
    issues: list[RenderIssue] = []

    items = hw.items
    stations = skeleton.stations
    if len(items) > len(stations):
        raise LayoutError(
            f"作业项 {len(items)} 条超过骨架留白 {len(stations)} 个；"
            "需分页或换骨架（spec §6.3）。")

    _draw_title(od, skeleton, hw, accent, panel_alpha, font)
    for z, it in zip(stations, items):
        _draw_station(od, z, it, accent, panel_alpha, issues, font)
    for z in stations[len(items):]:
        _empty_station(od, z, panel_alpha, font)
    _draw_extras(od, skeleton, hw, accent, panel_alpha, issues, font)
    _draw_reward(od, skeleton, hw, panel_alpha, font)

    out = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    return out, issues


def _round_rect(draw: ImageDraw.ImageDraw, box, radius: int, **kw) -> None:
    draw.rounded_rectangle(box, radius=radius, **kw)


def _panel(draw: ImageDraw.ImageDraw, box, radius: int, fill: str, alpha: int) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=(*_hex(fill), alpha))


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _star(draw, cx: float, cy: float, r: float, fill: str) -> None:
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill, outline=INK, width=3)


def _zone(skeleton: Skeleton, kind: ZoneKind) -> Zone:
    return next(z for z in skeleton.zones if z.kind is kind)


def title_line(hw: ParsedHomework) -> str:
    """标题行。家长写过口号就只显示口号——口号本身就是标题，前面再拼「日期 · 姓名」会让
    家长以为自己的修改没生效；没写口号才退化到「日期 · 姓名 · 今日目标」。"""
    if hw.slogan.strip():
        return hw.slogan.strip()
    return " · ".join(p for p in (hw.date, hw.student_name, "今日目标") if p)


def _draw_title(od, skeleton: Skeleton, hw: ParsedHomework, accent: str, alpha: int,
                font) -> None:
    l, t, r, b = _zone(skeleton, ZoneKind.TITLE).rect
    _panel(od, [l, t, r, b], radius=46, fill="#FFFFFF", alpha=alpha)
    line = title_line(hw)
    lines, px, lh = fit_block(line, (r - l) - 70, (b - t) - 40,
                              pt_to_px(TITLE_PT * 0.78), pt_to_px(16), font=font)
    y = t + ((b - t) - len(lines) * lh) / 2
    for ln in lines:
        od.text(((l + r) / 2, y), ln, font=font(px), fill=INK, anchor="ma")
        y += lh


def _draw_station(od, z: Zone, it: HomeworkItem, accent: str, alpha: int,
                  issues: list[RenderIssue], font) -> None:
    l, t, r, b = z.rect
    _panel(od, [l, t, r, b], radius=40, fill="#FFFFFF", alpha=alpha)
    pad = 34
    inner_l, inner_r = l + pad, r - pad

    # 顶部行：序号徽章 + 科目 + 高优星标（星标=形状冗余，黑白打印也能识别）
    badge_r = 40
    bcx, bcy = inner_l + badge_r, t + badge_r + 18
    od.ellipse([bcx - badge_r, bcy - badge_r, bcx + badge_r, bcy + badge_r],
               fill=accent, outline=INK, width=4)
    od.text((bcx, bcy), str(z.px), font=font(52), fill="#FFFFFF", anchor="mm")

    subject = it.subject or "作业"
    sf = font(pt_to_px(BODY_PT))
    sx = bcx + badge_r + 26
    sw = text_w(subject, sf)
    _round_rect(od, [sx, bcy - 42, sx + sw + 40, bcy + 42], radius=30, fill=accent)
    od.text((sx + 20 + sw / 2, bcy), subject, font=sf, fill="#FFFFFF", anchor="mm")

    if it.priority == "high":
        # 星标 + “重要”都放在标题行内，不给正文让位，避免与任务文字相撞
        sx, sy = inner_r - 40, bcy
        _star(od, sx, sy, 34, "#F2B705")
        od.text((sx - 46, sy), "重要", font=font(36), fill=INK, anchor="rm")

    # 勾选框：由排版引擎画，不依赖 AI
    cb = 56
    od.rectangle([inner_r - cb, b - pad - cb, inner_r, b - pad], outline=INK, width=5)

    task_line, reqs = station_text(it)
    if not it.task:
        issues.append(RenderIssue(z.key, "", "任务内容为空"))

    text_l = inner_l
    text_r = inner_r - cb - 26
    max_w = text_r - text_l
    head_bottom = bcy + badge_r + 22
    bottom = b - pad - 8
    avail_h = bottom - head_bottom

    note_px = pt_to_px(NOTE_PT)
    req_text = "　".join(reqs)
    req_lines, req_px, req_lh = (
        fit_block(req_text, max_w, avail_h * 0.42, note_px, pt_to_px(9), font=font)
        if req_text else ([], 0, 0)
    )

    task_avail = avail_h - len(req_lines) * req_lh
    base_px = body_px_for(avail_h)
    if base_px < pt_to_px(BODY_FLOOR_PT):
        issues.append(RenderIssue(
            z.key, task_line,
            f"正文可用高度不足，字号最多 {round(base_px * 72 / A4_DPI, 1)}pt"
            f"（低于 {BODY_FLOOR_PT}pt 下限）"))
    task_lines, tpx, t_lh = fit_block(task_line, max_w, task_avail, base_px,
                                     pt_to_px(BODY_FLOOR_PT), font=font)
    if tpx < pt_to_px(BODY_PT):
        issues.append(
            RenderIssue(z.key, task_line,
                        f"任务过长，已降到 {round(tpx * 72 / A4_DPI, 1)}pt（低于 14pt 下限）")
        )
    if len(task_lines) * t_lh > task_avail + 2:
        issues.append(RenderIssue(z.key, task_line, "文字放不下，请精简该项"))
        return

    y = head_bottom
    for ln in task_lines:
        od.text((text_l, y), ln, font=font(tpx), fill=INK, anchor="la")
        y += t_lh
    y += 6
    for ln in req_lines:
        od.text((text_l, y), ln, font=font(req_px), fill="#4A5568", anchor="la")
        y += req_lh


def _empty_station(od, z: Zone, alpha: int, font) -> None:
    l, t, r, b = z.rect
    _panel(od, [l, t, r, b], radius=40, fill="#FFFFFF", alpha=max(90, alpha - 90))
    od.text(((l + r) / 2, (t + b) / 2), f"第 {z.px} 关（今日无作业）",
            font=font(pt_to_px(NOTE_PT)), fill="#A0AEC0", anchor="mm")


def _draw_extras(od, skeleton: Skeleton, hw: ParsedHomework, accent: str, alpha: int,
                 issues: list[RenderIssue], font) -> None:
    z = _zone(skeleton, ZoneKind.EXTRAS)
    l, t, r, b = z.rect
    _panel(od, [l, t, r, b], radius=34, fill="#FFF6DC", alpha=min(255, alpha + 40))
    label = "别忘了"
    lf = font(pt_to_px(NOTE_PT * 1.15))
    lw = text_w(label, lf)
    _round_rect(od, [l + 20, t + 14, l + 20 + lw + 40, b - 14], radius=24, fill="#E5533D")
    od.text((l + 40 + lw / 2, (t + b) / 2), label, font=lf, fill="#FFFFFF", anchor="mm")

    extras = [x for x in hw.extras if x]
    text = "　".join(extras) if extras else "（无）"
    x0 = l + 40 + lw + 60
    lines, px, lh = fit_block(text, r - x0 - 24, (b - t) - 24,
                              pt_to_px(NOTE_PT * 1.15), pt_to_px(8.5), font=font)
    if len(lines) * lh > (b - t) - 20:
        issues.append(RenderIssue(z.key, text, "易漏项过多，请精简"))
    y = t + ((b - t) - len(lines) * lh) / 2
    for ln in lines:
        od.text((x0, y), ln, font=font(px), fill=INK, anchor="la")
        y += lh


def _draw_reward(od, skeleton: Skeleton, hw: ParsedHomework, alpha: int, font) -> None:
    """奖励区只在家长写了奖励时才画。

    空字符串 = 家长选择不展示；连框一起省掉，把版面让给作业项。
    """
    reward = (hw.reward or "").strip()
    if not reward:
        return
    z = _zone(skeleton, ZoneKind.REWARD)
    l, t, r, b = z.rect
    _panel(od, [l, t, r, b], radius=34, fill="#FFFFFF", alpha=alpha)
    label = "通关奖励："
    lf = font(pt_to_px(NOTE_PT))
    label_w = text_w(label, lf)
    od.text((l + 26, (t + b) / 2), label, font=lf, fill=INK, anchor="lm")
    # 文案可能较长：从标签右侧开始折行，放不下就逐级缩字号并记 issue
    lines, px, lh = fit_block(reward, r - (l + 26 + label_w) - 20, (b - t) - 20,
                             pt_to_px(NOTE_PT), pt_to_px(BODY_FLOOR_PT), font=font)
    y = (t + b) / 2 - (len(lines) - 1) * lh / 2
    for ln in lines:
        od.text((l + 26 + label_w, y), ln, font=font(px), fill=INK, anchor="lm")
        y += lh
