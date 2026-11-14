"""
漫画/插图生成接口测试：POST /content/illustrate。
接口使用异步 generate_illustration_images_async，超时返回 504。
"""
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api.main import app


class TestIllustrateAPI:
    """POST /content/illustrate 接口测试。"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("content_generation.illustration_gen.image_gen.generate_illustration_images_async", new_callable=AsyncMock)
    def test_illustrate_returns_200_and_items(self, mock_gen: AsyncMock, client: TestClient):
        """调用 /content/illustrate 应返回 200 及 items 列表；仅传 illustration_prompts 与 interests。"""
        mock_gen.return_value = [
            {"prompt": "A child and a robot in the forest", "raw_prompt": "小明和机器人在森林", "images": []},
        ]
        response = client.post(
            "/content/illustrate",
            json={
                "illustration_prompts": ["小明和机器人在森林"],
                "interests": ["奥特曼"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["prompt"]
        assert "images" in data["items"][0]
        mock_gen.assert_called_once()
        call_kw = mock_gen.call_args[1]
        assert call_kw["prompts"] == ["小明和机器人在森林"]
        assert call_kw["interests"] == ["奥特曼"]
        # style/panels/provider 等由配置读取，接口不传入
        assert call_kw["style"] is None
        assert call_kw["panels_per_prompt"] is None
        assert call_kw["provider"] is None

    @patch("content_generation.illustration_gen.image_gen.generate_illustration_images_async", new_callable=AsyncMock)
    def test_illustrate_default_params(self, mock_gen: AsyncMock, client: TestClient):
        """仅传 illustration_prompts 时，interests 默认空列表；其余从配置读取。"""
        mock_gen.return_value = [{"prompt": "p", "raw_prompt": "原始", "images": []}]
        response = client.post(
            "/content/illustrate",
            json={"illustration_prompts": ["一段描述"]},
        )
        assert response.status_code == 200
        assert response.json()["items"]
        call_kw = mock_gen.call_args[1]
        assert call_kw["prompts"] == ["一段描述"]
        assert call_kw["interests"] == []
        assert call_kw["provider"] is None

    @patch("content_generation.illustration_gen.image_gen.generate_illustration_images_async", new_callable=AsyncMock)
    def test_illustrate_timeout_returns_504(self, mock_gen: AsyncMock, client: TestClient):
        """整体超时时返回 504。"""
        import asyncio
        mock_gen.side_effect = asyncio.TimeoutError()
        response = client.post(
            "/content/illustrate",
            json={"illustration_prompts": ["测试"]},
        )
        assert response.status_code == 504
        assert "超时" in response.json().get("detail", "")
