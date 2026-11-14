"""配置：命令行 > 环境变量 > config.toml / profile.toml > 内置默认。

环境变量前缀统一 HW_（HW_NAME / HW_SKELETON / HW_SKIN / HW_OUT / HW_TEXT_MODEL /
HW_OCR_MODEL）。凭证不在此列：DASHSCOPE_API_KEY 只由 llm_client 从环境读取，
本模块不认识它。把密钥做成一个「配置字段」，下一步就是它被写进 config.toml
然后提交——那一步不该有路可走。

out_dir 保持用户写下的样子（相对路径按调用时的 cwd 解释），本模块不替人猜根目录。
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from homework_compass.errors import ConfigError

DEFAULTS: dict = {
    "name": "",
    "default_skeleton": "quest-map",
    "default_skin": "dinosaur",
    "text_model": "qwen-plus",
    "ocr_model": "qwen-vl-ocr",
    "fonts": (),
    "out_dir": "out",
    # 主题底图目录：生成脚本 tools/gen_bases.py 的输出位置
    "base_dir": "assets/bases",
}

_ENV_MAP = {"HW_NAME": "name", "HW_SKELETON": "default_skeleton",
            "HW_SKIN": "default_skin", "HW_OUT": "out_dir",
            "HW_TEXT_MODEL": "text_model", "HW_OCR_MODEL": "ocr_model"}

_STRING_FIELDS = frozenset(DEFAULTS) - {"fonts", "out_dir", "base_dir"}
_DIR_FIELDS = {"out_dir", "base_dir"}


@dataclass(frozen=True, slots=True)
class Config:
    name: str
    default_skeleton: str
    default_skin: str
    text_model: str
    ocr_model: str
    fonts: tuple[str, ...]
    out_dir: Path
    base_dir: Path


def _read_toml(path: Path, known: dict, label: str) -> dict:
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} 不是合法 TOML：{e}") from e
    unknown = set(data) - set(known)
    if unknown:
        # 打错的键静默失效比报错更糟：用户以为自己配置好了
        raise ConfigError(f"{label} 不认识这些键：{sorted(unknown)}；可用键：{sorted(known)}")
    return data


def load_profile(root: Path | None = None) -> dict:
    """姓名 / 默认骨架 / 默认皮肤。方案文档的「一次设置、长期复用」，纯文件不引数据库。"""
    base = Path(root) if root else Path.cwd()
    return _read_toml(base / "profile.toml", DEFAULTS, "profile.toml")


def load_config(root: Path | None = None) -> Config:
    base = Path(root) if root else Path.cwd()
    merged = dict(DEFAULTS)
    merged.update(_read_toml(base / "config.toml", DEFAULTS, "config.toml"))
    merged.update(load_profile(base))
    for env, field in _ENV_MAP.items():
        if os.environ.get(env):
            merged[field] = os.environ[env]
    _check_types(merged)
    return Config(**{**merged, "out_dir": Path(merged["out_dir"]),
                     "base_dir": Path(merged["base_dir"]),
                     "fonts": tuple(merged["fonts"])})


def _check_types(merged: dict) -> None:
    """值类型错了也当场报错：`name = 123` 要等到拼标题时才炸，那时已经出了半张图。"""
    for field in sorted(_STRING_FIELDS):
        if not isinstance(merged[field], str):
            raise ConfigError(
                f"{field} 必须是字符串，读到 {type(merged[field]).__name__}：{merged[field]!r}")
    fonts = merged["fonts"]
    # `fonts = "/path/a.ttc"` 会被 tuple() 拆成一个个字符，解析字体时给出二十条假路径
    if isinstance(fonts, str) or not isinstance(fonts, (list, tuple)):
        raise ConfigError(
            f"fonts 要写成数组：fonts = [\"/path/a.ttc\", …]；读到 {type(fonts).__name__}：{fonts!r}")
    for f in _DIR_FIELDS:
        if not isinstance(merged[f], (str, Path)):
            raise ConfigError(f"{f} 必须是字符串路径，读到 {type(merged[f]).__name__}")


def load_dotenv_default(root: Path | None = None) -> None:
    """把 .env 灌进环境变量（已存在的不覆盖）。

    这仍然算「只从环境读取」：`.env` 是被 .gitignore 排除的环境载体，
    而不是配置体系里的一个字段——它承载的 key 照样进不了 Config。
    """
    candidate = (Path(root) if root else Path.cwd()) / ".env"
    if not candidate.is_file():
        return
    for raw in candidate.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip():
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
