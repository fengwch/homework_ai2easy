#!/usr/bin/env python3
"""小红书软文：组装文案、写运营日记；默认通过 xiaohongshu-mcp 自动发布。--execute 仅用于遗留的开放平台 client。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional
from urllib import error, request

from utils.env import safe_load_dotenv

from marketing.xiaohongshu.client import XiaohongshuClient
from marketing.xiaohongshu.composer import compose_note
from marketing.xiaohongshu.diary import append_daily_markdown, append_jsonl
from marketing.xiaohongshu.theme import load_campaign


def _root() -> Path:
    return Path(__file__).resolve().parents[2]

def _to_mcp_image_path(path: str, imgs_root: Path) -> str:
    """将本地素材路径映射到 xiaohongshu-mcp 容器内路径。"""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (_root() / p).resolve()
    else:
        p = p.resolve()

    try:
        rel = p.relative_to(imgs_root.resolve())
    except ValueError:
        # 不在 imgs 目录下时保留原路径，便于排查
        return str(p)
    return f"/app/images/{rel.as_posix()}"


def _collect_steps_images(root: Path) -> list[str]:
    """小程序步骤截图：imgs/steps 下的图片列表。"""
    steps_dir = root / "imgs" / "steps"
    paths: list[str] = []
    if steps_dir.is_dir():
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for p in sorted(steps_dir.glob(ext)):
                paths.append(str(p))
    return paths


def _read_info_md_text(video_dir: Path) -> str:
    info_file = video_dir / "info.md"
    if not info_file.exists():
        return ""
    try:
        return info_file.read_text(encoding="utf-8")
    except Exception:
        return ""


# info.md 中流水线/技术元数据：不应出现在小红书正文
_INFO_POST_SKIP_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"视频已成功|已保存为|保存为\s*`?video_|`video_\d+\.mp4`", re.I),
    re.compile(r"video_\d+\.mp4|\.mp4\s*$", re.I),
    re.compile(r"无下载失败|下载失败|下载成功|已保存视频数量|下载失败数量", re.I),
    re.compile(r"^\s*时间\s*[:：]", re.I),
    re.compile(r"^\s*目录\s*[:：]", re.I),
    re.compile(r"工作流\s*ID|^\s*工作流", re.I),
    re.compile(r"\bAppID\b|应用\s*ID", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"coze-dianbo|X-Tos-|volces\.com", re.I),
    re.compile(r"运行配置|base_url|max_wait_seconds|poll_interval", re.I),
    re.compile(r"视频URL|已保存文件|调用参数|任务输出|最后一步输出", re.I),
    re.compile(r"node_status|node_execute_uuid|sub_video_url", re.I),
)


def _should_skip_info_line_for_post(line: str) -> bool:
    """非教学内容行（生成状态、路径、ID、链接等）→ 不用于推文。"""
    t = line.strip()
    if not t:
        return True
    for rx in _INFO_POST_SKIP_RES:
        if rx.search(t):
            return True
    return False


def _extract_json_string_field(info_text: str, key: str) -> str:
    """从 info.md 全文里宽松提取 JSON 字符串字段（题目/学科/主题等）。"""
    pat = re.compile(
        rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"',
        re.DOTALL,
    )
    m = pat.search(info_text)
    if not m:
        return ""
    return (
        m.group(1)
        .replace("\\n", "\n")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
        .strip()
    )


def _extract_teaching_snippets_from_info_md(info_text: str) -> str:
    """从调用参数等 JSON 中抽取与教学相关的短句，补充到推文素材。"""
    parts: list[str] = []
    q = _extract_json_string_field(info_text, "questions")
    if q:
        parts.append(f"本期题目：{q}")
    subj = _extract_json_string_field(info_text, "subject")
    if subj:
        parts.append(f"学科：{subj}")
    theme = _extract_json_string_field(info_text, "theme")
    if theme:
        parts.append(f"故事主题：{theme}")
    # 输出剧情为纯教学叙事，可摘要一行（截断避免过长）
    story = _extract_json_string_field(info_text, "输出剧情")
    if story:
        one = story.replace("\n", " ").strip()
        if len(one) > 220:
            one = one[:217] + "…"
        parts.append(f"剧情摘要：{one}")
    return "\n".join(parts)


def _filter_info_md_for_post(info_text: str) -> str:
    """去掉 Markdown 中的代码块与流水线行，只保留可能面向家长的说明句。"""
    if not info_text.strip():
        return ""
    lines_out: list[str] = []
    in_fence = False
    for raw in info_text.splitlines():
        t = raw.strip()
        if t.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if t.startswith("#"):
            continue
        t = t.lstrip("- ").strip()
        if not t:
            continue
        if _should_skip_info_line_for_post(t):
            continue
        lines_out.append(t)
    base = "\n".join(lines_out).strip()
    extra = _extract_teaching_snippets_from_info_md(info_text)
    if extra and extra not in base:
        if base:
            return f"{base}\n\n{extra}".strip()
        return extra
    return base


def _extract_info_highlights(info_text: str, max_lines: int = 8) -> str:
    """从 info.md 提取可直接放到文案里的关键信息（不含流水线/技术元数据）。"""
    filtered = _filter_info_md_for_post(info_text)
    if not filtered:
        return ""
    lines = []
    for raw in filtered.splitlines():
        t = raw.strip()
        if not t:
            continue
        lines.append(t)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


def _llm_polish_video_info(info_text: str) -> str:
    """可选：用 LLM 把与教学相关的 info 摘要整理成短文案（不含流水线/技术元数据）。"""
    filtered = _filter_info_md_for_post(info_text)
    if not filtered.strip():
        return ""
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage
    except ImportError:
        return ""
    if not os.environ.get("DASHSCOPE_API_KEY"):
        return ""
    model_name = os.environ.get("MODEL_NAME", "qwen-turbo")
    model = ChatTongyi(model=model_name)
    prompt = (
        "请仅根据下面与**本期视频教学内容**相关的材料，整理为 3-5 行中文小红书视频说明。"
        "语气自然，不夸大，不承诺效果。\n"
        "禁止输出或改写：文件路径、文件名（如 video_01.mp4）、下载成功/失败、"
        "工作流/AppID、网址链接、生成任务状态等技术性表述。\n\n"
        f"{filtered}"
    )
    try:
        out = model.invoke([HumanMessage(content=prompt)])
        text = getattr(out, "content", None) or str(out)
        return text.strip()
    except Exception:
        return ""


def _rule_optimize_xhs_content(body: str, hashtags: str, mode: str) -> str:
    """无 LLM 时的规则增强：结构清晰、带互动引导、保留合规提示。"""
    body = (body or "").strip()
    hashtags = (hashtags or "").strip()
    mode_hint = "小程序实操" if mode == "miniprogram" else "每日视频打卡"
    cta = (
        f"\n\n如果你也在做「{mode_hint}」，欢迎在评论区告诉我你家孩子最近最喜欢的主题，"
        "我按这个思路继续更新。"
    )
    # 避免重复追加
    if "评论区" in body:
        cta = ""
    return f"{body}{cta}\n\n{hashtags}".strip()


def _llm_optimize_xhs_content(title: str, content: str, mode: str) -> str:
    """可选：使用 LLM 再润色成更适合小红书推流的表达。"""
    if not content.strip():
        return content
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage
    except ImportError:
        return content
    if not os.environ.get("DASHSCOPE_API_KEY"):
        return content

    model_name = os.environ.get("MODEL_NAME", "qwen-turbo")
    model = ChatTongyi(model=model_name)
    prompt = (
        "你是小红书运营编辑。请将以下文案润色为更适合小红书推荐流分发的内容，要求：\n"
        "1) 保持原意，不夸大，不做疗效/提分承诺；\n"
        "2) 语气自然，分段清晰，有轻互动引导；\n"
        "3) 保留已有标签，不新增敏感表述；\n"
        "4) 控制在 350-700 字。\n\n"
        f"模式：{mode}\n标题：{title}\n\n原文：\n{content}"
    )
    try:
        out = model.invoke([HumanMessage(content=prompt)])
        text = getattr(out, "content", None) or str(out)
        polished = text.strip()
        return polished or content
    except Exception:
        return content


def _build_miniprogram_context(
    campaign: dict,
    note: dict,
    steps_images: list[str],
    mcp_image_paths: list[str],
) -> str:
    """聚合小程序模式可用于 LLM 改写的上下文信息。"""
    theme_ctx = note.get("theme_context") or {}
    context = {
        "product_name": campaign.get("product_name", "作业辅导AI助手"),
        "one_liner": campaign.get("one_liner", ""),
        "theme_id": campaign.get("theme_id", ""),
        "angle": campaign.get("angle", ""),
        "sample_interest": theme_ctx.get("sample_interest", ""),
        "sample_subject": theme_ctx.get("sample_subject", ""),
        "cover_count": len(note.get("assets", {}).get("cover_candidates") or []),
        "story_image_count": len(note.get("assets", {}).get("story_images") or []),
        "steps_count": len(steps_images),
        "steps_examples": steps_images[:3],
        "mcp_image_examples": mcp_image_paths[:5],
    }
    return json.dumps(context, ensure_ascii=False)


def _llm_optimize_miniprogram_content(title: str, content: str, context_json: str) -> str:
    """小程序模式专用：结合结构化上下文做小红书推文改写。"""
    if not content.strip():
        return content
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage
    except ImportError:
        return content
    if not os.environ.get("DASHSCOPE_API_KEY"):
        return content
    model_name = os.environ.get("MODEL_NAME", "qwen-turbo")
    model = ChatTongyi(model=model_name)
    prompt = (
        "你是小红书母婴/教育方向运营编辑。请根据给定上下文，把文案改写成适合推荐流分发的图文推文：\n"
        "1) 首段3行内抓住家长痛点；\n"
        "2) 明确“微信小程序：作业辅导AI助手”的使用场景和价值；\n"
        "3) 给出轻量步骤感知（结合 steps 图片信息）；\n"
        "4) 结尾带自然互动引导；\n"
        "5) 不夸大、不承诺提分，保留标签。\n\n"
        f"上下文信息(JSON)：{context_json}\n\n"
        f"标题：{title}\n\n原文：\n{content}"
    )
    try:
        out = model.invoke([HumanMessage(content=prompt)])
        text = getattr(out, "content", None) or str(out)
        polished = text.strip()
        return polished or content
    except Exception:
        return content


def _publish_via_mcp(
    *,
    title: str,
    content: str,
    image_paths: list[str],
    tags: list[str],
    endpoint: str,
    timeout_seconds: int = 120,
) -> dict:
    payload = {
        "title": title,
        "content": content,
        "images": image_paths,
        "tags": tags,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            return {
                "success": True,
                "endpoint": endpoint,
                "http_status": resp.status,
                "response": parsed,
                "payload": payload,
            }
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {"raw": raw}
        except Exception:
            parsed = {"raw": raw}
        return {
            "success": False,
            "endpoint": endpoint,
            "http_status": e.code,
            "error": str(e),
            "response": parsed,
            "payload": payload,
        }
    except Exception as e:
        return {
            "success": False,
            "endpoint": endpoint,
            "error": str(e),
            "payload": payload,
        }


def _publish_video_via_mcp(
    *,
    title: str,
    content: str,
    video_path: str,
    tags: list[str],
    endpoint: str,
    timeout_seconds: int = 300,
) -> dict:
    payload = {
        "title": title,
        "content": content,
        "video": video_path,
        "tags": tags,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            return {
                "success": True,
                "endpoint": endpoint,
                "http_status": resp.status,
                "response": parsed,
                "payload": payload,
            }
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {"raw": raw}
        except Exception:
            parsed = {"raw": raw}
        return {
            "success": False,
            "endpoint": endpoint,
            "http_status": e.code,
            "error": str(e),
            "response": parsed,
            "payload": payload,
        }
    except Exception as e:
        return {
            "success": False,
            "endpoint": endpoint,
            "error": str(e),
            "payload": payload,
        }


def main(argv: Optional[list] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    safe_load_dotenv(_root() / ".env")

    p = argparse.ArgumentParser(
        description="小红书推广：默认生成后通过 xiaohongshu-mcp 发布；--execute 仅对接遗留开放平台 client"
    )
    p.add_argument("--execute", action="store_true", help="真实请求开放平台 common_controller（非 MCP；默认仅组装文案并写日记）")
    p.add_argument("--use-llm", action="store_true", help="尝试使用 ChatTongyi 润色正文")
    p.add_argument("--refresh-token", action="store_true", help="调用 oauth.refreshToken（需 XHS_REFRESH_TOKEN）")
    p.add_argument("--oauth-code", type=str, default="", help="用授权码换取 access_token（写入 token 缓存）")
    p.add_argument("--campaign", type=Path, default=None, help="覆盖默认 config/xhs_campaign.yaml")
    p.add_argument("--account-id", type=str, default="default", help="日记中的账号标识")
    p.add_argument(
        "--mode",
        type=str,
        choices=["miniprogram", "daily-video"],
        default="miniprogram",
        help="内容模式：小程序介绍(miniprogram) 或 定期每日发视频(daily-video)",
    )
    p.add_argument(
        "--mcp-publish",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否在生成后调用 xiaohongshu-mcp 发布图文（默认开启；可用 --no-mcp-publish 关闭）",
    )
    p.add_argument(
        "--mcp-endpoint",
        type=str,
        default=os.environ.get("XHS_MCP_PUBLISH_ENDPOINT", "http://127.0.0.1:18060/api/v1/publish"),
        help="xiaohongshu-mcp 图文发布接口地址",
    )
    args = p.parse_args(argv)

    campaign = load_campaign(args.campaign)
    note = compose_note(args.campaign, use_llm=args.use_llm)

    if not note["compliance_ok"]:
        print("合规警告：命中禁用词 →", note["compliance_hits"], file=sys.stderr)

    title = note["title"]
    body = note["body"]
    hashtags = note["hashtags"]
    print("\n--- 素材 ---")
    print("封面候选:", note["assets"].get("cover_candidates"))
    print("故事插图:", note["assets"].get("story_images"))
    cover = (note["assets"].get("cover_candidates") or [None])[0]
    story = note["assets"].get("story_images") or []
    local_image_paths = [x for x in ([cover] if cover else []) + story if x]
    imgs_root = (_root() / "imgs").resolve()
    # 小程序介绍模式：追加步骤截图
    steps_images: list[str] = []
    if args.mode == "miniprogram":
        steps_images = _collect_steps_images(_root())
        local_image_paths.extend(steps_images)
    mcp_image_paths = [_to_mcp_image_path(x, imgs_root) for x in local_image_paths]
    print("MCP可用图片路径:", mcp_image_paths)
    if steps_images:
        print("小程序步骤图:", steps_images)

    dry_run = not args.execute
    publish_result: dict = {"mode": "compose_only", "execute": False}
    video_info: dict | None = None
    final_content = _rule_optimize_xhs_content(body, hashtags, args.mode)
    # miniprogram 模式默认尝试 LLM；若环境不满足会自动回退规则文案
    llm_enabled = args.use_llm or args.mode == "miniprogram"
    if llm_enabled:
        if args.mode == "miniprogram":
            mp_context = _build_miniprogram_context(campaign, note, steps_images, mcp_image_paths)
            final_content = _llm_optimize_miniprogram_content(title, final_content, mp_context)
        else:
            final_content = _llm_optimize_xhs_content(title, final_content, args.mode)
    print("\n--- 推流文案 ---")
    print(f"{title}\n\n{final_content}")

    if args.oauth_code.strip():
        client = XiaohongshuClient(dry_run=dry_run)
        publish_result = client.oauth_get_access_token(args.oauth_code.strip())
        print("\n--- OAuth ---\n", publish_result)

    elif args.refresh_token:
        client = XiaohongshuClient(dry_run=dry_run)
        try:
            publish_result = client.oauth_refresh_token()
        except ValueError as e:
            publish_result = {"success": False, "error": str(e)}
        print("\n--- Refresh ---\n", publish_result)

    elif args.execute:
        try:
            client = XiaohongshuClient(dry_run=False)
            if client.refresh_token:
                try:
                    client.oauth_refresh_token()
                except Exception:
                    pass
            publish_result = client.publish_note(
                title=title,
                content=final_content,
                image_paths=local_image_paths,
            )
            print("\n--- Publish ---\n", publish_result)
        except ValueError as e:
            publish_result = {"success": False, "error": str(e)}
            print("\n--- Publish 未执行 ---\n", publish_result, file=sys.stderr)
    elif args.mcp_publish:
        tags = [x.lstrip("#").strip() for x in hashtags.split() if x.strip()]
        if args.mode == "daily-video":
            videos_root = _root() / "uploads" / "vedio"
            latest_dir = None
            if videos_root.is_dir():
                subdirs = sorted(d for d in videos_root.iterdir() if d.is_dir())
                if subdirs:
                    latest_dir = subdirs[-1]
            if latest_dir is None:
                publish_result = {
                    "success": False,
                    "error": f"未找到视频目录：{videos_root}",
                }
                print("\n--- MCP Video Publish 未执行 ---\n", publish_result, file=sys.stderr)
            else:
                videos = sorted(latest_dir.glob("video_*.mp4"))
                if not videos:
                    publish_result = {
                        "success": False,
                        "error": f"目录中未找到视频文件：{latest_dir}",
                    }
                    print("\n--- MCP Video Publish 未执行 ---\n", publish_result, file=sys.stderr)
                else:
                    # 目录名直接作为 /app/videos 的子目录名
                    rel = latest_dir.name + "/" + videos[0].name
                    mcp_video_path = f"/app/videos/{rel}"
                    info_text = _read_info_md_text(latest_dir)
                    info_highlights = _extract_info_highlights(info_text)
                    llm_info = _llm_polish_video_info(info_text) if args.use_llm else ""
                    info_for_post = llm_info or info_highlights
                    if info_for_post:
                        content_with_video_info = (
                            final_content.replace("\n\n" + hashtags, "")
                            + "\n\n【本期视频信息】\n"
                            + info_for_post
                            + "\n\n"
                            + hashtags
                        )
                        final_content = _rule_optimize_xhs_content(
                            content_with_video_info.replace("\n\n" + hashtags, ""),
                            hashtags,
                            args.mode,
                        )
                        if llm_enabled:
                            final_content = _llm_optimize_xhs_content(title, final_content, args.mode)
                    video_info = {
                        "local_dir": str(latest_dir),
                        "local_file": str(videos[0]),
                        "mcp_video_path": mcp_video_path,
                        "info_md": str(latest_dir / "info.md"),
                        "info_excerpt": info_highlights,
                        "info_llm_excerpt": llm_info,
                    }
                    video_endpoint = os.environ.get(
                        "XHS_MCP_PUBLISH_VIDEO_ENDPOINT",
                        "http://127.0.0.1:18060/api/v1/publish_video",
                    )
                    publish_result = _publish_video_via_mcp(
                        title=title,
                        content=final_content,
                        video_path=mcp_video_path,
                        tags=tags,
                        endpoint=video_endpoint,
                    )
                    print("\n--- MCP Video Publish ---\n", publish_result)
        else:
            publish_result = _publish_via_mcp(
                title=title,
                content=final_content,
                image_paths=mcp_image_paths,
                tags=tags,
                endpoint=args.mcp_endpoint,
            )
            print("\n--- MCP Publish ---\n", publish_result)

    asset_summary = f"cover={note['assets'].get('cover_candidates')[:1]}, stories={len(note['assets'].get('story_images') or [])}"

    record = {
        "theme_id": campaign.get("theme_id"),
        "account_id": args.account_id,
        "title": title,
        "dry_run": dry_run,
        "compliance_ok": note["compliance_ok"],
        "compliance_hits": note["compliance_hits"],
        "publish_result": publish_result,
        "asset_summary": asset_summary,
        "mcp_image_paths": mcp_image_paths,
        "mode": args.mode,
        "video_info": video_info,
        "final_content_preview": final_content[:240],
        "note": "oauth" if args.oauth_code else ("refresh" if args.refresh_token else ""),
    }
    append_jsonl(record)
    append_daily_markdown(record)
    print("\n已写入 marketing/logs/xhs_publish.jsonl 与当日 md。")
    if not args.oauth_code and not args.refresh_token and not args.execute and not args.mcp_publish:
        print("\n模式：仅生成软文与运营日记（未调用小红书 API）。可复制正文到 App 手动发布。")
    return 0 if note["compliance_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
