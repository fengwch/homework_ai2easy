# P0 核心体验修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 PRD 中标记的 4 项 P0 核心体验断点：兴趣绑定管道、免费额度模型、奖励系统后端、插图进度可视化

**Architecture:** 四组独立子系统，可并行实施：(1) agent 端兴趣绑定增强 (2) backend 端免费额度与奖励系统 (3) app 端插图进度与配额展示。每组改动互不依赖，但 Task 1（兴趣绑定）是产品差异化的核心，应优先完成。

**Tech Stack:** Go (Kratos v2), Python (FastAPI + LangChain), uni-app x (Vue 3 + TS), MySQL, Redis

---

## File Change Map

| Task | Create | Modify | Test |
|---|---|---|---|---|
| Task 1: 兴趣绑定管道 | `agent/content_generation/story_generator/templates.py`（重写）| `agent/content_generation/story_generator/generator.py` | `agent/tests/test_story_generation.py` |
| Task 2: 免费额度模型 | `backend/internal/data/model/daily_usage.go`, `backend/internal/biz/usecase/quota.go`, `backend/internal/pkg/errors/quota.go` | `backend/api/user/v1/user.proto`, `backend/internal/data/repository/quota_repo.go`, `backend/internal/service/grpc/user_service.go`, `backend/internal/service/grpc/assignment_service.go` | `backend/internal/biz/usecase/quota_test.go` |
| Task 3: 奖励系统后端 | `backend/internal/data/model/reward.go`, `backend/internal/biz/usecase/reward.go` | `backend/api/user/v1/user.proto`（追加 reward 相关 message/rpc）, `backend/internal/data/repository/reward_repo.go` | `backend/internal/biz/usecase/reward_test.go` |
| Task 4: 插图进度可视化 | — | `app/frontend/pages/learning/story.uvue`, `app/frontend/api/content.ts` | `app/frontend/pages/pages.test.js` |

---

## Task 1: 兴趣绑定管道增强（agent/）

**Files:**
- Modify: `agent/content_generation/story_generator/generator.py`
- Modify: `agent/content_generation/story_generator/templates.py`
- Create: `agent/tests/test_story_generation.py`
- Modify: `agent/configs/content_generation.yaml`

**现状分析**：兴趣管道已存在但体验不足。`_select_theme()` 只做精确匹配（兴趣标签 == 模板名），匹配不到时返回 `interests[0]` 但无对应模板导致降级为 "小动物学习"。主角名字使用 `child_profile.name`（默认"小明"），但故事标题未体现兴趣。

### Step 1: 编写测试

- [ ] **Step 1.1: 创建测试文件**

Create `agent/tests/test_story_generation.py`:

```python
"""兴趣绑定管道测试：验证故事标题、正文、theme 均使用儿童兴趣。"""
import pytest
from content_generation.story_generator.generator import (
    _select_theme,
    generate_story,
)
from content_generation.story_generator.templates import TEMPLATES, DEFAULT_THEME


class TestSelectTheme:
    """主题选择：精确匹配 + 模糊匹配 + 兜底。"""

    def test_exact_match_ultraman(self):
        assert _select_theme(["奥特曼"]) == "奥特曼"

    def test_exact_match_ocean_squad(self):
        assert _select_theme(["海底小纵队"]) == "海底小纵队"

    def test_partial_match(self):
        """兴趣含关键词时应匹配到对应模板。"""
        assert _select_theme(["喜欢奥特曼"]) == "奥特曼"

    def test_no_match_returns_first_interest(self):
        """无匹配模板时，返回第一个兴趣（作为自定义主题名）。"""
        result = _select_theme(["恐龙战队"])
        assert result == "恐龙战队"

    def test_empty_interests_returns_default(self):
        assert _select_theme([]) == DEFAULT_THEME


class TestGenerateStory:
    """故事生成：验证兴趣关键词出现在标题和正文中。"""

    def test_title_contains_character_interest(self):
        """故事标题应体现兴趣角色。"""
        result = generate_story(
            child_profile={
                "name": "小明",
                "age": 8,
                "grade": "三年级",
                "interests": ["奥特曼"],
            },
            questions=[{
                "id": "q1",
                "questionNumber": 1,
                "originalText": "下列哪个数是偶数？",
                "structuredData": {"stem": "下列哪个数是偶数？", "answer": "B"},
            }],
            subject="数学",
        )
        assert "奥特曼" in result["title"] or "光之战士" in result["title"]
        assert result["theme"] == "奥特曼"

    def test_story_contains_interest_keyword(self):
        """故事正文必须包含兴趣关键词。"""
        result = generate_story(
            child_profile={
                "name": "小明",
                "age": 8,
                "grade": "三年级",
                "interests": ["奥特曼"],
            },
            questions=[{
                "id": "q1",
                "questionNumber": 1,
                "originalText": "2+3=?",
                "structuredData": {"stem": "2+3=?", "answer": "5"},
            }],
            subject="数学",
        )
        # 校验：兴趣关键词必须出现在故事正文中
        assert "奥特曼" in result["story"], "故事正文未包含兴趣关键词"

    def test_theme_field_not_empty(self):
        """theme 字段不应为空。"""
        result = generate_story(
            child_profile={
                "name": "小红",
                "age": 7,
                "grade": "二年级",
                "interests": ["海底小纵队"],
            },
            questions=[{
                "id": "q1",
                "questionNumber": 1,
                "originalText": "1+1=?",
                "structuredData": {"stem": "1+1=?", "answer": "2"},
            }],
            subject="数学",
        )
        assert result["theme"] != "", "theme 字段为空"


class TestGenerateStoryFallback:
    """无 API Key 时的 mock 兜底行为。"""

    def test_mock_story_uses_interest(self, monkeypatch):
        """mock 模式下故事标题也应体现兴趣。"""
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        result = generate_story(
            child_profile={
                "name": "小明",
                "age": 8,
                "grade": "三年级",
                "interests": ["奥特曼"],
            },
            questions=[{"id": "q1", "questionNumber": 1, "originalText": "1+1=?"}],
            subject="数学",
        )
        # mock 标题格式: {interest}的{subject}奇遇记
        assert "奥特曼" in result["title"]
```

