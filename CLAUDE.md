# CLAUDE.md

This file provides repo-level guidance to Claude Code when working anywhere under `homework_ai2easy/`. Read this for the cross-project map, then drop into the relevant subproject's own `CLAUDE.md` (all except `HomeworkCompass/`) for specifics.

## Product

Children's homework tutoring app: parents/children upload homework, the system OCRs it, generates a child-friendly story explaining the questions, produces step-by-step solution guides, and delivers voice + illustrations. Cross-platform client (H5 / WeChat MP / iOS / Android / Harmony) backed by a Go service that orchestrates a Python AI service layer.

## Monorepo Layout

```
homework_ai2easy/
├── agent/            # Python AI service layer (FastAPI) — OCR / story / TTS / illustration
├── app/              # Frontend client (uni-app x + Vue 3 + TypeScript); actual code lives in app/frontend/
├── backend/          # Main Go backend (Kratos v2) — business logic, persistence, AI orchestration
├── HomeworkCompass/  # Standalone Python CLI (`hw`) — homework parsing, mechanical validation, A4 render
└── docs/             # Shared product / architecture / API documentation
```

Each of `agent/`, `app/`, `backend/`, `HomeworkCompass/` is an independent project with its own dependencies, tests, and build. The root is **not** a git repo; `HomeworkCompass/` has its own `.git`, and `agent/`/`app/`/`backend/` are versioned independently. They communicate over network protocols, not by importing each other's code.

`HomeworkCompass/` is **not** wired into the app/backend/agent request flow yet — it is a spec-driven CLI (see its `README.md` and `docs/使用指南.md`) whose defining invariant is *no fabrication, no omission, block on ambiguity*: `parse` → `confirm` → `render`, and `render` refuses to write when `pending` is non-empty (exit 2). Preserve that contract; do not make `hw` guess.

## Subproject Responsibilities

| Subproject | Stack | Owns |
|---|---|---|
| [agent/](agent/CLAUDE.md) | Python 3 + FastAPI + LangChain 1.0 LCEL + ChatTongyi (DashScope) | OCR engines (Baidu / Paddle / Qwen-VL), story generation, solution guides, Aliyun TTS, TTAPI Midjourney + Gemini illustration, OpenCV comic panel extraction, Xiaohongshu marketing pipeline |
| [app/](app/CLAUDE.md) | uni-app x (Vue 3 + TS + Pinia + Vite), HBuilderX ^3.99 | Cross-platform UI for auth / child / assignment / content / learning / parent / print / profile / reward. **All code is under `app/frontend/`** (`.uvue` pages, `api/`, `stores/`) |
| [backend/](backend/CLAUDE.md) | Go + Kratos v2 + Wire + GORM + MySQL + Redis | Auth / User / Child / Assignment / Content / File services; JWT; file upload; PDF; orchestrates `agent/` |
| [HomeworkCompass/](HomeworkCompass/README.md) | Python 3.13 + Pillow, `hw` console script | Offline homework-text → validated structured homework → A4 2480×3508 @300dpi PNG. No CLAUDE.md; guide in `docs/使用指南.md` |
| [docs/](docs/) | Markdown | Product requirements, architecture, API specs, database schema, marketing assets |

## Cross-Project Contracts

### Request flow

```
app/ (uni-app x)
   ↓ HTTPS, /api/v1/...
backend/ (Go Kratos, port 8000)
   ↓ HTTP, internal
agent/ (Python FastAPI, port 8011)
   ↓ External APIs
[ DashScope / Baidu OCR / Aliyun TTS / TTAPI / Gemini / WeChat / SMS ]
```

Port note: `agent/` actually binds **8011** (`backend/configs/config.yaml` → `data.ai_agent.url`), despite `agent/gunicorn.conf.py`'s docstring mentioning 8001. When something can't reach the AI service, check the port first.

