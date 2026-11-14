""" 
Agent HTTP API：供主后端调用的 OCR、内容生成、解题引导 接口。 
请求/响应与 docs/api/Agent-API.md 及《前端接口文档》数据契约对齐。 
"""
import asyncio
from pathlib import Path
from typing import Optional, List
import logging
import os
import shutil
# 在加载 .env 前抑制 dotenv 解析单行失败时的 stderr 警告
for _n in ("dotenv", "dotenv.main"):
    logging.getLogger(_n).setLevel(logging.ERROR)
from utils.env import safe_load_dotenv
safe_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from contextlib import asynccontextmanager 
import base64
import yaml 
 
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
 
from api.schemas import ( 
    OCRRecognizeRequest, 
    OCRRecognizeResponse, 
    ContentGenerateRequest, 
    ContentGenerateResponse, 
    SolutionGuideRequest, 
    SolutionGuideResponse, 
    VoiceSynthesizeRequest, 
    VoiceSynthesizeResponse, 
    IllustrateRequest, 
    IllustrateResponse, 
    IllustrateItem, 
) 
from pydantic import BaseModel
from tools.comic_panel_extractor import extract_comic_panels_by_borders, _image_input_to_bytes
from utils.logging import get_logger 
 
logger = get_logger(__name__) 
 
 
@asynccontextmanager 
async def lifespan(app: FastAPI): 
    logger.info("AI-Agent API 启动中") 
    yield 
    logger.info("AI-Agent API 即将关闭") 
 
 
app = FastAPI( 
    title="AI-Agent API", 
    description="OCR、个性化故事生成、解题引导等 AI 能力，供主后端或统一 API 调用", 
    version="1.0.0", 
    lifespan=lifespan, 
) 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OCR 截取的插图通过 /uploads/ocr_figures 访问，便于请求端保存或展示
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
if _uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.middleware("http")
async def log_requests(request, call_next):
    """记录每个 HTTP 请求的方法、路径与响应状态码，便于调试。"""
    import time
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": round(duration_ms)},
    )
    return response
 
 
@app.post("/ocr/recognize", response_model=OCRRecognizeResponse) 
async def ocr_recognize(body: OCRRecognizeRequest, request: Request): 
    """OCR 识别：返回与前端 scan-status 完成时一致的 questions。""" 
    logger.info("收到 OCR 请求", extra={"path": str(request.url.path), "subject": body.subject}) 
    try: 
        from ocr.service import OCRService 
        service = OCRService() 
        result = service.recognize( 
            image_data=body.image_data, 
            subject=body.subject or "数学", 
        ) 
        logger.debug("OCR 识别完成", extra={"questions_count": len(result.get("questions", []))}) 
        return OCRRecognizeResponse(
            questions=result["questions"],
            figure_urls=result.get("figure_urls") or [],
        ) 
    except ValueError as e: 
        logger.warning("OCR 请求参数错误", exc_info=e) 
        raise HTTPException(status_code=400, detail=str(e)) 
    except RuntimeError as e: 
        logger.error("OCR 后端服务错误", exc_info=e) 
        raise HTTPException(status_code=502, detail=str(e)) 
    except Exception as e: 
        logger.exception("OCR 未预期异常") 
        raise HTTPException(status_code=500, detail=str(e)) 
 
 
@app.post("/content/generate", response_model=ContentGenerateResponse) 
async def content_generate(body: ContentGenerateRequest, request: Request): 
    """内容生成：故事、插图提示、学习页题目列表。""" 
    logger.info( 
        "收到内容生成请求", 
        extra={"path": str(request.url.path), "subject": body.subject, "questions_count": len(body.questions)}, 
    ) 
    try: 
        from content_generation.story_generator.generator import generate_story 
        cp = body.child_profile 
        profile = { 
            "name": cp.name, 
            "age": cp.age, 
            "grade": cp.grade, 
            "interests": cp.interests or [], 
        } 
        result = generate_story( 
            child_profile=profile, 
            questions=body.questions, 
            subject=body.subject or "数学", 
            assignment_id=body.assignment_id, 
        ) 
        logger.debug("内容生成完成", extra={"story_id": result.get("storyId")}) 
        return ContentGenerateResponse( 
            storyId=result["storyId"], 
            title=result["title"], 
            summary=result["summary"], 
            story=result["story"], 
            questions=result["questions"], 
            illustration_prompts=result.get("illustration_prompts") or [], 
            estimated_reading_time=result.get("estimated_reading_time", 0), 
            theme=result.get("theme", ""), 
            solution_guide=result.get("solution_guide"), 
        ) 
    except Exception as e: 
        logger.exception("内容生成失败") 
        raise HTTPException(status_code=500, detail=str(e)) 
 
 
