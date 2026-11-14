# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Agent is the Python AI service layer for a children's homework tutoring app. It exposes OCR, personalized story generation, step-by-step solution guidance, voice synthesis, and illustration generation via a FastAPI HTTP service consumed by a main backend.

## Common Commands

### Run the API

Development (single-process):
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8011
```

Production (multi-process via Gunicorn + Uvicorn worker):
```bash
gunicorn -c gunicorn.conf.py api.main:app
```

Environment variables for Gunicorn: `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`.

### Tests

Run all tests:
```bash
pytest
```

Run a specific test file:
```bash
pytest tests/test_api_ocr.py
```

Run the end-to-end flow with visible output (the `-s` flag is required to see step details):
```bash
pytest tests/test_e2e_homework_flow.py -v -s
```

### Scripts

Generate and auto-publish Xiaohongshu content (the script wraps `marketing/xiaohongshu/publish_cli.py` and posts to local `xiaohongshu-mcp`):
```bash
python3 scripts/xhs_publish.py                              # default: miniprogram intro + auto-publish
python3 scripts/xhs_publish.py --mode miniprogram --no-mcp-publish   # generate only, no posting
python3 scripts/xhs_publish.py --mode daily-video           # daily video (reads latest dir under uploads/vedio)
python3 scripts/xhs_publish.py --mode daily-video --use-llm # let LLM rewrite info.md before publishing
```

MCP endpoints can be overridden via `XHS_MCP_PUBLISH_ENDPOINT` and `XHS_MCP_PUBLISH_VIDEO_ENDPOINT` (defaults are `http://127.0.0.1:18060/api/v1/publish[_video]`).

Daily Coze workflow job (random child profile + theme → submits Coze workflow → downloads video):
```bash
python3 scripts/openclaw_daily_coze_job.py
python3 scripts/openclaw_daily_coze_job.py --background  # log → logs/openclaw_daily_coze_job_*.log
```

### Docker Dependencies

If MySQL/Redis/Milvus are needed:
```bash
docker compose up -d
```

The `xiaohongshu-mcp` container is in `tools/xiaohongshu-mcp/` and publishes to port `18060`.

## Architecture

### API Layer (`api/`)

- `api/main.py` — FastAPI app with lifespan, CORS, and a request-logging middleware that attaches `method/path/status/duration_ms` to every log line.
- `api/schemas.py` — Pydantic request/response models aligned with the frontend API contract.

`.env` is loaded via `utils.env.safe_load_dotenv` (tolerant of malformed lines so a single bad value won't crash startup). The loader is invoked at the top of `api/main.py` and `tests/conftest.py` before any service module imports.

Routes:
- `POST /ocr/recognize` — OCR recognition returning structured `questions` and `figure_urls`.
- `POST /content/generate` — Generates personalized stories, illustration prompts, and learning questions.
- `POST /content/solution-guide` — Step-by-step solution guide using the child's interest theme.
- `POST /voice/synthesize` — Aliyun TTS voice synthesis (base64 audio response).
- `POST /content/illustrate` — Async illustration generation via TTAPI Midjourney or Gemini. Overall timeout is read from `configs/content_generation.yaml` (`illustration.api_timeout`); a timeout returns 504.
- `POST /agent/img_extractor` — Comic panel extraction via OpenCV border detection. Output dir comes from `illustration.img_extractor_output_dir` in `configs/content_generation.yaml` (default `uploads/img_extractor/<timestamp>/`).
- `GET /health` — Health check.

Static file mount: `/uploads` serves the `uploads/` directory for OCR figures and extracted panels.

### Service Modules

- `ocr/` — Pipeline: `preprocessing/` → engine (`baidu_ocr.py` etc., selected via `configs/ocr_config.yaml#engine`) → `postprocessing/question_parser.py`. `figures.py` extracts in-image figures; `service.py` is the entry point used by the API.
- `content_generation/story_generator/` — `generate_story()` produces `{storyId, title, summary, story, questions, illustration_prompts, theme, solution_guide, estimated_reading_time}`. Stories are 4-segment (introduction/challenge/solution/conclusion), 300–500 chars, child-friendly.
- `content_generation/solution_generator/` — `generate_solution_guide()` reuses the child's interest theme for step-by-step explanations.
- `content_generation/illustration_gen/` — `generate_illustration_images_async()` calls TTAPI/Gemini per provider config.
- `voice_synthesis/aliyun_tts.py` — Returns `{success, audio_data|error, format}`. Voice/format/speech_rate defaults centralized in `configs/tts_config.yaml`.
- `marketing/xiaohongshu/` — `publish_cli.py` is the CLI entry; `composer.py` builds the 5-section post body; `theme.py` parses the latest video's `info.md`; `diary.py` writes `marketing/logs/xhs_publish.jsonl` + daily summary. Auto-publishing goes through `xiaohongshu-mcp` (browser + cookie), **not** the legacy open-platform API in `client.py`.
- `tools/` — `comic_panel_extractor.py` (OpenCV-based border detection) and `xiaohongshu-mcp/` (Dockerized MCP server, port `18060`).
- `utils/` — `env.py` (`safe_load_dotenv`) and `logging.py` (`get_logger`, writes to console and `logs/app.log`; level via `LOG_LEVEL`).

### Configuration

- `.env` — Secrets and runtime overrides (copy from `.env.example`). Required: `DASHSCOPE_API_KEY`, `MODEL_NAME` (e.g. `qwen-plus`). Optional: `BAIDU_OCR_*`, `ALIYUN_TTS_*`, `TTAPI_API_KEY`, `GEMINI_API_KEY`, `REDIS_URL`, `MILVUS_HOST/PORT`, `LOG_LEVEL`.
- `configs/` — YAML service configs: `content_generation.yaml` (story/illustration/img_extractor), `ocr_config.yaml` (engine selection + enhancement), `tts_config.yaml`.
- `config/` — Xiaohongshu campaign and (legacy) open-platform configs: `xhs_campaign.yaml`, `xhs_api.yaml`, `daily_coze_config.json`.

All service code reads configs from YAML or environment variables. No secrets are hardcoded.

### LangChain Conventions

- LangChain 1.0 + LCEL: build chains with the `Runnable` interface (`invoke`, `|` composition). Avoid the legacy `Chain`/`run` APIs.
- LLM calls go through `ChatTongyi` / Qwen via `langchain-dashscope` (`DASHSCOPE_API_KEY` + `MODEL_NAME`). Embeddings use `DashScopeEmbeddings` (`text-embedding-v2`).
- Prefer `langchain_core.runnables` (`RunnablePassthrough`, `RunnableLambda`) when extending chains.
- LangGraph (`langgraph` + `langgraph.checkpoint.memory.InMemorySaver`) is available for graph/agent flows but most pipelines today are LCEL chains.

### Testing Patterns

- `tests/conftest.py` calls `safe_load_dotenv` and provides session-scoped fixtures: `sample_image_path/base64/bytes` (defaults to `imgs/小学四年级数学试题.png`) and `story_comic_image_path/base64` (12-panel test image).
- Tests mock external APIs (OCR, illustration) when credentials are unavailable.
- `pytest.ini` ignores `urllib3` OpenSSL warnings and the `aliyun-nls` `ssl.PROTOCOL_TLS` deprecation warning (third-party SDK not yet adapted to Python 3.11+).

### Long-Term Memory

The `.cursorrules` file and `memory-bank/` directory contain project decisions and conventions. When making significant changes, update `memory-bank/3-architecture.md` and `memory-bank/4-progress.md`.
