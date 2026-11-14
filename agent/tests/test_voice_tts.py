"""
TTS（语音合成）自检与测试。
- check_tts_setup() 用于运维/CLI 自检；
- 集成测试在配置 + SDK 齐全时调用真实 synthesize，否则跳过；
- 长文本分段与配置读取有单元测试。
"""
import pytest
from unittest.mock import patch, MagicMock

from voice_synthesis.aliyun_tts import (
    check_tts_setup,
    synthesize,
    _split_text_for_tts,
    _get_max_chars_per_request,
)


class TestCheckTTSSetup:
    """TTS 自检函数测试。"""

    def test_check_tts_setup_returns_dict(self):
        """check_tts_setup 返回包含 ok/config_ready/nls_sdk_available/message 的字典。"""
        result = check_tts_setup()
        assert isinstance(result, dict)
        assert "ok" in result
        assert "config_ready" in result
        assert "nls_sdk_available" in result
        assert "acs_available" in result
        assert "message" in result
        assert isinstance(result["ok"], bool)
        assert isinstance(result["message"], str)


class TestSynthesize:
    """语音合成测试：配置与 SDK 齐全时调用真实接口，否则跳过。"""

    @pytest.fixture(scope="class")
    def tts_ready(self):
        """检查 TTS 是否就绪（配置 + NLS SDK）。"""
        return check_tts_setup()

    def test_synthesize_empty_text(self):
        """空文本应返回 success=False、error 提示。"""
        result = synthesize("")
        assert result["success"] is False
        assert "error" in result
        assert "format" in result

    def test_synthesize_with_real_api(self, tts_ready):
        """配置与 SDK 齐全时，对短文本进行真实合成。"""
        if not tts_ready["ok"]:
            pytest.skip(
                f"TTS 未就绪，跳过真实合成测试: {tts_ready['message']}\n"
                "请设置 ALIYUN_TTS_* 环境变量并执行 pip install aliyun-nls aliyun-python-sdk-core"
            )
        result = synthesize("测试语音合成", speech_rate=0)
        assert result["success"] is True, f"synthesize 失败: {result.get('error')}"
        assert "audio_data" in result
        assert isinstance(result["audio_data"], bytes)
        assert len(result["audio_data"]) > 0
        assert result.get("format") in ("mp3", "wav", "pcm")


class TestSplitTextForTTS:
    """长文本分段逻辑与配置。"""

    def test_split_empty(self):
        assert _split_text_for_tts("", 300) == []
        assert _split_text_for_tts("  \n  ", 300) == []

    def test_split_under_limit(self):
        assert _split_text_for_tts("短文本", 300) == ["短文本"]
        assert _split_text_for_tts("正好三百字" + "x" * 295, 300) == ["正好三百字" + "x" * 295]

    def test_split_at_sentence_end(self):
        # 优先在。！？；\n 处切分
        text = "第一句。第二句！第三句？"
        segs = _split_text_for_tts(text, 5)
        assert len(segs) >= 2
        assert "".join(segs) == text

    def test_split_hard_cut_no_sentence_end(self):
        # 无句末时按 max_chars 硬切
        text = "没有句号" * 80  # 很长
        segs = _split_text_for_tts(text, 20)
        assert all(len(s) <= 20 for s in segs)
        assert "".join(segs) == text

    def test_get_max_chars_default(self):
        n = _get_max_chars_per_request()
        assert isinstance(n, int)
        assert n >= 1

    @patch("voice_synthesis.aliyun_tts._synthesize_with_sdk")
    @patch("voice_synthesis.aliyun_tts._get_nls_token", return_value="fake-token")
    @patch.dict("os.environ", {
        "ALIYUN_TTS_ACCESS_KEY_ID": "id",
        "ALIYUN_TTS_ACCESS_KEY_SECRET": "secret",
        "ALIYUN_TTS_APPKEY": "appkey",
    }, clear=False)
    def test_long_text_batched_and_concatenated(self, mock_token, mock_sdk):
        """长文本应被拆成多段请求，各段音频拼接后返回。"""
        # max_chars=2 时 "一二三四五" 会拆成 3 段
        mock_sdk.side_effect = [
            {"success": True, "audio_data": b"a1", "format": "mp3"},
            {"success": True, "audio_data": b"a2", "format": "mp3"},
            {"success": True, "audio_data": b"a3", "format": "mp3"},
        ]
        with patch("voice_synthesis.aliyun_tts._get_max_chars_per_request", return_value=2):
            result = synthesize("一二三四五", format="mp3")
        assert result["success"] is True
        assert result["audio_data"] == b"a1" + b"a2" + b"a3"
        assert result["format"] == "mp3"
        assert mock_sdk.call_count == 3
