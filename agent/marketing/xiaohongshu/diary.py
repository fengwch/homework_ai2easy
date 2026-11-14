"""运营日记：JSONL + 按日 Markdown 摘要。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def append_jsonl(record: Dict[str, Any], log_path: Optional[Path] = None) -> Path:
    path = log_path or project_root() / "marketing" / "logs" / "xhs_publish.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


def append_daily_markdown(
    record: Dict[str, Any],
    *,
    logs_dir: Optional[Path] = None,
) -> Path:
    """追加到 marketing/logs/YYYY-MM-DD.md（与 uploads/vedio/*/info.md 类似的复盘风格）。"""
    logs_dir = logs_dir or project_root() / "marketing" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    path = logs_dir / f"{day}.md"
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    block = f"""
---

## 记录 {ts}

- **主题**: {record.get("theme_id", "")}
- **账号**: {record.get("account_id", "default")}
- **标题**: {record.get("title", "")}
- **dry_run**: {record.get("dry_run", False)}
- **发布结果**: {json.dumps(record.get("publish_result"), ensure_ascii=False) if record.get("publish_result") is not None else "（未调用或仅文案）"}
- **素材**: {record.get("asset_summary", "")}
- **备注**: {record.get("note", "")}

"""
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)
    return path
