# AI-Agent 项目

本仓库是「AI 赋能儿童作业辅导 App」中的 **AI-Agent 部分**，对应整体技术架构里的 **AI 服务层（Python）**，提供 OCR 识别、个性化故事生成、解题引导、语音合成等能力，供主后端或统一 API 通过 HTTP 调用。

---

## 一、启动说明

### 1. 环境要求

- Python 3.9+
- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/install/)（可选，仅在使用 MySQL/Redis/Milvus 时）

### 2. 安装依赖

在项目根目录（即本 README 所在目录）执行：

```bash
pip install -r requirements.txt
```

建议使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置并按需修改：

```bash
cp .env.example .env
```

必填（若使用故事/解题引导）：

- `DASHSCOPE_API_KEY`：阿里云 DashScope API Key（调用 Qwen 模型）
- `MODEL_NAME`：如 `qwen-plus` 或 `qwen-turbo`

可选：

- **OCR**：`BAIDU_OCR_API_KEY`、`BAIDU_OCR_SECRET_KEY`（当 `configs/ocr_config.yaml` 中 `engine: baidu`）
- **语音合成**：`ALIYUN_TTS_*`（见下方「可选配置获取方式」）
- **漫画/插图**：`TTAPI_API_KEY` 或 `GEMINI_API_KEY`（见下方）
- **Redis / Milvus**：使用异步任务或向量检索时配置 `REDIS_URL`、`MILVUS_HOST`、`MILVUS_PORT`
- **日志**：`LOG_LEVEL=DEBUG` 可输出更详细日志，便于调试

#### 可选配置获取方式

