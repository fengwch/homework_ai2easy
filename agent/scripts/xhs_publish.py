#!/usr/bin/env python3
"""从项目根目录运行小红书推广 CLI（便于 crontab）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketing.xiaohongshu.publish_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
