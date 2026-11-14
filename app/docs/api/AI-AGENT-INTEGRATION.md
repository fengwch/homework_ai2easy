# AI-Agent 对接说明

本文档说明后端与 AI-Agent（`http://0.0.0.0:8001`）的对接位置及实现状态。

## 配置

在 `configs/config.yaml` 或 `configs/config.test.yaml` 中配置：

```yaml
ai_agent:
  url: "http://0.0.0.0:8001"
  timeout: 600s  # 请求超时，默认 10 分钟；超时/连接失败时自动重试 3 次
```

- **url 为空或未配置**：调用回退到 mock 逻辑（延迟 + 模拟数据）
- **url 已配置**：调用 AI-Agent 对应接口

## 对接点一览

| 后端功能 | Agent-API 接口 | 实现位置 | 说明 |
|----------|----------------|----------|------|
| 扫描识别 | `POST /ocr/recognize` | `internal/biz/usecase/assignment_usecase.go` → `runOCR` | 触发扫描后，异步调用 OCR 识别作业图片，写入题目 |
| 内容生成 | `POST /content/generate` | `internal/biz/usecase/assignment_usecase.go` → `runGenerate` | 触发生成后，异步调用内容生成，落库故事内容 |
| 获取学习材料 | - | `internal/server/content.go` | 从 DB 读取 `story_contents`，无则回退 mock |
| 解题引导 | `POST /content/solution-guide` | `internal/server/content.go` → `handleSolutionGuide` | 已对接，未配置时返回 mock |
| 语音合成 | `POST /voice/synthesize` | `internal/server/content.go` → `handleVoiceSynthesize` | 已对接，未配置时返回 503 |

## 实现详情

### 1. OCR 识别（`/ocr/recognize`）

- **调用时机**：用户上传作业图片 → 触发扫描（`POST /api/v1/assignments/{id}/scan`）→ 异步 `runOCR`
- **输入**：作业首张图片（URL 如 `/uploads/assignments/1/0.jpg` 会转为本地路径后读取为 base64）、科目 `subject`
- **输出**：题目列表写入 `assignments.questions`
- **回退**：AI-Agent 未配置或调用失败时使用 mock 题目

### 2. 内容生成（`/content/generate`）

- **调用时机**：作业识别完成 → 触发生成（`POST /api/v1/assignments/{id}/generate`）→ 异步 `runGenerate`
- **输入**：`assignment_id`、`child_profile`（儿童姓名、年级、兴趣）、`questions`、`subject`
- **输出**：故事内容写入 `story_contents`，`assignments.generated_content` 更新为 `storyId`、`status: completed`
- **回退**：AI-Agent 未配置或调用失败时使用 mock 故事并落库

### 3. 获取学习材料（`GET /api/v1/contents/{story_id}`）

- **数据来源**：优先从 `story_contents` 表读取
- **回退**：若无记录，返回 mock 数据（兼容历史或未落库的 `story_id`）

## 数据流

```
上传图片 → 创建作业 → 触发扫描
    ↓
runOCR: 若 ai_agent.url 已配置 → POST /ocr/recognize → 更新 questions
    否则 → mock 题目
    ↓
识别完成 → 触发生成
    ↓
runGenerate: 若 ai_agent.url 已配置 → POST /content/generate → 落库 story_contents
    否则 → mock 故事 → 落库 story_contents
    ↓
用户点击「开始学习」→ GET /api/v1/contents/{story_id}
    ↓
从 story_contents 读取 → 返回学习材料
```

### 4. 解题引导（`POST /content/solution-guide`）

- **调用时机**：前端请求 `POST /api/v1/contents/solution-guide`
- **输入**：`question`（id, questionType, originalText）、`child_profile`（name, interests）
- **输出**：theme、steps、full_text
- **回退**：AI-Agent 未配置时返回 mock 引导步骤

### 5. 语音合成（`POST /voice/synthesize`）

- **调用时机**：前端请求 `POST /api/v1/voice/synthesize`
- **输入**：text（必填）、voice（默认 xiaoyun）、format（默认 mp3）
- **输出**：success、audio_data（base64）、format
- **回退**：AI-Agent 未配置时返回 503 Service Unavailable

## 相关文件

- `internal/pkg/aiagent/client.go` - AI-Agent HTTP 客户端
- `internal/biz/usecase/assignment_usecase.go` - OCR / 内容生成业务逻辑
- `internal/data/model/story_content.go` - 故事内容模型
- `internal/data/repository/story_content_repository.go` - 故事内容仓储
- `internal/server/content.go` - 学习材料 HTTP 处理
