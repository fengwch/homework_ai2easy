"""
OCR 服务单元测试：使用本地图片 imgs/数学题目-1.jpg。
通过 mock 百度 OCR 接口，不依赖真实 API Key 即可验证预处理 + 题目解析流程。
"""
import pytest
from unittest.mock import patch, MagicMock

from ocr.service import OCRService


# 模拟百度 OCR 返回的文本（与 question_parser 规则匹配：题号 + 内容）
FAKE_OCR_TEXT = """1. 小明有 3 个苹果，吃了 1 个，还剩几个？
2. 计算 2 + 3 的结果。"""

# 测试用 OCR 配置，确保走百度引擎以便 mock _recognize_baidu
OCR_CONFIG_BAIDU = {"engine": "baidu", "question_parsing": {"use_llm": False, "subject_hint": "数学"}}


class TestOCRServiceWithLocalImage:
    """使用本地数学题目图片的 OCRService 单元测试。"""

    @pytest.fixture
    def ocr_service(self):
        return OCRService()

    @patch("ocr.service._recognize_baidu")
    @patch("ocr.service.extract_and_save_figures", return_value=[])
    @patch("ocr.service._load_config", return_value=OCR_CONFIG_BAIDU)
    def test_recognize_with_local_image_path(
        self, mock_config, mock_figures, mock_baidu: MagicMock, sample_image_path: str
    ):
        """传入本地图片路径，mock 百度 OCR，应返回与前端一致的 questions 结构。"""
        mock_baidu.return_value = (FAKE_OCR_TEXT, [])
        ocr_service = OCRService()
        result = ocr_service.recognize(image_data=sample_image_path, subject="数学")
        assert "questions" in result
        questions = result["questions"]
        assert isinstance(questions, list)
        assert len(questions) >= 1
        for q in questions:
            assert "id" in q
            assert "questionNumber" in q
            assert "questionType" in q
            assert "originalText" in q
            assert "structuredData" in q
            assert "knowledgePoints" in q
            assert "metadata" in q
        mock_baidu.assert_called_once()

    @patch("ocr.service._recognize_baidu")
    @patch("ocr.service.extract_and_save_figures", return_value=[])
    @patch("ocr.service._load_config", return_value=OCR_CONFIG_BAIDU)
    def test_recognize_with_base64_from_local_image(
        self, mock_config, mock_figures, mock_baidu: MagicMock, sample_image_base64: str
    ):
        """传入 base64（来自本地图片），应走同一套预处理与解析。"""
        mock_baidu.return_value = (FAKE_OCR_TEXT, [])
        ocr_service = OCRService()
        result = ocr_service.recognize(image_data=sample_image_base64, subject="数学")
        assert "questions" in result
        assert len(result["questions"]) >= 1
        mock_baidu.assert_called_once()

    @patch("ocr.service._recognize_baidu")
    @patch("ocr.service.extract_and_save_figures", return_value=[])
    @patch("ocr.service._load_config", return_value=OCR_CONFIG_BAIDU)
    def test_recognize_question_structure(
        self, mock_config, mock_figures, mock_baidu: MagicMock, sample_image_path: str
    ):
        """校验单道题包含前端需要的字段。"""
        mock_baidu.return_value = ("1. 某道题内容", [])
        ocr_service = OCRService()
        result = ocr_service.recognize(image_data=sample_image_path, subject="数学")
        q = result["questions"][0]
        assert q["id"] == "q1"
        assert q["questionNumber"] == 1
        assert q["originalText"]
        assert "stem" in q["structuredData"]
        assert isinstance(q["metadata"].get("wordCount"), (int, type(None))) or "wordCount" in q["metadata"]

    @patch("ocr.service._recognize_baidu")
    @patch("ocr.service.extract_and_save_figures", return_value=[])
    @patch("ocr.service._load_config", return_value=OCR_CONFIG_BAIDU)
    def test_answer_saved_and_removed_from_display(
        self, mock_config, mock_figures, mock_baidu: MagicMock, sample_image_path: str
    ):
        """题目中含答案时：标准答案写入 structuredData.answer，展示用 originalText 不包含答案。"""
        mock_baidu.return_value = ("1. 以下哪个正确？ A. 选项1 B. 选项2 答案：A", [])
        ocr_service = OCRService()
        result = ocr_service.recognize(image_data=sample_image_path, subject="数学")
        questions = result["questions"]
        assert len(questions) >= 1
        q = questions[0]
        assert q["structuredData"].get("answer") == "A"
        # 答题展示不应出现答案行（如 答案：A）
        assert "答案：A" not in q["originalText"]
        assert "答案:A" not in q["originalText"]

    @patch("ocr.service.extract_figures_for_questions")
    @patch("ocr.service._recognize_baidu")
    @patch("ocr.service._load_config", return_value=OCR_CONFIG_BAIDU)
    def test_figure_ref_and_line_index_when_ocr_has_boxes(
        self, mock_config, mock_baidu: MagicMock, mock_figures, sample_image_path: str
    ):
        """当百度 OCR 返回带 box 的 ocr_lines 时，解析出 hasImageRef、figureRefLineIndex，并调用按题截插图。"""
        def _fake_figures(img_array, ocr_lines_arg, questions_arg, run_id):
            return {"q1": [f"/uploads/ocr_figures/{run_id}/q1/0.png"]}
        mock_figures.side_effect = _fake_figures
        text = "1. 如图所示，求阴影部分面积。"
        ocr_lines = [
            {"text": "1. 如图所示，求阴影部分面积。", "box": (10, 20, 200, 30)},
        ]
        mock_baidu.return_value = (text, ocr_lines)
        ocr_service = OCRService()
        result = ocr_service.recognize(image_data=sample_image_path, subject="数学")
        questions = result["questions"]
        assert len(questions) >= 1
        q = questions[0]
        assert q["metadata"].get("hasImageRef") is True
        assert q["metadata"].get("figureRefLineIndex") is not None
        assert len(q["metadata"].get("figureUrls", [])) == 1
        assert q["metadata"]["figureUrls"][0].startswith("/uploads/ocr_figures/") and "q1/0.png" in q["metadata"]["figureUrls"][0]
        mock_figures.assert_called_once()
