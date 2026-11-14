"""主题元信息：一套以主题为中心的皮肤 + 底图 + 兴趣标签映射。

这是「元能力」的唯一事实来源：
  - 生成脚本 tools/gen_bases.py 按 THEMES 每个主题画一张底图；
  - 渲染 render() 按主题自动选底图与配色；
  - 前端按主题展示中文名与兴趣标签。

关键约束（与 skeleton.py 的 skin_palette 一致）：
  - 关键信息靠形状区分，配色只是线索，保证黑白打印可读。
  - 底图文件名固定为 <assets>/<theme>_quest-map.png，留白区必须纯白。
"""

from __future__ import annotations

from dataclasses import dataclass

# 每个主题的底图装饰色板。面板恒白，accent 是框描边/星标色。
_THEME_PALETTES: dict[str, dict[str, str]] = {
    "dinosaur": {"accent": "#3F7D3A", "deco": "#8FBC94", "deco_dark": "#2F5D2F", "bg": "#F2F8EF"},
    "space":    {"accent": "#2C3E7A", "deco": "#8BB0E8", "deco_dark": "#1F2B5C", "bg": "#EAF0FB"},
    "robot":    {"accent": "#47A39A", "deco": "#8CD0C9", "deco_dark": "#2F7B72", "bg": "#EEF8F6"},
    "ocean":    {"accent": "#1F6FA8", "deco": "#6FB3DC", "deco_dark": "#14527E", "bg": "#E8F4FB"},
    "candy":    {"accent": "#A8467B", "deco": "#E8A0C3", "deco_dark": "#7A2E57", "bg": "#FBF0F5"},
    "car":      {"accent": "#C0562B", "deco": "#E89B6B", "deco_dark": "#8F3E1C", "bg": "#FBF1EA"},
    "animal":   {"accent": "#8A6D3B", "deco": "#D2B585", "deco_dark": "#5E4A24", "bg": "#F6F1E6"},
    "princess": {"accent": "#A0537E", "deco": "#E0B3CF", "deco_dark": "#6E3A55", "bg": "#FBF0F4"},
    "castle":   {"accent": "#5B4A8A", "deco": "#B2A6D9", "deco_dark": "#3F3163", "bg": "#F1EEFB"},
    "pixel":    {"accent": "#4A4A4A", "deco": "#9AA5B1", "deco_dark": "#2E2E2E", "bg": "#F1F3F5"},
}

# 兴趣标签 → 主题。用在候选屏：孩子选过「恐龙」就把恐龙主题排前。
_INTEREST_TO_THEME: dict[str, str] = {
    "恐龙": "dinosaur", "动物世界": "animal", "海洋生物": "ocean",
    "太空": "space", "外星人": "space", "未来世界": "space",
    "机器人": "robot", "积木": "pixel",
    "公主": "princess", "王子": "princess", "魔法": "castle", "城堡": "castle",
    "汽车": "car", "美食": "candy", "糖果": "candy",
    "奥特曼": "robot", "海底小纵队": "ocean", "超级飞侠": "car", "汪汪队": "animal",
}

# 主题排序：候选屏默认展示顺序，与 child/edit.uvue 的 presetInterests 高频一致
_THEME_ORDER: list[str] = [
    "dinosaur", "space", "robot", "ocean", "candy",
    "car", "animal", "princess", "castle", "pixel",
]

_CN: dict[str, str] = {
    "dinosaur": "恐龙", "space": "太空宇航", "robot": "机器人",
    "ocean": "海洋世界", "candy": "糖果甜品", "car": "汽车小镇",
    "animal": "动物森林", "princess": "公主物语", "castle": "魔法城堡", "pixel": "像素游戏",
}


@dataclass(frozen=True, slots=True)
class Theme:
    key: str
    cn: str
    accent: str
    deco: str
    deco_dark: str
    bg: str
    interest_tags: tuple[str, ...]
    base_file: str

    @property
    def interest_list(self) -> list[str]:
        return list(self.interest_tags)


def _themes() -> list[Theme]:
    out: list[Theme] = []
    for key in _THEME_ORDER:
        p = _THEME_PALETTES[key]
        tags = [tag for tag, t in _INTEREST_TO_THEME.items() if t == key]
        out.append(Theme(
            key=key, cn=_CN[key],
            accent=p["accent"], deco=p["deco"], deco_dark=p["deco_dark"], bg=p["bg"],
            interest_tags=tuple(tags),
            base_file=f"{key}_quest-map.png",
        ))
    return out


def get_themes() -> list[Theme]:
    return _themes()


def get_theme(key: str) -> Theme | None:
    for t in _themes():
        if t.key == key:
            return t
    return None


def skin_palette(skin: str) -> dict[str, str]:
    """渲染所需的 accent/panel。兼容既有 skin_palette 契约。"""
    t = get_theme(skin)
    return {"accent": t.accent if t else "#33415C", "panel": "#FFFFFF"}


def theme_for_interests(interests: list[str]) -> list[str]:
    """给定孩子兴趣，返回按匹配度排序的主题（匹配优先，其次默认顺序）。"""
    matched = [t for tag in (interests or []) if (t := _INTEREST_TO_THEME.get(tag)) is not None]
    seen: list[str] = []
    for t in matched:
        if t not in seen:
            seen.append(t)
    rest = [k for k in _THEME_ORDER if k not in seen]
    return seen + rest
