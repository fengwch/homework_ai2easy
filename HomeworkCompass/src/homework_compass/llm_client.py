"""百炼 DashScope 传输层：鉴权、POST、错误翻译。

已知坑（实测踩过，写在这里省掉下一个人的半小时）：
- `response_format={"type":"json_object"}` 要求提示词里出现 "JSON" 字样，否则 400。
- 业务空间（workspace）维度的 key 形如 `sk-ws-...`，老域名可能不认，需要专属域名。
- 生图返回的 URL 24 小时失效。本版不生图，但接生图的那个 spec 必须立刻下载落盘。
- key 只从环境变量读：凭证一旦进 config.toml，就会被顺手提交。
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request

from homework_compass.errors import ApiError, ExtractionError

KEY_ENV = "DASHSCOPE_API_KEY"
COMPATIBLE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
NATIVE_BASE = "https://dashscope.aliyuncs.com"
_RETRYABLE = (429, 500, 502, 503)


def api_key() -> str:
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise ApiError(
            f"未设置环境变量 {KEY_ENV}。请 `export {KEY_ENV}=sk-xxx`"
            "（百炼控制台生成，通常 30+ 位）。凭证不要写进 config.toml。"
        )
    return key


def compatible_url(path: str) -> str:
    root = (os.environ.get("DASHSCOPE_BASE_URL") or COMPATIBLE_BASE).rstrip("/")
    return f"{root}/{path.lstrip('/')}"


def _ssl_context() -> ssl.SSLContext | None:
    """优先用 certifi 的根证书。

    CentOS 7 的 ca-certificates 太旧，缺 DashScope 证书链的根，urlopen 会直接
    抛 CERTIFICATE_VERIFY_FAILED。装了 certifi 就用它，没装就交给系统默认，
    不在代码里关校验——关掉等于把中间人攻击的门打开。
    """
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def post(url: str, payload: dict, *, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key()}"}
    ctx = _ssl_context()
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            if e.code in _RETRYABLE:
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise ApiError(
                    f"HTTP {e.code}（已自动重试一次仍失败）：{detail or '<空响应体>'}\n"
                    "限流或服务端抖动通常过一会儿就好；连续出现请稍后再试。"
                ) from e
            if e.code in (401, 403):
                raise ApiError(
                    f"HTTP {e.code} API Key 无效或被拒：{detail or '<空响应体>'}\n"
                    f"请确认 {KEY_ENV} 是完整 key（sk- 开头）、已开通该模型权限；"
                    "若 key 曾在对话/日志里明文出现过，请先在控制台轮换。"
                ) from e
            if e.code == 404:
                raise ApiError(
                    f"HTTP 404（端点或模型不可用）：{url} —— {detail or '<空响应体>'}\n"
                    "可能原因：模型不在此接入方式下、地域不对（国际站用 "
                    "dashscope-intl.aliyuncs.com）、或业务空间 Key 需改用专属域名。"
                ) from e
            if e.code == 400 and "json" in detail.lower():
                raise ApiError(
                    f"HTTP 400：{detail}\n提示：结构化输出要求提示词中出现 “JSON” 字样。"
                ) from e
            raise ApiError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise ApiError(f"网络错误：{e.reason}。请重试，或调大 timeout（当前 {timeout}s）。") from e
        except TimeoutError as e:
            raise ApiError(f"请求超时（{timeout}s）：请重试或调大 timeout。") from e
    raise ApiError("重试后仍失败：未收到可用的响应。")


def check_body_error(body: dict) -> None:
    """两种协议错误字段不同：兼容模式是 error{}，原生是顶层 code/message。"""
    if body.get("error"):
        raise ApiError(f"接口返回错误：{json.dumps(body['error'], ensure_ascii=False)}")
    if body.get("code"):
        raise ApiError(f"接口错误 {body['code']}: {body.get('message', '')}")


def chat(content: list[dict], model: str, *, system: str,
         response_format: dict | None = None, timeout: int = 120,
         transport=None) -> str:
    payload: dict = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": content}],
        "temperature": 0,      # 抄写型任务不需要创造性
    }
    if response_format:
        payload["response_format"] = response_format
    body = (transport or post)(compatible_url("chat/completions"), payload, timeout=timeout)
    check_body_error(body)
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ExtractionError(
            f"响应结构异常：{json.dumps(body, ensure_ascii=False)[:500]}") from e
