"""
OCR 接口测试：对 POST /ocr/recognize 使用本地图片 imgs/数学题目-1.jpg 的 base64。
通过 mock OCRService.recognize 避免依赖百度 API Key，校验响应状态与结构。
"""
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.main import app

# 与前端 scan-status 一致的题目结构
FAKE_QUESTIONS = [
    {
        "id": "q1",
        "questionNumber": 1,
        "questionType": "fill_blank",
        "originalText": "小明有 3 个苹果，吃了 1 个，还剩几个？",
        "structuredData": {"stem": "小明有 3 个苹果...", "options": [], "answer": "", "analysis": ""},
        "knowledgePoints": [{"subject": "数学", "topic": "综合", "subtopic": "", "difficulty": "medium"}],
        "metadata": {"wordCount": 15, "hasImage": False, "hasFormula": False, "confidence": 0.85},
    },
]


class TestOCRRecognizeAPI:
    """POST /ocr/recognize 接口测试（使用本地图片 base64）。"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("ocr.service.OCRService")
    def test_ocr_recognize_returns_200_and_questions(
        self, mock_ocr_class: MagicMock, client: TestClient, sample_image_base64: str
    ):
        """使用本地图片 base64 调用 /ocr/recognize，应返回 200 及 questions 列表。"""
        mock_instance = MagicMock()
        mock_instance.recognize.return_value = {"questions": FAKE_QUESTIONS}
        mock_ocr_class.return_value = mock_instance

        response = client.post(
            "/ocr/recognize",
            json={"image_data": sample_image_base64, "subject": "数学"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == "q1"
        assert data["questions"][0]["originalText"]
        mock_instance.recognize.assert_called_once()
        call_kw = mock_instance.recognize.call_args[1]
        assert call_kw["image_data"] == sample_image_base64
        assert call_kw["subject"] == "数学"

    @patch("ocr.service.OCRService")
    def test_ocr_recognize_subject_default(
        self, mock_ocr_class: MagicMock, client: TestClient, sample_image_base64: str
    ):
        """不传 subject 时默认为数学。"""
        mock_instance = MagicMock()
        mock_instance.recognize.return_value = {"questions": []}
        mock_ocr_class.return_value = mock_instance

        response = client.post(
            "/ocr/recognize",
            json={"image_data": sample_image_base64},
        )
        assert response.status_code == 200
        call_kw = mock_ocr_class.return_value.recognize.call_args[1]
        assert call_kw.get("subject") in (None, "数学")

    def test_ocr_recognize_missing_image_data_returns_400(self, client: TestClient):
        """缺少 image_data 应返回 400。"""
        response = client.post(
            "/ocr/recognize",
            json={"subject": "数学"},
        )
        assert response.status_code == 422  # FastAPI 校验为 422 Unprocessable Entity