### Step 2: 运行测试确认失败

```bash
cd agent
pytest tests/test_story_generation.py -v
```

预期：`TestGenerateStory` 的测试全部 FAIL（当前标题不含兴趣关键词）。

### Step 3: 重写 `_select_theme` 支持模糊匹配

Modify `agent/content_generation/story_generator/generator.py:30-36`:

```python
def _select_theme(interests: List[str]) -> str:
    """选择故事主题：优先精确匹配，其次模糊匹配，最后兜底。"""
    if not interests:
        return DEFAULT_THEME
    # 精确匹配
    for tag in interests:
        if tag in TEMPLATES:
            return tag
    # 模糊匹配：兴趣标签中包含模板关键词
    for tag in interests:
        for tpl in TEMPLATES:
            if tpl in tag or tag in tpl:
                return tpl
    # 无匹配：返回第一个兴趣（将作为自定义主题传入 prompt）
    return interests[0]
```

### Step 4: 增强故事 prompt 强制使用兴趣角色

Modify `agent/content_generation/story_generator/generator.py:113-131`（prompt 部分）:

```python
    # 确定主角名称：兴趣角色优先
    character_name = child_profile.get("name") or "小明"
    interest_lead = interests[0] if interests else ""
    # 在 prompt 中强制要求主角 = 兴趣角色
    if interest_lead:
        character_instruction = (
            f"故事主角必须是「{interest_lead}」或其相关角色（如光之战士、海洋探险队等），"
            f"而不是通用名字「{character_name}」。"
            f"「{character_name}」是孩子的名字，可以在故事开头作为旁白角色引入，"
            f"但核心冒险/挑战必须由兴趣角色主导。"
        )
    else:
        character_instruction = f"故事主角为「{character_name}」。"

    prompt = f"""你是一位儿童故事创作助手。请根据以下信息生成一个适合{age}岁儿童（{grade}）的短故事，将作业题目自然地融入故事情节。

故事主题：{theme}
{character_instruction}
学科：{subject}
题目内容摘要：
{questions_text}

配图说明：{illustration_note}

要求：
1. 将题目转化为故事中的任务或问题，不改变数学本质和难度。
2. 语言生动有趣，用词简单，适合儿童阅读。
3. 内容健康正面，无暴力、恐怖等不适合儿童的内容。
4. 故事长度：{min_chars}-{max_chars}字。
5. 结构分为四段：开头（引入角色）→ 发展（遇到题目/挑战）→ 高潮（思考与解决）→ 结尾（总结或收获）；每段尽量有清晰可画的场景，便于对应上述 {panels_per_prompt} 组插图。
6. 在故事末尾可加一行【学习要点】列出本故事涉及的知识点（简短 bullet）。
7. **重要**：故事正文中必须多次出现「{interest_lead}」（或与之等价的角色名），不少于 3 次。

请直接输出故事正文，不要输出"故事："等前缀。"""
```

### Step 5: 修改标题生成逻辑

Modify `agent/content_generation/story_generator/generator.py:162-163`:

```python
    # 标题：使用兴趣角色 + 学科
    if interest_lead:
        title = f"{interest_lead}的{subject}奇遇记"
    else:
        title = f"{character_name}的{subject}奇遇记"
    summary = f"基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。"
```

### Step 6: 添加兴趣关键词校验与自动重试

Add after the story generation block (before illustration prompts generation), in `agent/content_generation/story_generator/generator.py` around line 150:

```python
    # 校验：故事正文必须包含兴趣关键词，否则重试一次
    if interest_lead and interest_lead not in story:
        logger.warning("故事未包含兴趣关键词，重试生成", extra={"interest": interest_lead})
        retry_prompt = prompt + f"\n\n**重要提醒**：故事正文中必须出现「{interest_lead}」这个角色，请重新生成。"
        try:
            retry_chain = ChatPromptTemplate.from_messages([("human", "{prompt}")]) | model | StrOutputParser()
            story = retry_chain.invoke({"prompt": retry_prompt}).strip()
            logger.debug("重试生成完成", extra={"length": len(story)})
        except Exception as e:
            logger.warning("重试生成也失败，使用降级文案", exc_info=e)
            # 在故事开头插入兴趣角色引入
            intro = f"有一天，{character_name}和{interest_lead}一起做作业时遇到了一个有趣的问题。\n\n"
            story = intro + story
```

### Step 7: 修改 mock 兜底文案

Modify the mock fallback text in `agent/content_generation/story_generator/generator.py` (around line 141 and the fallback after exception):

```python
        if not api_key:
            # mock 标题使用兴趣角色
            mock_title = f"{interest_lead}的{subject}奇遇记" if interest_lead else f"{character_name}的{subject}奇遇记"
            story = f"（请配置 DASHSCOPE_API_KEY 以生成故事）\n\n{character_name}和{interest_lead}一起做作业，遇到了一个有趣的问题：{questions_text[:200]}……\n\n【学习要点】\n• 请完成作业并思考解题方法。"
```

And the exception fallback (around line 149):

```python
        story = f"（故事生成暂时不可用：{e}）\n\n{character_name}和{interest_lead}一起学习：{questions_text[:150]}……\n\n【学习要点】\n• 认真读题，动脑思考。"
```

### Step 8: 配置默认兴趣模板

Modify `agent/configs/content_generation.yaml`:

```yaml
story:
  min_chars: 300
  max_chars: 500
  default_theme: "小动物学习"
  # 新增：兴趣关键词校验重试次数
  interest_validation_retries: 1

illustration:
  panels_per_prompt: 3
  panels_in_image: 6
  panels_layout: "2x3"
  include_dialogue: true
```

### Step 9: 运行测试确认通过

```bash
cd agent
pytest tests/test_story_generation.py -v
```

预期：全部测试 PASS。

### Step 10: 运行全量测试确保无回归

```bash
cd agent
pytest -v
```

### Step 11: Commit

```bash
cd agent
git add content_generation/story_generator/generator.py content_generation/story_generator/templates.py configs/content_generation.yaml tests/test_story_generation.py
git commit -m "feat(content_generation): enhance interest binding in story generation

- fuzzy match interests to theme templates
- force interest character as story protagonist in prompt
- title format: {interest}的{subject}奇遇记
- validate story contains interest keyword, retry once if not
- update mock fallback to use interest character"
```

