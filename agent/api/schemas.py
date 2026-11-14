"""请求/响应模型，与《前端接口文档》及 docs/api/Agent-API.md 对齐。"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ----- OCR -----
class OCRRecognizeRequest(BaseModel):
    image_data: str = Field(..., description="base64 编码的图片数据或图片 URL")
    subject: Optional[str] = Field("数学", description="学科")


class OCRRecognizeResponse(BaseModel):
    questions: List[Dict[str, Any]] = Field(..., description="与前端 scan-status 完成时的 questions 一致，含答案与 figureUrls")
    figure_urls: List[str] = Field(default_factory=list, description="整图中截取的插图链接列表，供请求端保存")


# ----- Content Generate -----
class ChildProfile(BaseModel):
    name: Optional[str] = "小明"
    age: Optional[int] = 8
    grade: Optional[str] = "三年级"
    interests: Optional[List[str]] = Field(default_factory=list)


class ContentGenerateRequest(BaseModel):
    assignment_id: Optional[str] = None
    child_profile: ChildProfile = Field(default_factory=ChildProfile)
    questions: List[Dict[str, Any]] = Field(...)
    subject: Optional[str] = "数学"


class ContentGenerateResponse(BaseModel):
    storyId: str
    title: str
    summary: str
    story: str
    questions: List[Dict[str, Any]]
    illustration_prompts: List[str] = Field(default_factory=list)
    estimated_reading_time: int = 0
    theme: str = ""
    solution_guide: Optional[Dict[str, Any]] = None


# ----- 漫画/插图生成 -----
# 仅 illustration_prompts、interests 为入参；style/line_art/panels_per_prompt/reference_image_url/provider 等均从 configs/content_generation.yaml 的 illustration 段读取
class IllustrateRequest(BaseModel):
    illustration_prompts: List[str] = Field(..., description="插图描述列表，可与 /content/generate 返回的 illustration_prompts 一致")
    interests: Optional[List[str]] = Field(default_factory=list, description="兴趣爱好列表，取其一生成兴趣相关人物角色并写入图片生成提示词，指定连环画角色")


class IllustrateItem(BaseModel):
    prompt: str = Field(..., description="最终用于绘图的英文 Prompt（可能经 LLM 优化）")
    raw_prompt: Optional[str] = None
    images: List[str] = Field(default_factory=list, description="图片 URL 或 data:image/png;base64,...")


class IllustrateResponse(BaseModel):
    items: List[IllustrateItem] = Field(..., description="按提示生成的图，每项含 prompt 与 images 列表")


# ----- Solution Guide -----
class SolutionGuideRequest(BaseModel):
    question: Dict[str, Any] = Field(...)
    child_profile: ChildProfile = Field(default_factory=ChildProfile)


class SolutionGuideResponse(BaseModel):
    theme: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    full_text: str = ""


# ----- Voice（个性化内容朗读）-----
class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., description="要朗读的文案，如故事正文、解题引导等个性化内容")
    voice: Optional[str] = Field("xiaoyun", description="发音人，如 xiaoyun 等儿童友好风格")
    format: Optional[str] = Field("mp3", description="输出格式：mp3 | wav")
    speech_rate: Optional[int] = Field(None, description="语速，-500～500，0 为默认，正数加快负数变慢")


class VoiceSynthesizeResponse(BaseModel):
    success: bool
    audio_data: Optional[str] = None  # base64
    format: Optional[str] = None
    error: Optional[str] = None
