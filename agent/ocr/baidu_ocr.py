"""
百度 OCR 集成：先取 access_token 再调用识别接口。
APIKey、SecretKey 从环境变量 BAIDU_OCR_API_KEY、BAIDU_OCR_SECRET_KEY 读取。
"""
import base64
import json
import os
import urllib.request
import urllib.parse
from typing import List, Dict, Any


def _get_access_token() -> str:
    api_key = os.getenv("BAIDU_OCR_API_KEY")
    secret_key = os.getenv("BAIDU_OCR_SECRET_KEY")
    if not api_key or not secret_key:
        raise ValueError("请设置环境变量 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")
    url = (
        "https://aip.baidubce.com/oauth/2.0/token"
        "?grant_type=client_credentials"
        f"&client_id={urllib.parse.quote(api_key)}"
        f"&client_secret={urllib.parse.quote(secret_key)}"
    )
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"获取百度 access_token 失败: {data}")
    return token


def recognize(image_bytes: bytes, with_location: bool = False) -> Dict[str, Any]:
    """
    调用百度 OCR。with_location=True 时使用 general（含位置信息），否则用 general_basic。
    位置信息供插图截取时生成文字 mask，需在百度控制台开通「通用文字识别（含位置信息）」。
    """
    token = _get_access_token()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    path = "general" if with_location else "general_basic"
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{path}?access_token={token}"
    body = {
        "image": image_b64,
        "language_type": "CHN_ENG",
        "detect_direction": "true",
        "paragraph": "true",
        "probability": "true",
    }
    data = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode())
    if "error_code" in out and out["error_code"]:
        raise RuntimeError(f"百度 OCR 识别失败: {out.get('error_msg', out)}")
    return out


def words_result_to_text(result: Dict[str, Any]) -> str:
    """从百度 OCR 返回的 words_result 拼接为全文。"""
    lines = []
    for item in result.get("words_result") or []:
        lines.append(item.get("words", ""))
    return "\n".join(lines)


def words_result_to_ocr_lines(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从百度 OCR 返回的 words_result 解析为带位置的行列表，供插图截取时生成文字 mask。
    每项为 {"text": str, "box": (x, y, w, h)}，box 为 left, top, width, height。
    若某行无 location（如部分接口不返回位置），则 box 为 None。
    """
    lines = []
    for item in result.get("words_result") or []:
        text = item.get("words", "")
        loc = item.get("location")
        if loc and isinstance(loc, dict):
            x = int(loc.get("left", 0))
            y = int(loc.get("top", 0))
            w = int(loc.get("width", 0))
            h = int(loc.get("height", 0))
            lines.append({"text": text, "box": (x, y, w, h)})
        else:
            lines.append({"text": text, "box": None})
    return lines
