# scripts 目录说明

本目录存放项目常用脚本，覆盖三类场景：

- Coze 工作流调用与定时任务
- 小红书内容生成与发布入口
- 本地接口联调工具

建议在项目根目录执行以下命令：

```bash
cd /Users/fengwanchang/Documents/homework_ai2easy/agent
```

## 1) `xhs_publish.py`

小红书发布入口脚本。它会转调 `marketing/xiaohongshu/publish_cli.py`。

- 默认行为：生成内容并通过本地 `xiaohongshu-mcp` 自动发布
- 支持两种模式：
  - `miniprogram`：小程序介绍（会附带步骤图）
  - `daily-video`：每日视频（读取 `uploads/vedio` 最新目录）

常用命令：

```bash
# 默认：小程序介绍 + 自动发布
python3 scripts/xhs_publish.py

# 小程序介绍，仅生成不发布
python3 scripts/xhs_publish.py --mode miniprogram --no-mcp-publish

# 每日视频 + 自动发布视频
python3 scripts/xhs_publish.py --mode daily-video

# 每日视频 + AI整理同目录 info.md 后再发布（需 DASHSCOPE_API_KEY）
python3 scripts/xhs_publish.py --mode daily-video --use-llm
```

相关环境变量（可选）：

- `XHS_MCP_PUBLISH_ENDPOINT`（默认 `http://127.0.0.1:18060/api/v1/publish`）
- `XHS_MCP_PUBLISH_VIDEO_ENDPOINT`（默认 `http://127.0.0.1:18060/api/v1/publish_video`）


调用mcp失败，可登录mcp 进行测试

- npx @modelcontextprotocol/inspector 进行安装
- http://localhost:6274/ 登录进行测试

---

## 2) `openclaw_daily_coze_job.py`

每日 Coze 工作流任务脚本。会随机生成儿童档案、学科题目、动画主题，然后调用 `call_coze_workflow.py`。

常用命令：

```bash
# 前台执行（实时输出）
python3 scripts/openclaw_daily_coze_job.py

# 后台执行（立即返回，日志写入 logs/）
python3 scripts/openclaw_daily_coze_job.py --background
```

后台日志文件示例：

- `logs/openclaw_daily_coze_job_YYYYmmdd_HHMMSS.log`

常用环境变量（可选）：

- `COZE_API_TOKEN`
- `COZE_WORKFLOW_ID`
- `COZE_APP_ID`
- `COZE_MAX_WAIT_SECONDS`
- `DAILY_SUBJECTS`（如 `数学,语文`）
- `DAILY_AGES`、`DAILY_GENDERS`、`DAILY_NAMES_男`、`DAILY_NAMES_女`

---

## 3) `call_coze_workflow.py`

底层 Coze 异步工作流调用器：提交任务、轮询状态、解析输出，并自动下载返回视频到 `uploads/vedio/<时间目录>/`。

常用命令：

```bash
python3 scripts/call_coze_workflow.py \
  --token "$COZE_API_TOKEN" \
  --workflow-id "7613788373953953834" \
  --app-id "7613730010209878070" \
  --parameters-json '{"theme":"海底小纵队","subject":"数学"}'
```

也支持：

- `--parameters-file <json文件>`
- `--max-wait-seconds <秒>`
- `--poll-interval <秒>`

---

## 4) `call_illustrate_api.py`

本地调试脚本，模拟 `curl` 调用 `POST /content/illustrate`。

常用命令：

```bash
python3 scripts/call_illustrate_api.py
```

可选环境变量：

- `AGENT_BASE_URL`（默认 `http://localhost:8001`）
- `ILLUSTRATE_TIMEOUT`（默认 `400` 秒）
- `ILLUSTRATE_PROMPTS`（逗号分隔）
- `ILLUSTRATE_INTERESTS`（逗号分隔）

---

## 快速排查建议

- 小红书发布失败：先确认 `xiaohongshu-mcp` 容器在线、登录态有效、`/app/images` 与 `/app/videos` 可读。
- Coze 任务失败：先看 `logs/openclaw_daily_coze_job_*.log`，若出现 `RPM limit exceeded`，可降低并发/拉长轮询间隔。
- 仅想验证生成内容：统一加 `--no-mcp-publish`。