---

## Task 2: 免费额度模型（backend/）

**Files:**
- Create: `backend/internal/data/model/daily_usage.go`
- Create: `backend/internal/data/repository/quota_repo.go`
- Create: `backend/internal/biz/usecase/quota.go`
- Create: `backend/internal/biz/usecase/quota_test.go`
- Create: `backend/internal/pkg/errors/quota.go`
- Modify: `backend/api/user/v1/user.proto`
- Modify: `backend/internal/service/grpc/user_service.go`
- Modify: `backend/internal/service/grpc/assignment_service.go`

**设计决策**：使用 Redis 计数器存储每日使用量（key: `daily_usage:{user_id}:{YYYY-MM-DD}`），而非 MySQL 表。理由：日粒度数据无需持久化到关系数据库，Redis 天然支持 TTL 过期。

### Step 1: 定义错误码

Create `backend/internal/pkg/errors/quota.go`:

```go
package errors

import kerr "github.com/go-kratos/kratos/v2/errors"

const (
	// ErrCodeDailyQuotaExceeded 每日免费额度已用尽
	ErrCodeDailyQuotaExceeded = 40101
)

func DailyQuotaExceeded(dailyLimit int32) *kerr.Error {
	return kerr.New(
		ErrCodeDailyQuotaExceeded,
		"DAILY_QUOTA_EXCEEDED",
		fmt.Sprintf("今日免费额度已用完（%d题/日），请明日再试或订阅解锁无限量", dailyLimit),
	)
}
```

### Step 2: 定义数据模型

Create `backend/internal/data/model/daily_usage.go`:

```go
package model

// DailyUsage 用户每日使用量，仅用于 Redis 计数，不映射到 MySQL。
type DailyUsage struct {
	UserID uint64 `json:"user_id"`
	Date   string `json:"date"` // YYYY-MM-DD
	Count  int32  `json:"count"`
}
```

### Step 3: 定义仓储接口

Create `backend/internal/data/repository/quota_repo.go`:

```go
package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// QuotaRepository 每日额度仓储
type QuotaRepository interface {
	// IncrementDailyUsage 增加使用计数并返回当前总量；首次使用时设置 TTL 到次日零点
	IncrementDailyUsage(ctx context.Context, userID uint64) (int32, error)
	// GetDailyUsage 获取当前已使用量
	GetDailyUsage(ctx context.Context, userID uint64) (int32, error)
	// ResetDailyUsage 重置使用量（管理操作）
	ResetDailyUsage(ctx context.Context, userID uint64) error
}

type redisQuotaRepo struct {
	rdb       *redis.Client
	dailyLimit int32
}

func NewQuotaRepository(rdb *redis.Client, dailyLimit int32) QuotaRepository {
	return &redisQuotaRepo{rdb: rdb, dailyLimit: dailyLimit}
}

func (r *redisQuotaRepo) key(userID uint64) string {
	return fmt.Sprintf("daily_usage:%d:%s", userID, time.Now().Format("2006-01-02"))
}

func (r *redisQuotaRepo) IncrementDailyUsage(ctx context.Context, userID uint64) (int32, error) {
	key := r.key(userID)
	count, err := r.rdb.Incr(ctx, key).Result()
	if err != nil {
		return 0, err
	}
	// 首次使用时设置 TTL 到当天结束
	if count == 1 {
		now := time.Now()
		ttl := time.Until(time.Date(now.Year(), now.Month(), now.Day(), 23, 59, 59, 0, now.Location()))
		r.rdb.Expire(ctx, key, ttl)
	}
	return int32(count), nil
}

func (r *redisQuotaRepo) GetDailyUsage(ctx context.Context, userID uint64) (int32, error) {
	key := r.key(userID)
	val, err := r.rdb.Get(ctx, key).Result()
	if err == redis.Nil {
		return 0, nil
	}
	if err != nil {
		return 0, err
	}
	var count int32
	fmt.Sscanf(val, "%d", &count)
	return count, nil
}

func (r *redisQuotaRepo) ResetDailyUsage(ctx context.Context, userID uint64) error {
	key := r.key(userID)
	return r.rdb.Del(ctx, key).Err()
}
```

### Step 4: 编写 usecase 测试

Create `backend/internal/biz/usecase/quota_test.go`:

```go
package usecase

import (
	"context"
	"testing"

	"homework_ai2easy/backend/internal/pkg/errors"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/stretchr/testify/assert"
)

func TestQuotaUsecase_CheckAndConsume(t *testing.T) {
	ctx := context.Background()
	uc := NewQuotaUsecase(
		NewMockQuotaRepo(0), // 使用量为 0
		3,                   // 每日 3 题免费
		log.DefaultLogger,
	)

	// 第 1 次：成功
	remaining, err := uc.CheckAndConsume(ctx, 1)
	assert.NoError(t, err)
	assert.Equal(t, int32(2), remaining) // 3-1=2

	// 第 2 次：成功
	remaining, err = uc.CheckAndConsume(ctx, 1)
	assert.NoError(t, err)
	assert.Equal(t, int32(1), remaining)

	// 第 3 次：成功
	remaining, err = uc.CheckAndConsume(ctx, 1)
	assert.NoError(t, err)
	assert.Equal(t, int32(0), remaining)

	// 第 4 次：超额
	_, err = uc.CheckAndConsume(ctx, 1)
	assert.True(t, errors.IsDailyQuotaExceeded(err))
}

func TestQuotaUsecase_GetRemainingQuota(t *testing.T) {
	ctx := context.Background()
	uc := NewQuotaUsecase(
		NewMockQuotaRepo(2), // 已使用 2
		3,
		log.DefaultLogger,
	)
	remaining, err := uc.GetRemainingQuota(ctx, 1)
	assert.NoError(t, err)
	assert.Equal(t, int32(1), remaining)
}

// MockQuotaRepo 测试用 mock
type MockQuotaRepo struct {
	currentUsage int32
}

func NewMockQuotaRepo(initialUsage int32) *MockQuotaRepo {
	return &MockQuotaRepo{currentUsage: initialUsage}
}

func (m *MockQuotaRepo) IncrementDailyUsage(ctx context.Context, userID uint64) (int32, error) {
	m.currentUsage++
	return m.currentUsage, nil
}

func (m *MockQuotaRepo) GetDailyUsage(ctx context.Context, userID uint64) (int32, error) {
	return m.currentUsage, nil
}

func (m *MockQuotaRepo) ResetDailyUsage(ctx context.Context, userID uint64) error {
	m.currentUsage = 0
	return nil
}
```

