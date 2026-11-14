# 数据库表结构与 questionId 说明

本文档说明后端接口实现中 **questionId 的生成规则**、**MySQL 表结构** 及与 API 的对应关系。

---

## 1. questionId 生成规则

### 1.1 定义

`questionId` 是**题目在作业内的唯一标识**，类型为字符串，用于：

- 路径参数：`/api/v1/assignments/{id}/questions/{question_id}`
- 单题生成：`/api/v1/assignments/{assignmentId}/questions/{question_id}/generate`
- 关联 `story_contents`、`question_generation_statuses` 表中的题目

### 1.2 来源

| 来源 | 格式 | 说明 |
|------|------|------|
| AI-Agent OCR | 由 Agent 返回 | `POST /ocr/recognize` 响应中每题的 `id` 字段，如 `q1`、`q2` |
| Mock OCR | `q{N}` | 后端 mock 使用 `q1`、`q2`… 与 Agent 约定一致 |
| 前端保存 | 保持不变 | `PUT /api/v1/assignments/{id}` 时，`questions[].id` 沿用 OCR 返回的 id |

### 1.3 约束

- **唯一性**：在同一作业 `assignments.questions` JSON 数组内唯一
- **不可变**：题目保存后，questionId 不建议修改，否则单题生成状态会失效
- **格式建议**：`q1`、`q2`、`q3`… 或 Agent 自定义格式（如 `ques-001`）

### 1.4 相关 ID 对照

| ID 类型 | 格式示例 | 说明 |
|---------|----------|------|
| questionId | `q1` | 题目在作业内标识 |
| storyId（作业级） | `story-{assignmentId}` | 整份作业生成的故事 |
| storyId（单题级） | `story-{assignmentId}-{questionId}` 或 Agent 返回 | 单题生成的故事 |
| contentId | `content-{assignmentId}-{questionId}` | 单题生成任务标识，用于轮询状态 |

---

## 2. 表结构变更概览

| 表名 | 变更类型 | 说明 |
|------|----------|------|
| `users` | 已有 | 用户 |
| `children` | 已有 | 儿童档案 |
| `assignments` | 已有 | 作业（含 questions JSON） |
| `story_contents` | 新增 + 字段 | 故事内容，新增 `question_id` |
| `question_generation_statuses` | 新增 | 单题内容生成状态 |

---

## 3. 表结构详情

### 3.1 users

用户表（已有）。

### 3.2 children

儿童档案表（已有）。

### 3.3 assignments

作业表（已有）。主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint unsigned | 主键 |
| child_id | bigint unsigned | 儿童 ID |
| subject | varchar(20) | 科目 |
| original_images | json | 图片 URL 数组 |
| **questions** | json | 题目数组，每项含 `id`(questionId)、`question_number`、`question_type` 等 |
| generated_content | json | 作业级生成内容 `{story_id, status}` |
| status | varchar(20) | pending/processing/completed/failed |

`questions` JSON 每项结构示例：

```json
{
  "id": "q1",
  "question_number": 1,
  "question_type": "multiple_choice",
  "original_text": "1. 下列哪个数是偶数？...",
  "structured_data": { "stem": "...", "options": [], "answer": "B", "analysis": "..." },
  "knowledge_points": [],
  "metadata": {}
}
```

### 3.4 story_contents（有变更）

故事/学习材料内容。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint unsigned | 主键 |
| story_id | varchar(64) | 唯一，故事 ID |
| assignment_id | bigint unsigned | 作业 ID |
| **question_id** | varchar(64) | **新增** 单题生成时非空，关联题目 |
| title | varchar(200) | 标题 |
| summary | text | 简介 |
| story | longtext | 正文 |
| questions | json | 题目摘要 |
| theme | varchar(100) | 主题 |
| created_at, updated_at | datetime | |
| deleted_at | datetime | 软删除 |

- `question_id` 为空：作业级生成的故事
- `question_id` 非空：单题生成的故事

### 3.5 question_generation_statuses（新增）

单题内容生成状态。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint unsigned | 主键 |
| assignment_id | bigint unsigned | 作业 ID |
| question_id | varchar(64) | 题目 ID |
| status | varchar(20) | pending/processing/completed/failed |
| story_id | varchar(64) | 完成时的故事 ID |
| created_at, updated_at | datetime | |
| deleted_at | datetime | 软删除 |

**唯一约束**：`(assignment_id, question_id)`

---

## 4. 接口与表关系

| 接口 | 涉及表 | 说明 |
|------|--------|------|
| GET/PUT assignments/{id} | assignments | 读写 questions JSON，其中含 questionId |
| POST .../questions/{questionId}/generate | question_generation_statuses, story_contents | 创建状态记录，异步落库故事 |
| GET .../questions/{questionId}/generate-status | question_generation_statuses | 按 assignment_id+question_id 查询 |
| GET /api/v1/contents/{storyId} | story_contents | 按 story_id 查询 |

---

## 5. 迁移说明

- 项目使用 **GORM AutoMigrate**，启动时自动创建/更新表结构
- 新增 `story_contents.question_id`、`question_generation_statuses` 表会在首次启动后自动生效
- 若需手动执行 DDL，参见 `scripts/ddl.sql`