- **`app/` must never call `agent/` directly.** All AI requests go through `backend/`'s ContentService / AssignmentService, which auth, rate-limit, and audit them.
- **`backend/` is the only AI consumer of `agent/`.** It uses `internal/pkg/aiagent` to talk to FastAPI; never imports Python code.
- **`agent/` is stateless from the product's perspective.** It does not persist users, children, assignments, or session state. Anything that needs to outlive a request lives in `backend/`'s MySQL / Redis.

### Response shape (HTTP)

`backend/` returns:
```json
{ "code": 0, "message": "ok", "data": { ... } }
```
- `code === 0`: success, payload in `data`
- `code !== 0`: business error, `message` is user-facing, `code` falls in one of the documented error ranges (10000-19999 system, 20000-29999 business, 30000-39999 auth, 40000-49999 params, 50000-59999 external)

`agent/` returns standard FastAPI / OpenAPI shapes (typed Pydantic models). `backend/` converts these to the wrapper above before responding to `app/`.

### Field naming

- External (HTTP wire): historically a mix of camelCase and snake_case. Front-end `app/` declares both forms in its TypeScript interfaces for safety.
- Go internal: snake_case for proto / JSON tags, camelCase for Go identifiers.
- Python internal: snake_case throughout; convert at the FastAPI route boundary if the contract requires camelCase.

**Rule**: never rename external fields to "fix" the inconsistency without coordinating across all three subprojects.

## Documentation Locations

- **Product / business**: `docs/产品需求文档.md`, `docs/商业需求文档.md`, `docs/项目章程.md`
- **Architecture (cross-cutting)**: `docs/技术架构文档.md`
- **API specs**: `docs/api/` (shared), plus auto-generated `backend/openapi.yaml`
- **Database**: `docs/database-schema.md`, `docs/database-setup.md`
- **Subproject-specific**: each subproject's `README.md`, `CLAUDE.md`, `memory-bank/`

When making a change that crosses subproject boundaries, update **all** the affected docs in the same change.

## Per-Subproject Tooling

Run commands from inside each subproject directory.

```bash
# agent/  (Python; deps: pip install -r requirements.txt; .env with DASHSCOPE_API_KEY + MODEL_NAME)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8011   # dev
gunicorn -c gunicorn.conf.py api.main:app                    # prod (GUNICORN_BIND/WORKERS/TIMEOUT)
pytest                                                       # all
pytest tests/test_api_ocr.py                                 # one file
pytest tests/test_e2e_homework_flow.py -v -s                 # e2e with step output

# backend/  (Go; first time: make init && make api && make wire)
make run          # build + run with configs/config.yaml
make dev          # go run with configs/config.dev.yaml
make test         # test-unit + test-api (test-api needs MySQL + Redis up)
make test-unit    # internal/biz/usecase + internal/pkg
go test ./internal/biz/usecase -run TestUserUsecase_Profile -v   # single test
make api && make wire   # REQUIRED after any api/**/*.proto or DI edit

# app/frontend/  (uni-app x; build is HBuilderX-driven, no `npm run dev`)
#   HBuilderX → open app/frontend → Run to Browser/H5 or WeChat Developer Tools
npx jest                    # from app/frontend

# HomeworkCompass/  (Python 3.13 CLI)
python3 -m pip install -e ".[dev]"
pytest                                  # default excludes `network` marker
pytest -m network                       # opt-in: real DashScope calls
hw parse --file raw.txt --name 小宇 --offline --out hw.json
```

`app/` build notes, HTTP-client rules, and platform constraints are in [app/CLAUDE.md](app/CLAUDE.md). `backend/`'s proto-first workflow and layer rules are in [backend/CLAUDE.md](backend/CLAUDE.md). `agent/`'s routing/config/LangChain conventions are in [agent/CLAUDE.md](agent/CLAUDE.md).

## Conventional Commits Across the Repo

All four subprojects use Conventional Commits: `type(scope): subject`.
- `type` ∈ `feat | fix | refactor | chore | docs | test | perf | style`
- `scope` aligns with the touched directory and is subproject-specific (`api`, `ocr`, `usecase`, `pages`, `stores`, ...).
- One commit per atomic change. No mixing of subprojects in a single commit unless the change is genuinely a cross-cutting contract update; even then, prefer a series of commits with clear scope per subproject.

