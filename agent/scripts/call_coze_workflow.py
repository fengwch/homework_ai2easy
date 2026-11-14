#!/usr/bin/env python3
"""
使用 Coze Python SDK 调用工作流异步接口，并轮询直到结束。

示例：
python scripts/call_coze_workflow.py \
  --token "$COZE_API_TOKEN" \
  --workflow-id "7613788373953953834" \
  --app-id "7613730010209878070" \
  --parameters-json '{"theme":"海底小纵队","subject":"数学"}'
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from cozepy import COZE_CN_BASE_URL, Coze, TokenAuth, WorkflowExecuteStatus

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / ".env").exists():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")


DEFAULT_PARAMETERS = {
    "character_name": "冯玉桥",
    "child_profile": {
        "age": "6",
        "grade": "男",
        "interests": "海底小纵队",
        "name": "冯玉桥",
    },
    "include_dialogue": True,
    "line_art": False,
    "mode": "1",
    "panels_in_image": "12",
    "panels_layout": "3x4",
    "panels_per_prompt": "3",
    "questions": "时针指向3，分针指向12，时间是（)",
    "style": "儿童漫画，卡通，2d, 连环画，活泼童趣氛围，可爱拟人化",
    "subject": "数学",
    "theme": "海底小纵队，勇士",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="调用 Coze 异步工作流并轮询结果")
    parser.add_argument(
        "--base-url",
        default=os.getenv("COZE_API_BASE_URL") or os.getenv("COZE_API_BASE") or COZE_CN_BASE_URL,
        help="Coze API 基础地址，默认 COZE_CN_BASE_URL",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("COZE_API_TOKEN"),
        help="Coze PAT（也可通过环境变量 COZE_API_TOKEN 提供）",
    )
    parser.add_argument(
        "--workflow-id",
        default=os.getenv("COZE_WORKFLOW_ID", "7613788373953953834"),
        help="工作流 ID",
    )
    parser.add_argument(
        "--app-id",
        default=os.getenv("COZE_APP_ID", "7613730010209878070"),
        help="应用 ID",
    )
    parser.add_argument(
        "--parameters-json",
        default=None,
        help="JSON 字符串形式的 parameters",
    )
    parser.add_argument(
        "--parameters-file",
        default=None,
        help="parameters 的 JSON 文件路径（优先级高于 --parameters-json）",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=420,
        help="最大等待时长（秒），默认 420（7 分钟）",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.5,
        help="轮询间隔秒数，默认 1.5",
    )
    return parser.parse_args()


def load_parameters(args: argparse.Namespace) -> dict[str, Any]:
    if args.parameters_file:
        with open(args.parameters_file, "r", encoding="utf-8") as f:
            return json.load(f)
    if args.parameters_json:
        return json.loads(args.parameters_json)
    return DEFAULT_PARAMETERS


def status_to_text(status: Any) -> str:
    value = getattr(status, "value", status)
    return str(value).upper()


def run_create_with_optional_app_id(coze: Coze, body: dict[str, Any], app_id: Optional[str]) -> Any:
    create_kwargs = {
        "workflow_id": body["workflow_id"],
        "parameters": body["parameters"],
        "is_async": True,
    }
    if app_id:
        create_kwargs["app_id"] = app_id
    try:
        return coze.workflows.runs.create(**create_kwargs)
    except TypeError:
        # 兼容不同版本 cozepy：有些版本 create 不支持 app_id 参数。
        create_kwargs.pop("app_id", None)
        return coze.workflows.runs.create(**create_kwargs)


def history_retrieve_with_optional_app_id(
    coze: Coze,
    workflow_id: str,
    execute_id: str,
    app_id: Optional[str],
) -> Any:
    retrieve_kwargs = {
        "workflow_id": workflow_id,
        "execute_id": execute_id,
    }
    if app_id:
        retrieve_kwargs["app_id"] = app_id
    try:
        return coze.workflows.runs.run_histories.retrieve(**retrieve_kwargs)
    except TypeError:
        retrieve_kwargs.pop("app_id", None)
        return coze.workflows.runs.run_histories.retrieve(**retrieve_kwargs)


def to_plain_data(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump()
        except Exception:
            pass
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            pass
    data = getattr(value, "__dict__", None)
    if isinstance(data, dict) and data:
        return data
    return str(value)


def parse_json_if_needed(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                return value
    return value


def extract_last_step_output(output: Any) -> Any:
    output = parse_json_if_needed(to_plain_data(output))
    if not isinstance(output, dict):
        return None

    # 常见结构：steps / nodes / node_results
    for key in ("steps", "nodes", "node_results"):
        items = output.get(key)
        if isinstance(items, list) and items:
            last_item = parse_json_if_needed(to_plain_data(items[-1]))
            if isinstance(last_item, dict):
                for out_key in ("output", "result", "data", "final_output"):
                    if out_key in last_item:
                        return parse_json_if_needed(last_item[out_key])
            return last_item

    # 兜底：某些工作流会直接有 final_output/result
    for key in ("final_output", "result", "data"):
        if key in output:
            return parse_json_if_needed(output[key])
    return None


def find_video_urls(data: Any) -> list[str]:
    results: list[str] = []

    def _walk(value: Any) -> None:
        value = parse_json_if_needed(to_plain_data(value))
        if isinstance(value, dict):
            for k, v in value.items():
                key_lower = str(k).lower()
                if key_lower in {"vedio_url", "video_url"}:
                    if isinstance(v, str) and v.strip():
                        results.append(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                results.append(item.strip())
                _walk(v)
        elif isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(data)
    # 去重并保持顺序
    uniq: list[str] = []
    seen = set()
    for url in results:
        if url not in seen:
            seen.add(url)
            uniq.append(url)
    return uniq


def _guess_video_ext(url: str, content_type: str = "") -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}:
        return suffix
    ctype = (content_type or "").lower()
    if "webm" in ctype:
        return ".webm"
    if "quicktime" in ctype:
        return ".mov"
    return ".mp4"


def download_videos_and_write_info(
    video_urls: list[str],
    args: argparse.Namespace,
    body: dict[str, Any],
    output_plain: Any,
    last_step_output: Any,
) -> None:
    timestamp_hour = datetime.now().strftime("%Y%m%d%H")
    target_dir = ROOT / "uploads" / "vedio" / timestamp_hour
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    failed_urls: list[str] = []

    for idx, url in enumerate(video_urls, 1):
        try:
            with urlopen(url, timeout=180) as resp:
                content_type = resp.headers.get("Content-Type", "")
                ext = _guess_video_ext(url, content_type)
                filename = f"video_{idx:02d}{ext}"
                file_path = target_dir / filename
                data = resp.read()
                file_path.write_bytes(data)
                saved_files.append(filename)
        except Exception:
            failed_urls.append(url)

    info_md = target_dir / "info.md"
    info_lines = [
        "# Coze 视频生成记录",
        "",
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 目录: `{target_dir}`",
        f"- 工作流ID: `{body.get('workflow_id')}`",
        f"- AppID: `{body.get('app_id')}`",
        f"- 已保存视频数量: {len(saved_files)}",
        f"- 下载失败数量: {len(failed_urls)}",
        "",
        "## 视频URL",
    ]
    for i, url in enumerate(video_urls, 1):
        info_lines.append(f"{i}. {url}")
    info_lines.extend(["", "## 已保存文件"])
    if saved_files:
        for name in saved_files:
            info_lines.append(f"- `{name}`")
    else:
        info_lines.append("- 无")

    if failed_urls:
        info_lines.extend(["", "## 下载失败URL"])
        for url in failed_urls:
            info_lines.append(f"- {url}")

    info_lines.extend(
        [
            "",
            "## 调用参数",
            "```json",
            json.dumps(body.get("parameters", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## 任务输出（output）",
            "```json",
            json.dumps(output_plain, ensure_ascii=False, indent=2)
            if isinstance(output_plain, (dict, list))
            else str(output_plain),
            "```",
            "",
            "## 最后一步输出",
            "```json",
            json.dumps(last_step_output, ensure_ascii=False, indent=2)
            if isinstance(last_step_output, (dict, list))
            else str(last_step_output),
            "```",
            "",
            "## 运行配置",
            f"- base_url: `{args.base_url}`",
            f"- max_wait_seconds: `{args.max_wait_seconds}`",
            f"- poll_interval: `{args.poll_interval}`",
        ]
    )

    info_md.write_text("\n".join(info_lines) + "\n", encoding="utf-8")
    print(f"视频已下载到: {target_dir}")
    print(f"参数记录文件: {info_md}")


def main() -> int:
    args = parse_args()
    if not args.token:
        print(
            "缺少 token，请通过 --token 或环境变量 COZE_API_TOKEN 提供。",
            file=sys.stderr,
        )
        return 1

    try:
        parameters = load_parameters(args)
    except Exception as exc:
        print(f"解析 parameters 失败: {exc}", file=sys.stderr)
        return 1

    body = {
        "workflow_id": args.workflow_id,
        "app_id": args.app_id,
        "parameters": parameters,
    }

    print("=== 请求信息 ===")
    print("SDK: cozepy")
    print("base_url:", args.base_url)
    print(
        "body:",
        json.dumps(
            {
                "workflow_id": body["workflow_id"],
                "app_id": body["app_id"],
                "parameters": body["parameters"],
            },
            ensure_ascii=False,
        ),
    )
    print(f"max_wait_seconds: {args.max_wait_seconds}, poll_interval: {args.poll_interval}s")

    try:
        coze = Coze(auth=TokenAuth(token=args.token), base_url=args.base_url)
        workflow_run = run_create_with_optional_app_id(coze=coze, body=body, app_id=args.app_id)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        return 1

    execute_id = getattr(workflow_run, "execute_id", None)
    if not execute_id:
        print(f"未拿到 execute_id，原始返回: {workflow_run}", file=sys.stderr)
        return 1

    print("已提交异步任务，execute_id:", execute_id)
    start = time.monotonic()

    while True:
        elapsed = time.monotonic() - start
        if elapsed > args.max_wait_seconds:
            print(f"超时：等待超过 {args.max_wait_seconds}s，任务仍未结束。", file=sys.stderr)
            return 1
        try:
            run_history = history_retrieve_with_optional_app_id(
                coze=coze,
                workflow_id=args.workflow_id,
                execute_id=execute_id,
                app_id=args.app_id,
            )
        except Exception as exc:
            print(f"轮询失败: {exc}", file=sys.stderr)
            return 1

        status_raw = getattr(run_history, "execute_status", None)
        status_text = status_to_text(status_raw)
        print(f"[{elapsed:6.1f}s] status={status_text}")

        if status_raw == WorkflowExecuteStatus.RUNNING or status_text in {"RUNNING", "IN_PROGRESS"}:
            time.sleep(args.poll_interval)
            continue

        if status_raw == WorkflowExecuteStatus.FAIL or status_text in {"FAIL", "FAILED", "ERROR"}:
            error_message = getattr(run_history, "error_message", "") or str(run_history)
            print("任务失败:", error_message, file=sys.stderr)
            return 1

        output = getattr(run_history, "output", None)
        print("任务完成，output:")
        output_plain = parse_json_if_needed(to_plain_data(output))
        if isinstance(output_plain, (dict, list)):
            print(json.dumps(output_plain, ensure_ascii=False, indent=2))
        else:
            print(output_plain)

        last_step_output = extract_last_step_output(output_plain)
        if last_step_output is not None:
            print("最后一步输出:")
            if isinstance(last_step_output, (dict, list)):
                print(json.dumps(last_step_output, ensure_ascii=False, indent=2))
            else:
                print(last_step_output)

        video_urls = find_video_urls(output_plain)
        if not video_urls and last_step_output is not None:
            video_urls = find_video_urls(last_step_output)
        if video_urls:
            print("=" * 18 + " VIDEO URL " + "=" * 18)
            for idx, url in enumerate(video_urls, 1):
                print(f"[{idx}] {url}")
            print("=" * 47)
            download_videos_and_write_info(
                video_urls=video_urls,
                args=args,
                body=body,
                output_plain=output_plain,
                last_step_output=last_step_output,
            )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
