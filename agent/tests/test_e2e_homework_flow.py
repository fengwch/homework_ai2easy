"""
端到端流程测试：一张作业图片 → OCR 识别 → 个性化故事生成 → 解题引导。
使用本地图片 imgs/数学题目-1.jpg，并输出每一步的详细内容。

运行方式（必须加 -s 才能看到所有步骤的详细输出）：
  pytest tests/test_e2e_homework_flow.py -v -s

环境说明：
- 配置 DASHSCOPE_API_KEY 后，步骤二、三会调用真实 Qwen 生成故事与解题引导。
- 配置 BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY 后，步骤一会对本地图片做真实 OCR；
  未配置时自动使用模拟题目数据，流程仍可跑通并输出完整内容。
"""
import json
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from api.main import app

# 当 OCR 未配置百度 Key 时使用的模拟题目，保证故事与解题引导仍可跑通
FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "q1",
        "questionNumber": 1,
        "questionType": "fill_blank",
        "originalText": "小明有 3 个苹果，吃了 1 个，还剩几个？",
        "structuredData": {
            "stem": "小明有 3 个苹果，吃了 1 个，还剩几个？",
            "options": [],
            "answer": "2 个",
            "analysis": "用总数减去吃掉的个数：3 - 1 = 2。",
        },
        "knowledgePoints": [{"subject": "数学", "topic": "减法", "subtopic": "10 以内减法", "difficulty": "easy"}],
        "metadata": {"wordCount": 15, "hasImage": False, "hasFormula": False, "confidence": 0.9},
    },
    {
        "id": "q2",
        "questionNumber": 2,
        "questionType": "calculation",
        "originalText": "计算 2 + 3 的结果。",
        "structuredData": {
            "stem": "计算 2 + 3 的结果。",
            "options": [],
            "answer": "5",
            "analysis": "2 加 3 等于 5。",
        },
        "knowledgePoints": [{"subject": "数学", "topic": "加法", "subtopic": "10 以内加法", "difficulty": "easy"}],
        "metadata": {"wordCount": 8, "hasImage": False, "hasFormula": False, "confidence": 0.9},
    },
]


def _print_section(title: str, data: Any, indent: str = "  "):
    """将步骤标题与内容格式化打印，便于查看。"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)
    print()


class TestE2EHomeworkFlow:
    """作业图片 → OCR → 故事生成 → 解题引导 全流程测试，并输出每步详细内容。"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def child_profile(self) -> Dict[str, Any]:
        return {
            "name": "小明",
            "age": 8,
            "grade": "三年级",
            "interests": ["小动物学习", "探险"],
        }

    def test_full_flow_ocr_story_solution_guide(
        self,
        client: TestClient,
        sample_image_base64: str,
        child_profile: Dict[str, Any],
    ):
        """
        完整流程：OCR 识别 → 个性化故事生成 → 解题引导。
        每步结果均打印详细内容。
        """
        # -------------------------------------------------------------------------
        # 步骤一：OCR 识别
        # -------------------------------------------------------------------------
        print("\n【步骤一】OCR 识别（作业图片 → 题目列表）")
        ocr_resp = client.post(
            "/ocr/recognize",
            json={"image_data": sample_image_base64, "subject": "数学"},
        )

        if ocr_resp.status_code == 200:
            ocr_data = ocr_resp.json()
            questions = ocr_data.get("questions", [])
            ocr_note = ""
            ocr_section = {"status_code": 200, "questions_count": len(questions), "questions": questions}
        else:
            questions = FALLBACK_QUESTIONS
            ocr_note = "（未成功，使用模拟题目继续后续步骤；请检查 .env 是否加载及 BAIDU_OCR_API_KEY、BAIDU_OCR_SECRET_KEY 是否同时配置）"
            try:
                err_body = ocr_resp.json()
            except Exception:
                err_body = ocr_resp.text
            ocr_section = {
                "status_code": ocr_resp.status_code,
                "error_detail": err_body,
                "questions_count": len(questions),
                "questions": questions,
            }
        _print_section("OCR 识别结果" + (" " + ocr_note if ocr_note else ""), ocr_section)

        # 额外单独打印 originalText，方便人工查看特殊符号（如 □、公式符号等）
        print("\n--- OCR originalText 明细 ---")
        for idx, q in enumerate(questions, 1):
            print(f"【题目 {idx} originalText】")
            print(q.get("originalText", ""))
            print("------")
        print("--- OCR originalText 明细结束 ---\n")

        assert isinstance(questions, list), "questions 应为列表"
        assert len(questions) >= 1, "至少应有一道题"

        # -------------------------------------------------------------------------
        # 步骤二：个性化故事生成
        # -------------------------------------------------------------------------
        print("\n【步骤二】个性化故事生成（题目 + 儿童档案 → 故事、插图提示等）")
        story_resp = client.post(
            "/content/generate",
            json={
                "assignment_id": "e2e-test-001",
                "child_profile": child_profile,
                "questions": questions,
                "subject": "数学",
            },
        )
        assert story_resp.status_code == 200, f"故事生成失败: {story_resp.status_code} {story_resp.text}"

        story_data = story_resp.json()
        _print_section("故事生成结果", {
            "storyId": story_data.get("storyId"),
            "title": story_data.get("title"),
            "summary": story_data.get("summary"),
            "story": story_data.get("story"),
            "theme": story_data.get("theme"),
            "estimated_reading_time": story_data.get("estimated_reading_time"),
            "illustration_prompts": story_data.get("illustration_prompts"),
            "questions_count": len(story_data.get("questions", [])),
        })

        # 打印故事正文单独一块，便于阅读
        print("\n--- 故事正文（原文） ---")
        print(story_data.get("story", ""))
        print("--- 故事正文结束 ---\n")

        # -------------------------------------------------------------------------
        # 步骤三：解题引导（对第一道题）
        # -------------------------------------------------------------------------
        first_question = questions[0]
        print("\n【步骤三】解题引导（针对第一道题 + 儿童档案 → 分步讲解）")
        guide_resp = client.post(
            "/content/solution-guide",
            json={
                "question": first_question,
                "child_profile": child_profile,
            },
        )
        assert guide_resp.status_code == 200, f"解题引导失败: {guide_resp.status_code} {guide_resp.text}"

        guide_data = guide_resp.json()
        _print_section("解题引导结果", {
            "theme": guide_data.get("theme"),
            "steps": guide_data.get("steps"),
            "full_text": guide_data.get("full_text"),
        })

        # 分步打印讲解内容
        print("\n--- 解题步骤（逐条） ---")
        for step in guide_data.get("steps", []):
            order = step.get("order", 0)
            text = step.get("text", "")
            print(f"  步骤 {order}：{text}")
        print("--- 解题步骤结束 ---\n")

        # 流程完整性断言
        assert story_data.get("storyId")
        assert story_data.get("story")
        assert len(guide_data.get("steps", [])) >= 1