@app.post("/content/solution-guide", response_model=SolutionGuideResponse) 
async def content_solution_guide(body: SolutionGuideRequest, request: Request): 
    """解题引导：基于兴趣角色分步讲解。""" 
    logger.info("收到解题引导请求", extra={"path": str(request.url.path)}) 
    try: 
        from content_generation.solution_generator.generator import generate_solution_guide 
        cp = body.child_profile 
        profile = { 
            "name": cp.name, 
            "interests": cp.interests or [], 
        } 
        result = generate_solution_guide(question=body.question, child_profile=profile) 
        logger.debug("解题引导生成完成", extra={"steps": len(result.get("steps", []))}) 
        return SolutionGuideResponse( 
            theme=result["theme"], 
            steps=result.get("steps", []), 
            full_text=result.get("full_text", ""), 
        ) 
    except Exception as e: 
        logger.exception("解题引导失败") 
        raise HTTPException(status_code=500, detail=str(e)) 
 
 
@app.post("/voice/synthesize", response_model=VoiceSynthesizeResponse) 
async def voice_synthesize(body: VoiceSynthesizeRequest, request: Request): 
    """语音合成：将个性化内容文案（故事、解题引导等）朗读为语音，支持语速调节。""" 
    logger.info("收到语音合成请求", extra={"path": str(request.url.path), "format": body.format}) 
    try: 
        from voice_synthesis.aliyun_tts import synthesize 
        out = synthesize( 
            text=body.text, 
            voice=body.voice or "xiaoyun", 
            format=body.format or "mp3", 
            speech_rate=body.speech_rate, 
        ) 
        if out.get("success"): 
            audio_b64 = ( 
                base64.b64encode(out["audio_data"]).decode("utf-8") 
                if isinstance(out["audio_data"], bytes) 
                else out.get("audio_data", "") 
            ) 
            logger.debug("语音合成成功", extra={"format": out.get("format", "mp3")}) 
            return VoiceSynthesizeResponse(success=True, audio_data=audio_b64, format=out.get("format", "mp3")) 
        logger.warning("语音合成失败", extra={"error": out.get("error")}) 
        return VoiceSynthesizeResponse(success=False, error=out.get("error", "合成失败")) 
    except ImportError: 
        logger.warning("语音合成模块未安装") 
        return VoiceSynthesizeResponse(success=False, error="语音合成模块未实现或未配置") 
    except Exception as e: 
        logger.exception("语音合成异常") 
        return VoiceSynthesizeResponse(success=False, error=str(e)) 
 
 
def _get_illustrate_api_timeout() -> float:
    """从 configs/content_generation.yaml 读取插图接口整体超时（秒）。"""
    config_path = Path(__file__).resolve().parent.parent / "configs" / "content_generation.yaml"
    if not config_path.exists():
        return 360.0
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ill = data.get("illustration") or {}
        t = ill.get("api_timeout") or ill.get("ttapi_timeout", 300) + 60
        return max(60.0, float(t))
    except Exception:
        return 360.0