## Shared Forbidden Patterns

These hold across the whole monorepo:

- **No hardcoded secrets / endpoints anywhere in source.** Use env vars (`agent/`: `.env` via `safe_load_dotenv`; `backend/`: env-overridden `Bootstrap` config; `app/`: `VITE_API_BASE_URL`). The current `backend/configs/config.yaml` still contains real WeChat & JWT secrets — this is tracked as a live risk in `backend/memory-bank/5-decision-log.md` and must be resolved before any external deploy.
- **No backwards-compatibility shims for hypothetical futures.** If a contract changes, update it everywhere in the same PR.
- **No half-finished features on the main branch of any subproject.** Each subproject's `master`/`main` must always start, build, and pass its default test suite.

## Memory Discipline

Each of `agent/`, `app/`, `backend/` keeps long-term context in its own `memory-bank/` (numbered 0-5: project-brief, tech-stack, implementation-plan, architecture, progress, decision-log). When you make architectural, contractual, or external-integration changes:

1. Update the affected subproject's `memory-bank/3-architecture.md` and `memory-bank/4-progress.md`.
2. Add a `memory-bank/5-decision-log.md` entry if the choice should outlive the current task.
3. If the change touches another subproject's contract, update that subproject's memory too.

Pick the right `CLAUDE.md` for the work at hand:
- Touching Python AI code, prompts, FastAPI routes → [agent/CLAUDE.md](agent/CLAUDE.md)
- Touching Go services, protos, Kratos config → [backend/CLAUDE.md](backend/CLAUDE.md)
- Touching uni-app x pages, components, stores → [app/CLAUDE.md](app/CLAUDE.md)
- Touching the `hw` CLI, its parser/validator/renderer → `HomeworkCompass/docs/使用指南.md` + `README.md` (spec + plan under `HomeworkCompass/docs/superpowers/`)

<comet-ambient-resume>
<!-- Managed by Comet. Edits inside this block may be replaced by comet init/update. -->
<!-- Contract: comet.resume_probe.v2 -->

## Comet Ambient Resume

在这个仓库中，开始处理需要改动或调查的任务前，如果可能存在活跃 Comet workflow，把当前用户请求传入只读探针：`comet resume-probe . --stdin --json`。

- 如果用户通过宿主明确调用任意 Comet Skill（例如 `@comet`、`/comet`、`@comet-native` 或 `/comet-hotfix`），显式调用优先于本恢复协议；不要运行 resume probe，直接进入被调用的 Skill。
- 如果用户通过宿主明确调用的是非 Comet 的 Skill 或斜杠命令，任务意图已由该调用明确：不要运行 resume probe，直接执行该 Skill。
- 如果你正在 Comet 流程内（包括正在等待用户回复你在流程中提出的问题），不要运行 resume probe；把这类回复（例如方案/选项选择）当作当前 change 的继续，直接按用户的选择推进。
- 只信任返回的 `workflow`、`skill` 和 `entrySource`；它们只由项目配置或无配置兼容回退决定。不得扫描或切换另一套 workflow。
- 如果 probe 返回 `auto_resume`，简短说明选中的 active change，并进入 `nextCommand` 指向的永久入口。不要把状态命令当作恢复入口直接推进。
- 如果 probe 返回 `ask_user`，只问一个简短问题并等待用户回复。
- 如果当前请求未明确调用 Comet Skill，且 probe 返回 `out_of_scope` 或 `none`，不要进入 Comet workflow。
- `out_of_scope` 或 `none` 只表示不要因为这个新请求进入 Comet workflow；它绝不表示要暂停或退出一个已在进行的 Comet 流程。
- 如果配置或状态无效且没有 `nextCommand`，停止并报告原因；不要猜测另一个 workflow。
- 不能只因为存在 active change 就把无关任务挂到该 change。Native 的未提交改动由 Native 入口检查，不由探针自动归因。
</comet-ambient-resume>
