"""
阿里云 TTS 集成。
access_key_id、access_key_secret、AppKey 从环境变量读取；
发音人、音量、语速等默认值集中在一处。
超出单次请求字数限制时按配置拆分多批请求，并将各批音频流拼接后返回。
返回统一为 {success, audio_data|error, format}。
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from utils.logging import get_logger

logger = get_logger(__name__)

# 默认单次请求字数上限（阿里云建议 ≤300，可由 configs/tts_config.yaml 或环境变量覆盖）
DEFAULT_MAX_CHARS_PER_REQUEST = 300

# 默认发音与格式，集中在一处（与 .cursorrules 约定一致）
DEFAULT_VOICE_CONFIG = {
    "voice": "xiaoyun",
    "volume": 50,
    "speech_rate": 0,
    "pitch_rate": 0,
    "format": "mp3",
    "sample_rate": 16000,
}


def _load_tts_config() -> Dict[str, Any]:
    """从 configs/tts_config.yaml 读取 TTS 配置；环境变量 ALIYUN_TTS_MAX_CHARS_PER_REQUEST 可覆盖单次字数上限。"""
    config_path = Path(__file__).resolve().parent.parent / "configs" / "tts_config.yaml"
    data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("加载 TTS 配置失败: %s", e)
    max_chars = os.getenv("ALIYUN_TTS_MAX_CHARS_PER_REQUEST")
    if max_chars is not None:
        try:
            data["max_chars_per_request"] = int(max_chars)
        except ValueError:
            pass
    return data


def _get_max_chars_per_request() -> int:
    """获取单次 TTS 请求允许的最大字符数。"""
    cfg = _load_tts_config()
    v = cfg.get("max_chars_per_request", DEFAULT_MAX_CHARS_PER_REQUEST)
    try:
        return max(1, int(v))
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS_PER_REQUEST


def _split_text_for_tts(text: str, max_chars: int) -> List[str]:
    """
    将长文本按 max_chars 拆分为多段，优先在句末（。！？；\\n）处切分，避免截断语义。
    返回若干非空子串，每段长度不超过 max_chars。
    """
    if not text or max_chars <= 0:
        return []
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    # 句末分隔符（可扩展）
    sentence_end = re.compile(r"([。！？；\n]+)")
    segments: List[str] = []
    rest = text

    while rest:
        rest = rest.strip()
        if not rest:
            break
        if len(rest) <= max_chars:
            segments.append(rest)
            break
        # 在不超过 max_chars 的范围内找最后一个句末分隔符
        chunk = rest[:max_chars]
        last_split = -1
        for m in sentence_end.finditer(chunk):
            last_split = m.end()
        if last_split > 0:
            seg = rest[:last_split].strip()
            rest = rest[last_split:].strip()
        else:
            seg = rest[:max_chars]
            rest = rest[max_chars:]
        if seg:
            segments.append(seg)

    return [s for s in segments if s]


def check_tts_setup() -> Dict[str, Any]:
    """
    自检 TTS 环境：配置与 NLS SDK 是否就绪。
    返回 {ok, config_ready, nls_sdk_available, message}，便于测试或运维诊断。
    """
    access_key_id = os.getenv("ALIYUN_TTS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIYUN_TTS_ACCESS_KEY_SECRET")
    appkey = os.getenv("ALIYUN_TTS_APPKEY")
    config_ready = bool(access_key_id and access_key_secret and appkey)

    nls_sdk_available = False
    try:
        import nls  # noqa: F401
        nls_sdk_available = True
    except ImportError:
        pass

    acs_available = False
    if config_ready:
        try:
            from aliyunsdkcore.client import AcsClient  # noqa: F401
            acs_available = True
        except ImportError:
            pass

    ok = config_ready and nls_sdk_available and acs_available
    if ok:
        message = "TTS 环境就绪"
    elif not config_ready:
        message = "未配置 ALIYUN_TTS_ACCESS_KEY_ID、ALIYUN_TTS_ACCESS_KEY_SECRET 或 ALIYUN_TTS_APPKEY"
    elif not acs_available:
        message = "请安装 aliyun-python-sdk-core（pip install aliyun-python-sdk-core）"
    elif not nls_sdk_available:
        message = "请安装阿里云 NLS SDK（pip install aliyun-nls）"
    else:
        message = "TTS 环境异常"

    return {
        "ok": ok,
        "config_ready": config_ready,
        "nls_sdk_available": nls_sdk_available,
        "acs_available": acs_available,
        "message": message,
    }


def synthesize(
    text: str,
    voice: Optional[str] = None,
    format: Optional[str] = None,
    speech_rate: Optional[int] = None,
    voice_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    语音合成（支持个性化内容朗读）。返回 {success: True, audio_data: bytes, format: str} 或 {success: False, error: str}。
    speech_rate: -500～500，0 为默认，正数加快、负数变慢。
    """
    cfg = voice_config or {}
    voice = voice or cfg.get("voice", DEFAULT_VOICE_CONFIG["voice"])
    fmt = format or cfg.get("format", DEFAULT_VOICE_CONFIG["format"])
    rate = speech_rate if speech_rate is not None else cfg.get("speech_rate", DEFAULT_VOICE_CONFIG["speech_rate"])

    access_key_id = os.getenv("ALIYUN_TTS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIYUN_TTS_ACCESS_KEY_SECRET")
    appkey = os.getenv("ALIYUN_TTS_APPKEY")
    region = os.getenv("ALIYUN_TTS_REGION", "cn-shanghai")

    if not text:
        logger.warning("语音合成：文本为空")
        return {"success": False, "error": "文本为空", "format": fmt}
    if not access_key_id or not access_key_secret:
        logger.warning("语音合成：未配置 ALIYUN_TTS_ACCESS_KEY_ID/SECRET")
        return {"success": False, "error": "请设置环境变量 ALIYUN_TTS_ACCESS_KEY_ID 与 ALIYUN_TTS_ACCESS_KEY_SECRET", "format": fmt}
    if not appkey:
        logger.warning("语音合成：未配置 ALIYUN_TTS_APPKEY")
        return {"success": False, "error": "请设置环境变量 ALIYUN_TTS_APPKEY（智能语音交互控制台创建项目后获取）", "format": fmt}

    # 获取 Token：阿里云 NLS 需用 AK/SK 调用 token 接口
    token = _get_nls_token(access_key_id, access_key_secret, region)
    if not token:
        logger.error("语音合成：获取 NLS Token 失败")
        return {"success": False, "error": "获取阿里云 NLS Token 失败", "format": fmt}

    max_chars = _get_max_chars_per_request()
    segments = _split_text_for_tts(text, max_chars)
    if not segments:
        return {"success": False, "error": "文本分段后为空", "format": fmt}

    # 使用 NLS SDK 合成；若未安装 SDK 则返回说明
    try:
        if len(segments) == 1:
            return _synthesize_with_sdk(
                text=segments[0], voice=voice, fmt=fmt, speech_rate=rate,
                token=token, appkey=appkey, region=region,
            )
        # 多批：逐段合成并拼接音频流（PCM/MP3 直接拼接即可）
        audio_parts: List[bytes] = []
        for i, seg in enumerate(segments):
            out = _synthesize_with_sdk(
                text=seg, voice=voice, fmt=fmt, speech_rate=rate,
                token=token, appkey=appkey, region=region,
            )
            if not out.get("success"):
                logger.warning("语音合成第 %d/%d 段失败: %s", i + 1, len(segments), out.get("error"))
                return {"success": False, "error": out.get("error", "分段合成失败"), "format": fmt}
            audio_parts.append(out["audio_data"])
        combined = b"".join(audio_parts)
        logger.info("语音合成：长文本拆分为 %d 批，已拼接返回", len(segments))
        return {"success": True, "audio_data": combined, "format": fmt}
    except ImportError:
        logger.warning("语音合成：NLS SDK 未安装")
        return {
            "success": False,
            "error": "请安装阿里云 NLS Python SDK（从 https://github.com/aliyun/alibabacloud-nls-python-sdk 安装）",
            "format": fmt,
        }
    except Exception as e:
        logger.exception("语音合成异常")
        return {"success": False, "error": str(e), "format": fmt}