### Step 5: 实现 usecase

Create `backend/internal/biz/usecase/quota.go`:

```go
package usecase

import (
	"context"

	"homework_ai2easy/backend/internal/data/repository"
	"homework_ai2easy/backend/internal/pkg/errors"

	"github.com/go-kratos/kratos/v2/log"
)

// QuotaUsecase 每日免费额度管理
type QuotaUsecase struct {
	quotaRepo  repository.QuotaRepository
	dailyLimit int32
	log        *log.Helper
}

// NewQuotaUsecase 创建额度用例
func NewQuotaUsecase(
	quotaRepo repository.QuotaRepository,
	dailyLimit int32,
	logger log.Logger,
) *QuotaUsecase {
	return &QuotaUsecase{
		quotaRepo:  quotaRepo,
		dailyLimit: dailyLimit,
		log:        log.NewHelper(logger),
	}
}

// CheckAndConsume 检查并消费一次免费额度；返回剩余额度
func (uc *QuotaUsecase) CheckAndConsume(ctx context.Context, userID uint64) (remaining int32, err error) {
	current, err := uc.quotaRepo.GetDailyUsage(ctx, userID)
	if err != nil {
		return 0, err
	}
	if current >= uc.dailyLimit {
		return 0, errors.DailyQuotaExceeded(uc.dailyLimit)
	}
	newCount, err := uc.quotaRepo.IncrementDailyUsage(ctx, userID)
	if err != nil {
		return 0, err
	}
	remaining = uc.dailyLimit - newCount
	if remaining < 0 {
		remaining = 0
	}
	uc.log.Context(ctx).Infof("daily quota consumed, user=%d, used=%d, remaining=%d", userID, newCount, remaining)
	return remaining, nil
}

// GetRemainingQuota 获取剩余额度
func (uc *QuotaUsecase) GetRemainingQuota(ctx context.Context, userID uint64) (int32, error) {
	current, err := uc.quotaRepo.GetDailyUsage(ctx, userID)
	if err != nil {
		return 0, err
	}
	remaining := uc.dailyLimit - current
	if remaining < 0 {
		remaining = 0
	}
	return remaining, nil
}

// IsSubscribed 检查用户是否已订阅（用于跳过额度检查）
// 当前为 false，后续对接真实订阅系统后替换
func (uc *QuotaUsecase) IsSubscribed(ctx context.Context, userID uint64) bool {
	// TODO: 对接订阅系统后替换
	return false
}
```

### Step 6: 更新 proto 定义

Modify `backend/api/user/v1/user.proto`, add before the closing brace of the service:

```proto
  // 获取每日剩余额度
  rpc GetDailyQuota (GetDailyQuotaRequest) returns (GetDailyQuotaReply) {
    option (google.api.http) = {
      get: "/api/v1/user/quota"
    };
  }
```

Add message definitions:

```proto
// 获取每日剩余额度请求
message GetDailyQuotaRequest {
}

// 获取每日剩余额度响应
message GetDailyQuotaReply {
  int32 code = 1;
  string message = 2;
  DailyQuotaData data = 3;
}

message DailyQuotaData {
  int32 remaining = 1;   // 当日剩余额度
  int32 daily_limit = 2; // 每日免费额度上限
  int32 used = 3;        // 当日已使用量
}
```

### Step 7: 实现 service 层

Modify `backend/internal/service/grpc/user_service.go`, add method:

```go
func (s *UserService) GetDailyQuota(ctx context.Context, req *v1.GetDailyQuotaRequest) (*v1.GetDailyQuotaReply, error) {
	userID, _ := ctxkey.GetUserID(ctx)
	remaining, err := s.quotaUsecase.GetRemainingQuota(ctx, userID)
	if err != nil {
		return nil, err
	}
	used, _ := s.quotaRepo.GetDailyUsage(ctx, userID)
	return &v1.GetDailyQuotaReply{
		Data: &v1.DailyQuotaData{
			Remaining:  remaining,
			DailyLimit: 3, // 从配置读取
			Used:       used,
		},
	}, nil
}
```

Also update Wire provider in `backend/internal/biz/usecase/provider.go` and `backend/internal/data/provider.go` to wire the new `QuotaUsecase` and `QuotaRepository`.

### Step 8: 在作业识别入口拦截额度

Modify `backend/internal/service/grpc/assignment_service.go` — in the `TriggerScan` or `GenerateContent` method, add quota check:

```go
// 在 TriggerScan 开头添加
func (s *AssignmentService) TriggerScan(...) {
    userID, _ := ctxkey.GetUserID(ctx)
    
    // 检查订阅状态，已订阅用户跳过额度检查
    if !s.quotaUsecase.IsSubscribed(ctx, userID) {
        remaining, err := s.quotaUsecase.CheckAndConsume(ctx, userID)
        if err != nil {
            // 返回额度不足错误
            return nil, err
        }
        // 可选：在响应中告知剩余额度
    }
    // ... 原有逻辑
}
```

### Step 9: 运行测试

```bash
cd backend
go test ./internal/biz/usecase -run TestQuotaUsecase -v
make test-unit
```

### Step 10: Commit

```bash
cd backend
git add internal/data/model/daily_usage.go internal/data/repository/quota_repo.go internal/biz/usecase/quota.go internal/biz/usecase/quota_test.go internal/pkg/errors/quota.go api/user/v1/user.proto internal/service/grpc/user_service.go internal/service/grpc/assignment_service.go
git commit -m "feat(user): add daily free quota model with Redis-backed counter

- 3 free scans per day, resets at midnight
- Redis key: daily_usage:{userId}:{date} with TTL
- New API: GET /api/v1/user/quota
- Quota check intercepts scan/content generation
- Error code 40101 for quota exceeded"
```

