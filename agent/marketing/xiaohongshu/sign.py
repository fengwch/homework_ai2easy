"""小红书开放平台 common_controller 签名（与官方文档一致）。参见 marketing/XHS_OPEN_PLATFORM.md。"""

from __future__ import annotations

import hashlib


def sign_request(method: str, app_id: str, timestamp: str, version: str, app_secret: str) -> str:
    raw = f"{method}?appId={app_id}&timestamp={timestamp}&version={version}{app_secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
