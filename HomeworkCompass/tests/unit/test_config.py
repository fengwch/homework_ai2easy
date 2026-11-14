from pathlib import Path

import pytest

from homework_compass.config import (
    Config, DEFAULTS, load_config, load_dotenv_default, load_profile,
)


def write(root: Path, name: str, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def test_defaults_when_no_files(tmp_path):
    c = load_config(tmp_path)
    assert c.default_skeleton == "quest-map" and c.text_model == "qwen-plus"
    assert c.out_dir == Path(DEFAULTS["out_dir"]) and c.fonts == ()


def test_config_toml_is_read(tmp_path):
    write(tmp_path, "config.toml", 'text_model = "qwen-plus"\nout_dir = "build/out"\n')
    assert load_config(tmp_path).out_dir == Path("build/out")


def test_profile_overrides_config(tmp_path):
    write(tmp_path, "config.toml", 'name = "配置里的人"\n')
    write(tmp_path, "profile.toml", 'name = "小宇"\ndefault_skin = "space"\n')
    c = load_config(tmp_path)
    assert c.name == "小宇" and c.default_skin == "space"


def test_env_wins_over_files(tmp_path, monkeypatch):
    write(tmp_path, "profile.toml", 'name = "小宇"\n')
    monkeypatch.setenv("HW_NAME", "环境变量的人")
    assert load_config(tmp_path).name == "环境变量的人"


def test_unknown_key_is_a_loud_error_not_typo_silence(tmp_path):
    write(tmp_path, "config.toml", 'text_modle = "qwen-plus"\n')   # 手滑打错
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="text_modle"):
        load_config(tmp_path)


def test_invalid_toml_is_reported_with_path(tmp_path):
    write(tmp_path, "config.toml", "name = 小宇\n")                 # 少引号
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="config.toml"):
        load_config(tmp_path)


def test_credentials_cannot_be_configured():
    """凭证不属配置体系：既没有承载它的字段，也没有读它的代码路径。

    本任务全部意义就在这条：只要 `Config` 里没有 `api_key` 这种字段，
    「把 key 写进 config.toml 然后提交」这件事在结构上就无法发生。
    """
    import homework_compass.config as cfg
    assert not any("api_key" in f.lower() or "token" in f.lower()
                   for f in Config.__slots__)
    assert not hasattr(cfg, "api_key")
    text = Path(cfg.__file__).read_text(encoding="utf-8")
    # docstring 里提到变量名是允许的（它是说明），被禁止的是真的去读它
    assert 'environ.get("DASHSCOPE_API_KEY")' not in text
    assert 'getenv("DASHSCOPE_API_KEY")' not in text


def test_dotenv_sets_env_without_overwriting(tmp_path, monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    write(tmp_path, ".env", "DASHSCOPE_API_KEY=sk-from-file\n")
    load_dotenv_default(tmp_path)
    import os
    assert os.environ["DASHSCOPE_API_KEY"] == "sk-from-file"
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-real")
    load_dotenv_default(tmp_path)
    assert os.environ["DASHSCOPE_API_KEY"] == "sk-real"       # setdefault 语义


def test_dotenv_skips_comments_blank_and_non_assignments(tmp_path, monkeypatch):
    monkeypatch.delenv("HW_SKIN", raising=False)
    write(tmp_path, ".env", "# 注释\n\n不是赋值\nHW_SKIN = 'ocean'\n")
    load_dotenv_default(tmp_path)
    import os
    assert os.environ["HW_SKIN"] == "ocean"      # 去空格、去引号


def test_fonts_as_string_is_rejected_not_split_into_chars(tmp_path):
    """`fonts = "/path/a.ttc"` 会被 tuple() 拆成一个个字符，报错比二十条假路径强。"""
    write(tmp_path, "config.toml", 'fonts = "/System/Library/Fonts/PingFang.ttc"\n')
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="fonts"):
        load_config(tmp_path)


def test_wrong_value_type_is_rejected_with_field_name(tmp_path):
    write(tmp_path, "config.toml", "name = 123\n")
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="name"):
        load_config(tmp_path)


def test_fonts_from_toml_become_a_tuple(tmp_path):
    write(tmp_path, "config.toml", 'fonts = ["/a.ttc", "/b.ttc"]\n')
    assert load_config(tmp_path).fonts == ("/a.ttc", "/b.ttc")


def test_load_profile_missing_file_is_empty_dict(tmp_path):
    assert load_profile(tmp_path) == {}