def _get_nls_token(access_key_id: str, access_key_secret: str, region: str) -> Optional[str]:
    """通过 AK/SK 获取 NLS 访问 Token。"""
    try:
        import json
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest

        client = AcsClient(access_key_id, access_key_secret, region)
        req = CommonRequest()
        req.set_domain("nls-meta.cn-shanghai.aliyuncs.com")
        req.set_version("2019-02-28")
        req.set_action_name("CreateToken")
        resp = client.do_action_with_exception(req)
        data = json.loads(resp.decode("utf-8"))
        return data.get("Token", {}).get("Id")
    except ImportError as e:
        logger.warning(
            "语音合成：未安装 aliyunsdkcore，无法获取 NLS Token。请执行 pip install aliyun-python-sdk-core",
            extra={"detail": str(e)},
        )
        return None
    except Exception as e:
        logger.warning("语音合成：获取 NLS Token 异常，请检查 AK/SK、网络或权限: %s", str(e), exc_info=True)
        return None


def _synthesize_with_sdk(
    text: str,
    voice: str,
    fmt: str,
    speech_rate: int,
    token: str,
    appkey: str,
    region: str,
) -> Dict[str, Any]:
    """使用 NLS Python SDK 进行语音合成（需安装 nls 包）。speech_rate -500～500。"""
    # 部分线上环境系统 CA 证书较旧，导致连接 wss://nls-gateway-*.aliyuncs.com
    # 时出现 CERTIFICATE_VERIFY_FAILED。这里优先让 Python 的 SSL 使用
    # certifi 提供的证书链，以提高兼容性。
    try:
        import certifi

        # 被 ssl.create_default_context / get_default_verify_paths 使用
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        # 若 certifi 不可用则退回系统默认 CA，具体错误由后续连接抛出
        pass

    try:
        import nls
    except ImportError:
        raise ImportError("请安装阿里云 NLS Python SDK")

    url = f"wss://nls-gateway-{region}.aliyuncs.com/ws/v1"
    audio_chunks = []

    def on_data(data, *args):
        if data:
            audio_chunks.append(data)

    def on_error(msg, *args):
        pass

    def on_close(*args):
        pass

    def on_metainfo(msg, *args):
        pass

    def on_completed(msg, *args):
        pass

    tts = nls.NlsSpeechSynthesizer(
        url=url,
        token=token,
        appkey=appkey,
        on_metainfo=on_metainfo,
        on_data=on_data,
        on_completed=on_completed,
        on_error=on_error,
        on_close=on_close,
    )
    aformat = "mp3" if fmt.lower() == "mp3" else "wav" if fmt.lower() == "wav" else "pcm"
    # 语速：NLS 部分版本支持 rate 参数，传入 speech_rate（-500～500）
    start_kwargs = {"voice": voice, "aformat": aformat}
    if speech_rate != 0:
        start_kwargs["rate"] = speech_rate
    tts.start(text, **start_kwargs)
    if not audio_chunks:
        return {"success": False, "error": "未收到音频数据", "format": fmt}
    audio_data = b"".join(audio_chunks)
    return {"success": True, "audio_data": audio_data, "format": fmt}


if __name__ == "__main__":
    """CLI 自检：python -m voice_synthesis.aliyun_tts"""
    from pathlib import Path
    from utils.env import safe_load_dotenv
    safe_load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    r = check_tts_setup()
    print("TTS 自检结果:")
    for k, v in r.items():
        print(f"  {k}: {v}")