---

## Task 3: 奖励系统后端（backend/）

**Files:**
- Create: `backend/internal/data/model/reward.go`
- Create: `backend/internal/data/repository/reward_repo.go`
- Create: `backend/internal/biz/usecase/reward.go`
- Create: `backend/internal/biz/usecase/reward_test.go`
- Modify: `backend/api/user/v1/user.proto`
- Modify: `backend/internal/service/grpc/user_service.go`
- Modify: `backend/internal/biz/usecase/provider.go`
- Modify: `backend/internal/data/provider.go`

### Step 1: 编写测试

Create `backend/internal/biz/usecase/reward_test.go`:

```go
package usecase

import (
	"context"
	"testing"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/stretchr/testify/assert"
	"homework_ai2easy/backend/internal/data/model"
)

func TestRewardUsecase_EarnPoints(t *testing.T) {
	ctx := context.Background()
	repo := NewMockRewardRepo(100) // 初始积分 100
	uc := NewRewardUsecase(repo, log.DefaultLogger)

	// 完成作业 +10
	points, err := uc.EarnPoints(ctx, 1, PointReasonCompleteAssignment, 0)
	assert.NoError(t, err)
	assert.Equal(t, int32(110), points)
}

func TestRewardUsecase_GetRewardSummary(t *testing.T) {
	ctx := context.Background()
	repo := NewMockRewardRepo(1280)
	uc := NewRewardUsecase(repo, log.DefaultLogger)

	summary, err := uc.GetRewardSummary(ctx, 1)
	assert.NoError(t, err)
	assert.Equal(t, int32(1280), summary.Points)
	// 应有默认徽章列表
	assert.Greater(t, len(summary.Badges), 0)
}

func TestRewardUsecase_GetPointHistory(t *testing.T) {
	ctx := context.Background()
	repo := NewMockRewardRepo(100)
	repo.AddHistory(model.PointHistory{
		ID:       1,
		UserID:   1,
		Points:   10,
		Reason:   string(PointReasonCompleteAssignment),
		Balance:  110,
	})
	uc := NewRewardUsecase(repo, log.DefaultLogger)

	history, total, err := uc.GetPointHistory(ctx, 1, 1, 10)
	assert.NoError(t, err)
	assert.Equal(t, int64(1), total)
	assert.Equal(t, int32(10), history[0].Points)
}

// MockRewardRepo 测试用 mock
type MockRewardRepo struct {
	points    int32
	history   []model.PointHistory
	badges    []model.UserBadge
}

func NewMockRewardRepo(initialPoints int32) *MockRewardRepo {
	return &MockRewardRepo{
		points: initialPoints,
		badges: []model.UserBadge{},
	}
}

func (m *MockRewardRepo) AddHistory(h model.PointHistory) {
	m.history = append(m.history, h)
}

func (m *MockRewardRepo) GetPoints(ctx context.Context, userID uint64) (int32, error) {
	return m.points, nil
}

func (m *MockRewardRepo) UpdatePoints(ctx context.Context, userID uint64, delta int32) (int32, error) {
	m.points += delta
	return m.points, nil
}

func (m *MockRewardRepo) AddPointHistory(ctx context.Context, h *model.PointHistory) error {
	m.history = append(m.history, *h)
	return nil
}

func (m *MockRewardRepo) GetPointHistory(ctx context.Context, userID uint64, page, pageSize int) ([]model.PointHistory, int64, error) {
	return m.history, int64(len(m.history)), nil
}

func (m *MockRewardRepo) GetUserBadges(ctx context.Context, userID uint64) ([]model.UserBadge, error) {
	return m.badges, nil
}

func (m *MockRewardRepo) AwardBadge(ctx context.Context, userID uint64, badgeID string) error {
	m.badges = append(m.badges, model.UserBadge{
		UserID:    userID,
		BadgeID:   badgeID,
		AwardedAt: "2026-05-08",
	})
	return nil
}
```

### Step 2: 运行测试确认失败

```bash
cd backend
go test ./internal/biz/usecase -run TestRewardUsecase -v
```

预期：FAIL（文件不存在）。

### Step 3: 定义数据模型

Create `backend/internal/data/model/reward.go`:

```go
package model

import "time"

// PointReason 积分获取原因
type PointReason string

const (
	PointReasonCompleteAssignment PointReason = "complete_assignment"  // 完成一次作业
	PointReasonConsecutiveDays    PointReason = "consecutive_days"     // 连续学习 N 天
	PointReasonHighAccuracy       PointReason = "high_accuracy"        // 正确率 > 90%
	PointReasonShareAchievement   PointReason = "share_achievement"    // 分享成就卡
)

// PointHistory 积分变动记录
type PointHistory struct {
	ID        uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID    uint64    `gorm:"type:bigint unsigned;not null;index" json:"user_id"`
	ChildID   uint64    `gorm:"type:bigint unsigned" json:"child_id"`
	Points    int32     `gorm:"type:int;not null" json:"points"`           // +表示获得，-表示消耗
	Reason    string    `gorm:"type:varchar(50);not null" json:"reason"`   // 变动原因
	Reference string    `gorm:"type:varchar(100)" json:"reference"`        // 关联作业ID等
	Balance   int32     `gorm:"type:int;not null" json:"balance"`          // 变动后余额
	CreatedAt time.Time `json:"created_at"`
}

func (PointHistory) TableName() string {
	return "point_histories"
}

// UserBadge 用户徽章
type UserBadge struct {
	ID        uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID    uint64    `gorm:"type:bigint unsigned;not null;index" json:"user_id"`
	BadgeID   string    `gorm:"type:varchar(50);not null" json:"badge_id"` // 徽章标识
	BadgeName string    `gorm:"type:varchar(50);not null" json:"badge_name"`
	BadgeIcon string    `gorm:"type:varchar(200)" json:"badge_icon"` // 图标 URL/emoji
	AwardedAt string    `gorm:"type:varchar(20)" json:"awarded_at"` // 授予日期
	CreatedAt time.Time `json:"created_at"`
}

func (UserBadge) TableName() string {
	return "user_badges"
}

// RewardSummary 奖励汇总（不映射到表，用于聚合返回）
type RewardSummary struct {
	Points       int32        `json:"points"`
	Badges       []UserBadge  `json:"badges"`
	StreakDays   int32        `json:"streak_days"`     // 连续学习天数
	TotalAssignments int32    `json:"total_assignments"` // 累计完成作业数
}
```

