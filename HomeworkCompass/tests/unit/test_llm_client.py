import pytest

from homework_compass.errors import ApiError, ExtractionError
from homework_compass.parsing.extract import SYSTEM_PROMPT, LlmExtractor


class FakePost:
    def __init__(self, body):
        self.body, self.calls = body, []

    def __call__(self, url, payload, *, timeout=120):
        self.calls.append((url, payload))
        return self.body


def ok(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_prompt_constraints_are_present_in_payload():
    fake = FakePost(ok('{"items": []}'))
    LlmExtractor(transport=fake)("1.数学练习册", date="2026-11-06", name="小宇")
    _, payload = fake.calls[0]
    assert payload["temperature"] == 0
    assert payload["response_format"] == {"type": "json_object"}   # 缺了接口会报错
    assert "逐字摘录" in payload["messages"][0]["content"]
    assert "不要输出 priority" in SYSTEM_PROMPT


@pytest.mark.parametrize("fence", ["```json", "```JSON", "```"])
def test_fences_are_stripped_before_json(fence):
    fake = FakePost(ok(f"{fence}\n{{\"items\": []}}\n```"))
    assert LlmExtractor(transport=fake)("x") == {"items": []}


def test_illegal_json_is_extraction_error_not_silent_none():
    fake = FakePost(ok("我觉得应该这样写……"))
    with pytest.raises(ExtractionError, match="JSON"):
        LlmExtractor(transport=fake)("x")


def test_top_level_list_is_rejected():
    fake = FakePost(ok("[1,2]"))
    with pytest.raises(ExtractionError, match="不是对象"):
        LlmExtractor(transport=fake)("x")


def test_empty_source_text_never_costs_money():
    fake = FakePost(ok("{}"))
    with pytest.raises(ExtractionError, match="为空"):
        LlmExtractor(transport=fake)("   ")
    assert fake.calls == []


def test_error_body_raises_api_error_with_actionable_text():
    fake = FakePost({"error": {"message": "model not activated"}})
    with pytest.raises(ApiError, match="model not activated"):
        LlmExtractor(transport=fake)("x")


@pytest.mark.parametrize("code,keyword", [(401, "API Key"), (404, "端点")])
def test_http_errors_are_translated(monkeypatch, code, keyword):
    import urllib.error

    from homework_compass import llm_client as lc

    def boom(req, **kw):
        raise urllib.error.HTTPError(req.full_url, code, "no", {}, None)

    monkeypatch.setattr(lc.urllib.request, "urlopen", boom)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    with pytest.raises(ApiError, match=keyword):
        lc.post("https://example.invalid", {})


def test_missing_key_message_names_the_env_var(monkeypatch):
    from homework_compass import llm_client as lc
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(ApiError, match="DASHSCOPE_API_KEY"):
        lc.api_key()


def test_ocr_returns_stripped_text_and_sends_inline_image(tmp_path):
    from homework_compass.parsing.extract import ocr_to_text
    img = tmp_path / "board.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    fake = FakePost(ok("  1.数学：P12  \n"))
    assert ocr_to_text(img, transport=fake) == "1.数学：P12"
    _, payload = fake.calls[0]
    user = payload["messages"][1]["content"]
    assert user[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert payload["messages"][0]["content"].startswith("你是 OCR 转写器")
    assert payload["temperature"] == 0


def test_ocr_missing_file_never_costs_money(tmp_path):
    from homework_compass.parsing.extract import ocr_to_text
    fake = FakePost(ok("x"))
    with pytest.raises(ExtractionError, match="图片不存在"):
        ocr_to_text(tmp_path / "nope.png", transport=fake)
    assert fake.calls == []