| 配置项 | 获取方式 |
|--------|----------|
| **阿里云 TTS（语音合成）** | |
| `ALIYUN_TTS_ACCESS_KEY_ID` / `ALIYUN_TTS_ACCESS_KEY_SECRET` | 登录 [阿里云控制台](https://ram.console.aliyun.com/manage/ak) → 访问控制 → 用户 → 创建 AccessKey |
| `ALIYUN_TTS_APPKEY` | 登录 [智能语音交互控制台](https://nls-portal.console.aliyun.com/) → 创建项目 → 项目列表中查看 AppKey |
| `ALIYUN_TTS_REGION` | 默认 `cn-shanghai`，按项目所在地域选择 |
| **TTAPI（Midjourney 插图）** | |
| `TTAPI_API_KEY` | 注册 [TTAPI](https://ttapi.io) → 个人中心 → API 密钥，按量付费模式可用 |
| `TTAPI_BASE_URL` | 默认 `https://api.ttapi.io`，托管模式或自建时按文档修改 |
| **Gemini/Imagen（插图）** | |
| `GEMINI_API_KEY` | 访问 [Google AI Studio](https://aistudio.google.com/app/apikey) → 创建 API Key，需安装 `pip install google-genai` |

### 4. 可选：启动 Docker 依赖

若需 MySQL、Redis、Milvus 等，在项目根目录执行：

```bash
docker compose up -d
```

详细说明见 [docs/docker-env.md](docs/docker-env.md)。

### 5. 启动应用

**方式一：开发 / 单进程（Uvicorn）**

在项目根目录执行：

```bash
source venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

- 若已激活虚拟环境且 `uvicorn` 在 PATH 中，也可：`uvicorn api.main:app --host 0.0.0.0 --port 8001`
- 服务默认地址：`http://0.0.0.0:8001`，本机访问：`http://localhost:8001`
- 健康检查：浏览器或 `curl http://localhost:8001/health`，返回 `{"status":"ok"}` 表示正常
- API 文档（Swagger）：`http://localhost:8001/docs`

**方式二：生产 / 多进程（Gunicorn）**

本应用为 **ASGI**（FastAPI），需通过 Gunicorn + Uvicorn Worker 启动：

```bash
source venv/bin/activate
gunicorn -c gunicorn.conf.py api.main:app
```

- 默认监听 `0.0.0.0:8001`，进程数 2，单请求超时 120 秒（适配 OCR、LLM 等长耗时）。
- 可选环境变量（在启动前 export 或写在 `.env` 中，需在启动前被加载）：

| 变量 | 说明 | 默认 |
|------|------|------|
| `GUNICORN_BIND` | 监听地址:端口 | `0.0.0.0:8001` |
| `GUNICORN_WORKERS` | Worker 进程数 | `2` |
| `GUNICORN_TIMEOUT` | 请求超时（秒） | `120` |
| `GUNICORN_LOG_LEVEL` | 日志级别 | `info` |

示例：指定端口与 4 个 worker：

```bash
export GUNICORN_BIND=0.0.0.0:8002
export GUNICORN_WORKERS=4
gunicorn -c gunicorn.conf.py api.main:app
```

- 应用内业务日志仍由 `utils.logging` 输出到控制台及 `logs/app.log`，`LOG_LEVEL` 控制详细程度。

---

## 二、应用说明

### 1. 服务定位

- **本仓库职责**：提供 AI 能力接口（OCR、故事生成、解题引导、语音合成），请求/响应与《前端接口文档》中 `questions`、`contents/{story_id}` 等数据契约对齐。
- **非本仓库职责**：用户/儿童档案、作业 CRUD、上传存储、任务状态持久化、对外完整 REST 路径（如 `POST /api/v1/assignments/upload`）由主后端实现；本仓库仅提供「被调用的 AI 服务」。

### 2. 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/ocr/recognize` | OCR 识别，返回结构化题目列表 `questions` |
| POST | `/content/generate` | 生成个性化故事、插图提示、学习页题目数据 |
| POST | `/content/solution-guide` | 按题目与兴趣生成解题引导（分步讲解） |
| POST | `/voice/synthesize` | 语音合成（可选，需配置阿里云 TTS） |
| POST | `/content/illustrate` | 漫画/插图生成（可选，需 TTAPI 或 Gemini API Key） |

详细请求/响应格式见 [docs/api/Agent-API.md](docs/api/Agent-API.md)。

### 3. 使用示例

**健康检查**

```bash
curl http://localhost:8001/health
```

**OCR 识别**（需传入 base64 图片或图片 URL，以及学科）

```bash
curl -X POST http://localhost:8001/ocr/recognize \
  -H "Content-Type: application/json" \
  -d '{"image_data":"<base64或URL>","subject":"数学"}'
```

**内容生成**（需传入儿童档案与题目列表）

```bash
curl -X POST http://localhost:8001/content/generate \
  -H "Content-Type: application/json" \
  -d '{
    "child_profile":{"name":"小明","age":8,"grade":"三年级","interests":["奥特曼"]},
    "questions":[...],
    "subject":"数学"
  }'
```

**解题引导**

```bash
curl -X POST http://localhost:8001/content/solution-guide \
  -H "Content-Type: application/json" \
  -d '{"question":{...},"child_profile":{"name":"小明","interests":["奥特曼"]}}'
```

交互式调试可使用 Swagger UI：访问 `http://localhost:8001/docs`。

### 4. 日志与调试

- 统一日志模块：`utils/logging.py`，通过 `LOG_LEVEL` 控制级别（默认 `INFO`）。
- 调试时在 `.env` 中设置 `LOG_LEVEL=DEBUG`，可看到更详细的 OCR、故事生成、解题引导等日志。
- 每个 HTTP 请求会记录方法、路径、状态码与耗时。

### 5. 相关文档

- [docs/api/Agent-API.md](docs/api/Agent-API.md)：Agent 接口请求/响应说明
- [docs/api/前端接口文档.md](docs/api/前端接口文档.md)：前端与主后端接口约定
- [docs/docker-env.md](docs/docker-env.md)：Docker 环境与 `.env` 配置说明
- [docs/核心功能规格说明.md](docs/核心功能规格说明.md)：作业扫描、内容生成、解题引导等规格
- [marketing/XHS_MCP_PUBLISH.md](marketing/XHS_MCP_PUBLISH.md)：经 xiaohongshu-mcp 发布（推荐）
- [marketing/XHS_OPEN_PLATFORM.md](marketing/XHS_OPEN_PLATFORM.md)：开放平台 API（可选 / 遗留）

---

## 小红书软文与发布（可选）

- **配置**：`config/xhs_campaign.yaml`。**自动发帖**推荐 [xiaohongshu-mcp](tools/xiaohongshu-mcp/README.md)（扫码登录后 `POST /api/v1/publish`），详见 [marketing/XHS_MCP_PUBLISH.md](marketing/XHS_MCP_PUBLISH.md)，**无需**开放平台发帖接口。
- **默认命令**（生成后自动调用本地 xiaohongshu-mcp 发布图文，并写运营日记）：`python3 scripts/xhs_publish.py`
- **仅生成不发布**：`python3 scripts/xhs_publish.py --no-mcp-publish`
- **遗留**：若仍对接开放平台 `common_controller`，再配置 `config/xhs_api.yaml` 与 `.env` 中 `XHS_*`，见 [marketing/XHS_OPEN_PLATFORM.md](marketing/XHS_OPEN_PLATFORM.md)