### Step 4: 定义仓储接口

Add to `backend/internal/data/repository/reward_repo.go`:

```go
package repository

import (
	"context"
	"time"

	"homework_ai2easy/backend/internal/data/model"
)

// RewardRepository 奖励系统仓储
type RewardRepository interface {
	// GetPoints 获取用户当前积分
	GetPoints(ctx context.Context, userID uint64) (int32, error)
	// UpdatePoints 更新积分并返回新余额
	UpdatePoints(ctx context.Context, userID uint64, delta int32) (int32, error)
	// AddPointHistory 记录积分变动
	AddPointHistory(ctx context.Context, h *model.PointHistory) error
	// GetPointHistory 获取积分变动历史
	GetPointHistory(ctx context.Context, userID uint64, page, pageSize int) ([]model.PointHistory, int64, error)
	// GetUserBadges 获取用户已授予徽章
	GetUserBadges(ctx context.Context, userID uint64) ([]model.UserBadge, error)
	// AwardBadge 授予徽章
	AwardBadge(ctx context.Context, userID uint64, badgeID string) error
	// GetStreakDays 获取连续学习天数
	GetStreakDays(ctx context.Context, userID uint64) (int32, error)
	// RecordStudyDay 记录今日学习（用于连续天数计算）
	RecordStudyDay(ctx context.Context, userID uint64) error
}

type mysqlRewardRepo struct {
	db *gorm.DB
}

func NewRewardRepository(db *gorm.DB) RewardRepository {
	return &mysqlRewardRepo{db: db}
}

func (r *mysqlRewardRepo) GetPoints(ctx context.Context, userID uint64) (int32, error) {
	var total int32
	r.db.Model(&model.PointHistory{}).
		Where("user_id = ?", userID).
		Select("COALESCE(SUM(points), 0)").
		Scan(&total)
	return total, nil
}

func (r *mysqlRewardRepo) UpdatePoints(ctx context.Context, userID uint64, delta int32) (int32, error) {
	// 先获取当前余额
	current, _ := r.GetPoints(ctx, userID)
	newBalance := current + delta
	
	h := &model.PointHistory{
		UserID:  userID,
		Points:  delta,
		Balance: newBalance,
	}
	if err := r.db.Create(h).Error; err != nil {
		return 0, err
	}
	return newBalance, nil
}

func (r *mysqlRewardRepo) AddPointHistory(ctx context.Context, h *model.PointHistory) error {
	return r.db.Create(h).Error
}

func (r *mysqlRewardRepo) GetPointHistory(ctx context.Context, userID uint64, page, pageSize int) ([]model.PointHistory, int64, error) {
	var history []model.PointHistory
	var total int64
	r.db.Model(&model.PointHistory{}).Where("user_id = ?", userID).Count(&total)
	r.db.Where("user_id = ?", userID).
		Order("created_at DESC").
		Offset((page - 1) * pageSize).
		Limit(pageSize).
		Find(&history)
	return history, total, nil
}

func (r *mysqlRewardRepo) GetUserBadges(ctx context.Context, userID uint64) ([]model.UserBadge, error) {
	var badges []model.UserBadge
	r.db.Where("user_id = ?", userID).Order("awarded_at DESC").Find(&badges)
	return badges, nil
}

func (r *mysqlRewardRepo) AwardBadge(ctx context.Context, userID uint64, badgeID string) error {
	badge := model.UserBadge{
		UserID:    userID,
		BadgeID:   badgeID,
		AwardedAt: time.Now().Format("2006-01-02"),
	}
	return r.db.Create(&badge).Error
}

func (r *mysqlRewardRepo) GetStreakDays(ctx context.Context, userID uint64) (int32, error) {
	// 简化实现：从 Redis 读取连续天数
	// 完整实现需要维护连续日期序列
	var streak int32
	r.db.Raw("SELECT COALESCE(MAX(streak_days), 0) FROM user_stats WHERE user_id = ?", userID).Scan(&streak)
	return streak, nil
}

func (r *mysqlRewardRepo) RecordStudyDay(ctx context.Context, userID uint64) error {
	// 记录今日学习，更新连续天数
	// 简化实现：写入一条记录，实际应由定时任务计算
	return nil
}
```

### Step 5: 实现 usecase

Create `backend/internal/biz/usecase/reward.go`:

```go
package usecase

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"

	"github.com/go-kratos/kratos/v2/log"
)

// RewardUsecase 奖励系统业务逻辑
type RewardUsecase struct {
	rewardRepo repository.RewardRepository
	log        *log.Helper
}

// NewRewardUsecase 创建奖励系统用例
func NewRewardUsecase(
	rewardRepo repository.RewardRepository,
	logger log.Logger,
) *RewardUsecase {
	return &RewardUsecase{
		rewardRepo: rewardRepo,
		log:        log.NewHelper(logger),
	}
}

// EarnPoints 获取积分并自动判定徽章解锁
func (uc *RewardUsecase) EarnPoints(ctx context.Context, userID uint64, reason model.PointReason, childID uint64) (int32, error) {
	var delta int32
	switch reason {
	case model.PointReasonCompleteAssignment:
		delta = 10
	case model.PointReasonConsecutiveDays:
		delta = 5
	case model.PointReasonHighAccuracy:
		delta = 20
	case model.PointReasonShareAchievement:
		delta = 3
	default:
		delta = 1
	}

	newBalance, err := uc.rewardRepo.UpdatePoints(ctx, userID, delta)
	if err != nil {
		return 0, err
	}

	// 记录历史
	_ = uc.rewardRepo.AddPointHistory(ctx, &model.PointHistory{
		UserID:  userID,
		ChildID: childID,
		Points:  delta,
		Reason:  string(reason),
		Balance: newBalance,
	})

	// 检查徽章解锁条件
	uc.checkBadgeUnlocks(ctx, userID, newBalance)

	uc.log.Context(ctx).Infof("points earned, user=%d, reason=%s, delta=%d, balance=%d", userID, reason, delta, newBalance)
	return newBalance, nil
}

// GetRewardSummary 获取奖励汇总
func (uc *RewardUsecase) GetRewardSummary(ctx context.Context, userID uint64) (*model.RewardSummary, error) {
	points, _ := uc.rewardRepo.GetPoints(ctx, userID)
	badges, _ := uc.rewardRepo.GetUserBadges(ctx, userID)
	streakDays, _ := uc.rewardRepo.GetStreakDays(ctx, userID)

	return &model.RewardSummary{
		Points:   points,
		Badges:   badges,
		StreakDays: streakDays,
	}, nil
}

// GetPointHistory 获取积分变动历史
func (uc *RewardUsecase) GetPointHistory(ctx context.Context, userID uint64, page, pageSize int) ([]model.PointHistory, int64, error) {
	return uc.rewardRepo.GetPointHistory(ctx, userID, page, pageSize)
}

// checkBadgeUnlocks 检查并授予徽章
func (uc *RewardUsecase) checkBadgeUnlocks(ctx context.Context, userID uint64, balance int32) {
	badgeDefinitions := []struct {
		id       string
		name     string
		icon     string
		condition int32
	}{
		{"first_step", "迈出第一步", "🎯", 10},
		{"learning_star", "学习之星", "⭐", 50},
		{"learning_master", "学习达人", "🏆", 200},
		{"knowledge_king", "知识王者", "👑", 500},
	}

	existing, _ := uc.rewardRepo.GetUserBadges(ctx, userID)
	existingMap := make(map[string]bool)
	for _, b := range existing {
		existingMap[b.BadgeID] = true
	}

	for _, bd := range badgeDefinitions {
		if !existingMap[bd.id] && balance >= bd.condition {
			_ = uc.rewardRepo.AwardBadge(ctx, userID, bd.id)
			uc.log.Context(ctx).Infof("badge unlocked, user=%d, badge=%s", userID, bd.name)
		}
	}
}

// AwardPointsForAssignment 完成作业时自动发放积分
func (uc *RewardUsecase) AwardPointsForAssignment(ctx context.Context, userID, childID uint64) error {
	_, err := uc.EarnPoints(ctx, userID, model.PointReasonCompleteAssignment, childID)
	return err
}
```

### Step 6: 更新 proto 定义

Modify `backend/api/user/v1/user.proto`, add reward-related messages and RPCs:

```proto
  // 获取奖励汇总
  rpc GetRewardSummary (GetRewardSummaryRequest) returns (GetRewardSummaryReply) {
    option (google.api.http) = {
      get: "/api/v1/user/rewards"
    };
  }

  // 获取积分历史
  rpc GetPointHistory (GetPointHistoryRequest) returns (GetPointHistoryReply) {
    option (google.api.http) = {
      get: "/api/v1/user/points/history"
    };
  }
```

Add messages:

```proto
// 获取奖励汇总
message GetRewardSummaryRequest {}

message GetRewardSummaryReply {
  int32 code = 1;
  string message = 2;
  RewardSummaryData data = 3;
}

message RewardSummaryData {
  int32 points = 1;
  int32 streak_days = 2;
  repeated BadgeData badges = 3;
}

message BadgeData {
  string badge_id = 1;
  string badge_name = 2;
  string badge_icon = 3;
  string awarded_at = 4;
}

// 获取积分历史
message GetPointHistoryRequest {
  int32 page = 1;
  int32 page_size = 2;
}

message GetPointHistoryReply {
  int32 code = 1;
  string message = 2;
  PointHistoryListData data = 3;
}

message PointHistoryListData {
  repeated PointHistoryItem list = 1;
  int64 total = 2;
}

message PointHistoryItem {
  int32 points = 1;
  string reason = 2;
  int32 balance = 3;
  string created_at = 4;
}
```

### Step 7: 实现 service 层

Modify `backend/internal/service/grpc/user_service.go`, add methods for `GetRewardSummary` and `GetPointHistory`. Wire up in `provider.go`.

### Step 8: 在内容生成完成时发放积分

Modify `backend/internal/biz/usecase/assignment_usecase.go` — in `runGenerate`, after successful content generation and story save:

```go
// 在 runGenerate 末尾，故事落库后
uc.rewardRepo.RecordStudyDay(bg, a.UserID) // 记录今日学习
_ = uc.rewardUsecase.AwardPointsForAssignment(bg, a.UserID, a.ChildID)
```

This requires injecting `RewardUsecase` into `AssignmentUsecase`.

### Step 9: 运行测试

```bash
cd backend
go test ./internal/biz/usecase -run TestRewardUsecase -v
make test-unit
```

### Step 10: 运行 `make wire` 并重新生成

```bash
cd backend
make wire
make build
```

### Step 11: Commit

```bash
cd backend
git add internal/data/model/reward.go internal/data/repository/reward_repo.go internal/biz/usecase/reward.go internal/biz/usecase/reward_test.go api/user/v1/user.proto internal/service/grpc/user_service.go internal/biz/usecase/assignment_usecase.go
git commit -m "feat(reward): add points/badges system with MySQL-backed persistence

- point rules: complete assignment +10, streak +5, accuracy>90% +20, share +3
- badge tiers: first_step(10), learning_star(50), learning_master(200), knowledge_king(500)
- APIs: GET /user/rewards, GET /user/points/history
- auto-award points on content generation complete
- auto-unlock badges based on point balance"
```

---

## Task 4: 插图进度可视化优化（app/）

**Files:**
- Modify: `app/frontend/pages/learning/story.uvue`
- Modify: `app/frontend/api/content.ts`

**现状分析**：前端已有插图进度展示基础设施（`imageGenStatus`, `imageGenProgressText`），但存在以下问题：
1. 进度文本格式可能不够直观（"图片生成中{{ imageGenProgressText }}"）
2. 插图生成失败时无明确提示
3. 轮询间隔和超时未明确配置

### Step 1: 增强进度展示 UI

Modify `app/frontend/pages/learning/story.uvue` — find the illustration loading section and enhance:

```vue
<!-- 替换原有的简单 loading 提示为带进度的进度条 -->
<view v-if="imageGenStatus === 'pending' || imageGenStatus === 'processing'" class="illustration-loading">
  <view class="loading-icon">
    <text class="icon-text">🎨</text>
  </view>
  <text class="loading-text">插图正在生成中，请稍候...</text>
  <view class="progress-bar">
    <view class="progress-fill" :style="{ width: imageGenProgress + '%' }"></view>
  </view>
  <text class="progress-text">已完成 {{ imageGenProgress }}%</text>
</view>

<view v-else-if="imageGenStatus === 'failed'" class="illustration-error">
  <text class="error-icon">⚠️</text>
  <text class="error-text">插图生成失败，请稍后重试</text>
  <button class="retry-btn" @click="retryIllustration">重试</button>
</view>
```

Add corresponding styles:

```css
.illustration-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0;
}

.loading-icon {
  margin-bottom: 20rpx;
}

.icon-text {
  font-size: 60rpx;
  animation: spin 2s linear infinite;
}

.loading-text {
  font-size: 28rpx;
  color: #666;
  margin-bottom: 24rpx;
}

.progress-bar {
  width: 80%;
  height: 8rpx;
  background-color: #f0f0f0;
  border-radius: 4rpx;
  overflow: hidden;
  margin-bottom: 12rpx;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 24rpx;
  color: #999;
}

.illustration-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0;
}

.error-icon {
  font-size: 48rpx;
  margin-bottom: 16rpx;
}

.error-text {
  font-size: 28rpx;
  color: #f44336;
  margin-bottom: 24rpx;
}

.retry-btn {
  padding: 16rpx 48rpx;
  background-color: #2196F3;
  color: #fff;
  border-radius: 8rpx;
  font-size: 28rpx;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

### Step 2: 添加插图状态轮询逻辑

Modify `app/frontend/pages/learning/story.uvue` script section, add polling for illustration status:

```typescript
// 插图生成轮询：每 5 秒检查一次状态
let illustrationPollTimer: number | null = null

function startIllustrationPolling(storyId: string) {
  if (illustrationPollTimer) return
  
  illustrationPollTimer = setInterval(async () => {
    try {
      const status = await fetchIllustrationStatus(storyId)
      imageGenStatus.value = status.status
      imageGenProgress.value = status.progress || 0
      imageUrls.value = status.images || []
      
      // 完成或失败时停止轮询
      if (status.status === 'completed' || status.status === 'failed') {
        stopIllustrationPolling()
      }
    } catch (e) {
      console.error('插图状态轮询失败', e)
      // 轮询 10 次仍未完成则判定为超时
      pollCount++
      if (pollCount >= 10) {
        imageGenStatus.value = 'failed'
        stopIllustrationPolling()
      }
    }
  }, 5000)
}

function stopIllustrationPolling() {
  if (illustrationPollTimer) {
    clearInterval(illustrationPollTimer)
    illustrationPollTimer = null
  }
}
```

### Step 3: 在 story 页面 onMounted 时启动轮询

Add to the story page's initialization logic:

```typescript
onMounted(() => {
  // 如果插图状态为 pending 或 processing，启动轮询
  if (imageGenStatus.value === 'pending' || imageGenStatus.value === 'processing') {
    startIllustrationPolling(storyId.value)
  }
})
```

### Step 4: 确认 API 层返回正确状态

Verify `app/frontend/api/content.ts` has the illustration status API. If not, add:

```typescript
export interface IllustrationStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  images: string[]
}

export function fetchIllustrationStatus(storyId: string) {
  return get<IllustrationStatus>(`/api/v1/content/stories/${storyId}/illustration-status`)
}
```

If the backend API doesn't exist yet, this is a backend task — but given the existing `GenerateStatusData` proto message already includes `image_status`, `image_progress`, and `image_urls`, the frontend just needs to map these correctly.

### Step 5: 在 HBuilderX 中验证 UI

Open `app/frontend` in HBuilderX → Run → Run to browser / H5. Navigate to a story page and verify:
1. Loading state shows animated icon + progress bar
2. Progress percentage updates on polling
3. Error state shows retry button
4. Completed state shows illustrations

### Step 6: Commit

```bash
cd app/frontend
git add pages/learning/story.uvue api/content.ts
git commit -m "feat(learning): enhance illustration progress visualization

- animated loading icon with progress bar
- polling every 5s for illustration status
- error state with retry button
- timeout after 10 polls (~50s)"
```

---

## 跨 Task 依赖与执行顺序

```
Task 1 (兴趣绑定) ────────────── 无依赖，可并行
Task 2 (免费额度) ────────────── 无依赖，可并行
Task 3 (奖励系统) ────────────── 依赖 Task 2 的错误码包结构（独立文件，无实际冲突）
Task 4 (插图进度) ────────────── 无依赖，前端纯 UI 改动
```

**推荐执行顺序**：Task 1 → Task 2 → Task 3 → Task 4（按产品优先级）
**并行执行**：Task 1/2/4 可完全并行，Task 3 与 Task 2 共享 `provider.go` 修改但无冲突

## 测试策略

| 层级 | 范围 | 命令 |
|---|---|---|
| agent 单元 | 兴趣匹配、故事生成、mock 兜底 | `cd agent && pytest -v` |
| backend 单元 | 额度用例、奖励用例 | `cd backend && make test-unit` |
| 端到端 | 完整流程：上传→识别→生成→故事展示 | `cd agent && pytest tests/test_e2e_homework_flow.py -v -s` |

## 验收标准

| 验收项 | 标准 |
|---|---|
| 故事标题含兴趣关键词 | "奥特曼的数学奇遇记" ✓ |
| 故事正文含兴趣关键词 | 出现"奥特曼"不少于 3 次 ✓ |
| theme 字段非空 | `theme === "奥特曼"` ✓ |
| 每日 3 题限制 | 第 4 题返回 40101 错误 ✓ |
| 积分增加 | 完成作业后积分 +10 ✓ |
| 徽章自动解锁 | 积分达到阈值自动获得徽章 ✓ |
| 插图进度条 | 动画 + 百分比 + 错误重试 ✓ |
