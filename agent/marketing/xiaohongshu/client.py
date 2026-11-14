"""小红书开放平台 HTTP 客户端：OAuth、common_controller 调用、可选发布。"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml

from marketing.xiaohongshu.sign import sign_request

METHOD_OAUTH_GET_TOKEN = "oauth.getAccessToken"
METHOD_OAUTH_REFRESH = "oauth.refreshToken"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_api_config(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or _project_root() / "config" / "xhs_api.yaml"
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class XiaohongshuClient:
    """dry_run=True 时不发起 HTTP 请求，仅返回拟发送内容。"""

    def __init__(
        self,
        *,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        dry_run: bool = False,
        api_config: Optional[Dict[str, Any]] = None,
        token_cache_path: Optional[Path] = None,
        session: Optional[requests.Session] = None,
    ):
        self.app_id = app_id or os.environ.get("XHS_APP_ID", "").strip()
        self.app_secret = app_secret or os.environ.get("XHS_APP_SECRET", "").strip()
        self.access_token = access_token or os.environ.get("XHS_ACCESS_TOKEN", "").strip() or None
        self.refresh_token = refresh_token or os.environ.get("XHS_REFRESH_TOKEN", "").strip() or None
        self.dry_run = dry_run
        self.api_config = api_config or load_api_config()
        self.token_cache_path = token_cache_path
        if self.token_cache_path is None:
            raw = os.environ.get("XHS_TOKEN_CACHE_PATH", "").strip()
            self.token_cache_path = Path(raw) if raw else _project_root() / "marketing" / "xiaohongshu" / ".token_cache.json"
        self.session = session or requests.Session()
        self._load_token_cache()

    def _load_token_cache(self) -> None:
        if not self.token_cache_path or not self.token_cache_path.is_file():
            return
        try:
            data = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
            self.access_token = self.access_token or data.get("accessToken")
            self.refresh_token = self.refresh_token or data.get("refreshToken")
        except (OSError, json.JSONDecodeError):
            pass

    def _save_token_cache(self, data: Dict[str, Any]) -> None:
        if self.dry_run:
            return
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _common_body(self, method: str, timestamp_ms: Optional[int] = None) -> Dict[str, Any]:
        ts = str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000))
        ver = "2.0"
        if not self.app_id or not self.app_secret:
            raise ValueError("缺少 XHS_APP_ID / XHS_APP_SECRET（或 .token_cache 仅用于读 token）")
        sig = sign_request(method, self.app_id, ts, ver, self.app_secret)
        return {
            "sign": sig,
            "appId": self.app_id,
            "timestamp": ts,
            "version": ver,
            "method": method,
        }

    def _url(self) -> str:
        base = self.api_config.get("base_url", "https://ark.xiaohongshu.com").rstrip("/")
        path = self.api_config.get("api_path", "/ark/open_api/v3/common_controller")
        return f"{base}{path}"

    def call_api(
        self,
        method: str,
        extra: Optional[Dict[str, Any]] = None,
        *,
        include_access_token: bool = True,
    ) -> Dict[str, Any]:
        body = self._common_body(method)
        if include_access_token and self.access_token:
            body["accessToken"] = self.access_token
        if extra:
            body.update(extra)
        if self.dry_run:
            return {"dry_run": True, "url": self._url(), "body": body}
        resp = self.session.post(self._url(), json=body, headers={"Content-Type": "application/json"}, timeout=60)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            return {"success": False, "error": str(e), "status_code": resp.status_code, "text": resp.text[:2000]}
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"success": False, "error": "invalid_json", "text": resp.text[:2000]}

    def oauth_get_access_token(self, code: str) -> Dict[str, Any]:
        extra = {"code": code}
        out = self.call_api(METHOD_OAUTH_GET_TOKEN, extra, include_access_token=False)
        if self.dry_run:
            return out
        if out.get("success") and out.get("data"):
            d = out["data"]
            self.access_token = d.get("accessToken")
            self.refresh_token = d.get("refreshToken")
            self._save_token_cache(
                {
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                    "accessTokenExpiresAt": d.get("accessTokenExpiresAt"),
                    "refreshTokenExpiresAt": d.get("refreshTokenExpiresAt"),
                }
            )
        return out

    def oauth_refresh_token(self) -> Dict[str, Any]:
        if not self.refresh_token:
            raise ValueError("缺少 refresh_token（XHS_REFRESH_TOKEN 或 token 缓存）")
        extra = {"refreshToken": self.refresh_token}
        out = self.call_api(METHOD_OAUTH_REFRESH, extra, include_access_token=False)
        if self.dry_run:
            return out
        if out.get("success") and out.get("data"):
            d = out["data"]
            self.access_token = d.get("accessToken")
            self.refresh_token = d.get("refreshToken")
            self._save_token_cache(
                {
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                    "accessTokenExpiresAt": d.get("accessTokenExpiresAt"),
                    "refreshTokenExpiresAt": d.get("refreshTokenExpiresAt"),
                }
            )
        return out

    def publish_note(
        self,
        title: str,
        content: str,
        image_paths: Optional[list] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """调用 config 中 publish_note.method；未配置则返回说明性错误。"""
        pn = (self.api_config.get("publish_note") or {})
        method = pn.get("method")
        if not pn.get("enabled") or not method:
            return {
                "success": False,
                "skipped": True,
                "reason": "config/xhs_api.yaml 中 publish_note 未启用或未配置 method，请按开放平台文档填写后重试",
            }
        merged = dict(pn.get("extra_params") or {})
        merged.update(extra_params or {})
        # 常见约定：标题、正文、图片 id 列表；实际字段名以官方为准
        merged.setdefault("title", title)
        merged.setdefault("content", content)
        if image_paths:
            merged.setdefault("local_image_paths", image_paths)
        return self.call_api(method, merged)

    def upload_image(self, file_path: Path) -> Dict[str, Any]:
        """若开放平台提供素材上传 method，在 xhs_api.yaml 的 upload_image 中配置后使用。"""
        ui = (self.api_config.get("upload_image") or {})
        method = ui.get("method")
        if not ui.get("enabled") or not method:
            return {
                "success": False,
                "skipped": True,
                "reason": "config/xhs_api.yaml 中 upload_image 未启用或未配置 method",
            }
        extra = dict(ui.get("extra_params") or {})
        extra.setdefault("file_path", str(file_path))
        return self.call_api(method, extra)