@app.post("/content/illustrate", response_model=IllustrateResponse)
async def content_illustrate(body: IllustrateRequest, request: Request):
    """漫画/插图生成：异步调用 TTAPI/Gemini，整体超时返回 504。style/line_art/panels/provider 等均从 configs/content_generation.yaml 读取。"""
    logger.info(
        "收到插图生成请求 path=%s prompts_count=%s interests=%s illustration_prompts=%s",
        str(request.url.path),
        len(body.illustration_prompts),
        body.interests or [],
        body.illustration_prompts,
    )
    try:
        from content_generation.illustration_gen.image_gen import generate_illustration_images_async

        timeout = _get_illustrate_api_timeout()
        logger.debug("插图生成：异步调用，整体超时 %.0fs", timeout)
        result = await asyncio.wait_for(
            generate_illustration_images_async(
                prompts=body.illustration_prompts,
                interests=body.interests or [],
            ),
            timeout=timeout,
        )
        logger.debug("插图生成：完成，items=%d", len(result))
        items = [
            IllustrateItem(prompt=item["prompt"], raw_prompt=item.get("raw_prompt"), images=item.get("images") or [])
            for item in result
        ]
        return IllustrateResponse(items=items)
    except asyncio.TimeoutError:
        logger.warning("插图生成整体超时（%.0fs）", _get_illustrate_api_timeout())
        raise HTTPException(status_code=504, detail="插图生成超时，请稍后重试或调大 configs/content_generation.yaml 中 illustration.api_timeout")
    except Exception as e:
        logger.exception("插图生成失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class ImgExtractorRequest(BaseModel):
    """漫画分格提取请求：支持 URL 或 base64。输出目录从 configs/content_generation.yaml 读取。"""

    image: str  # 图片 URL 或 base64（可含 data:image/...;base64, 前缀）
    max_panels: Optional[int] = None  # 期望最大分镜数量


class ImgExtractorResponse(BaseModel):
    success: bool
    panel_count: int
    panel_paths: List[str] = []
    output_dir: Optional[str] = None  # 实际保存 panels 的目录（绝对路径）
    error: Optional[str] = None


def _get_img_extractor_output_dir() -> str:
    """
    从 configs/content_generation.yaml 读取漫画分格输出目录。
    优先使用 illustration.img_extractor_output_dir；未配置时默认 'uploads/img_extractor'。
    """
    config_path = Path(__file__).resolve().parent.parent / "configs" / "content_generation.yaml"
    default_subdir = "uploads/img_extractor"
    if not config_path.exists():
        return default_subdir
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ill = data.get("illustration") or {}
        subdir = ill.get("img_extractor_output_dir") or default_subdir
        return subdir or default_subdir
    except Exception:
        return default_subdir


def _chown_recursive(path: Path, user: str = "www", group: str = "www") -> None:
    """
    递归修改目录及内部文件的属主/属组为指定用户（默认 www.www），并设置合理的访问权限。

    - 目录权限：rwxrwxr-x (0o775)，方便 www 组写入与遍历；
    - 文件权限：rw-rw-r-- (0o664)，方便 www 组写入，其他用户可读。

    在本地开发环境中若不存在该用户/组或 chmod 失败，则静默忽略错误。
    """
    try:
        shutil.chown(str(path), user=user, group=group)
        # 顶层路径权限
        if path.is_dir():
            try:
                path.chmod(0o775)
            except Exception:
                pass
        else:
            try:
                path.chmod(0o664)
            except Exception:
                pass
    except Exception:
        # 非生产环境可能不存在 www:www，忽略错误
        return

    if path.is_dir():
        for root, dirs, files in os.walk(path):
            for d in dirs:
                p = Path(root) / d
                try:
                    shutil.chown(str(p), user=user, group=group)
                    p.chmod(0o775)
                except Exception:
                    continue
            for f in files:
                p = Path(root) / f
                try:
                    shutil.chown(str(p), user=user, group=group)
                    p.chmod(0o664)
                except Exception:
                    continue


@app.post("/agent/img_extractor", response_model=ImgExtractorResponse)
async def img_extractor(body: ImgExtractorRequest, request: Request):
    """
    漫画分格提取：基于边框检测将一张漫画按实际分镜切成多张，并保存到配置指定目录。

    - 支持 image 为 URL 或 base64；
    - 输出目录从 configs/content_generation.yaml 的 illustration.img_extractor_output_dir 读取；
      若未配置，则默认 'uploads/img_extractor'；
    - 返回是否成功、分镜数量与实际保存的文件路径列表。
    """
    logger.info(
        "收到漫画分格请求", extra={"path": str(request.url.path), "max_panels": body.max_panels}
    )
    try:
        import time
        # 解析图片为字节
        raw_bytes = _image_input_to_bytes(body.image or "")

        # 写入临时源图（便于调试），并将结果输出到配置指定目录
        root = Path(__file__).resolve().parent.parent
        base_subdir = _get_img_extractor_output_dir()
        # 每次请求使用当前时间戳作为子目录，便于区分不同批次
        ts = int(time.time())
        # 若配置的是绝对路径（以 / 开头），则直接在该路径下创建子目录；
        # 否则视为相对项目根目录的子目录。
        if str(base_subdir).startswith("/"):
            subdir = f"{str(base_subdir).rstrip('/')}/{ts}"
            out_dir = Path(subdir).resolve()
        else:
            # subdir 为相对项目根目录的路径，如 'uploads/img_extractor/1731385600'
            subdir = f"{str(base_subdir).rstrip('/')}/{ts}"
            out_dir = (root / subdir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "漫画分格输出目录解析完成",
            extra={
                "base_subdir": str(base_subdir),
                "timestamp": ts,
                "subdir": str(subdir),
                "out_dir": str(out_dir),
            },
        )

        src_path = out_dir / "source.png"
        with open(src_path, "wb") as f:
            f.write(raw_bytes)

        panels = extract_comic_panels_by_borders(
            input_path=str(src_path),
            output_dir=str(out_dir),
            target_count=body.max_panels,
        )

        # 修改输出目录及内部文件的属主/属组为 www.www（若环境中存在该用户/组）
        _chown_recursive(out_dir, user="www", group="www")

        # 只返回实际生成的分镜相对路径列表（相对项目根目录，与 output_dir 同风格）
        panel_paths = []
        for p, _ in panels:
            p_path = Path(p)
            # 将绝对路径归一化为相对 root 的路径字符串
            try:
                rel = p_path.resolve().relative_to(root)
                panel_paths.append(str(rel))
            except Exception:
                # 兜底：若 relative_to 失败，则直接返回文件名
                panel_paths.append(p_path.name)
        logger.info(
            "漫画分格完成",
            extra={"panel_count": len(panel_paths), "output_dir": str(subdir), "timestamp": ts},
        )
        return ImgExtractorResponse(
            success=True,
            panel_count=len(panel_paths),
            panel_paths=panel_paths,
            # output_dir 对调用方仅暴露时间戳，目录前缀由配置控制
            output_dir=str(ts),
            error=None,
        )
    except Exception as e:
        logger.exception("漫画分格提取失败")
        return ImgExtractorResponse(
            success=False,
            panel_count=0,
            panel_paths=[],
            output_dir=None,
            error=str(e),
        )


@app.get("/health") 
async def health(): 
    return {"status": "ok"} 
