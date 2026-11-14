package usecase

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
	"homework_ai2easy/backend/internal/pkg/aiagent"
)

var (
	ErrStoryNotFound = errors.New("学习内容不存在")
	// ErrQuestionNotFound 定义在 assignment_usecase.go 中
)

// ContentUsecase 学习内容业务用例
type ContentUsecase struct {
	storyRepo          repository.StoryContentRepository
	assignmentRepo     repository.AssignmentRepository
	questionAnswerRepo repository.QuestionAnswerRepository
	voiceTaskRepo      repository.VoiceTaskRepository
	voiceCacheRepo     repository.VoiceCacheRepository
	aiClient           *aiagent.Client
}

// NewContentUsecase 创建学习内容业务用例
func NewContentUsecase(
	storyRepo repository.StoryContentRepository,
	assignmentRepo repository.AssignmentRepository,
	questionAnswerRepo repository.QuestionAnswerRepository,
	voiceTaskRepo repository.VoiceTaskRepository,
	voiceCacheRepo repository.VoiceCacheRepository,
	aiClient *aiagent.Client,
) *ContentUsecase {
	return &ContentUsecase{
		storyRepo:          storyRepo,
		assignmentRepo:     assignmentRepo,
		questionAnswerRepo: questionAnswerRepo,
		voiceTaskRepo:      voiceTaskRepo,
		voiceCacheRepo:     voiceCacheRepo,
		aiClient:           aiClient,
	}
}

// GetStoryContent 根据 storyID 获取故事内容，不存在返回 nil
func (uc *ContentUsecase) GetStoryContent(ctx context.Context, storyID string) (*model.StoryContent, error) {
	return uc.storyRepo.FindByStoryID(ctx, storyID)
}

// GetSolutionGuide 获取解题引导，若 AI-Agent 未配置则返回 mock
func (uc *ContentUsecase) GetSolutionGuide(ctx context.Context, req aiagent.SolutionGuideRequest) (*aiagent.SolutionGuideResponse, error) {
	if uc.aiClient != nil && uc.aiClient.IsConfigured() {
		resp, err := uc.aiClient.SolutionGuide(ctx, req)
		if err == nil {
			return resp, nil
		}
	}
	// 回退 mock
	return &aiagent.SolutionGuideResponse{
		Theme: "数学",
		Steps: []aiagent.SolutionGuideStep{
			{Order: 1, Text: "仔细阅读题目，理解题目在问什么"},
			{Order: 2, Text: "回忆相关知识点，如偶数的定义"},
			{Order: 3, Text: "逐项分析选项，排除错误答案"},
			{Order: 4, Text: "选出正确答案并验证"},
		},
		FullText: "第一步：仔细阅读题目。第二步：回忆偶数的定义。第三步：逐项分析选项。第四步：选出正确答案。",
	}, nil
}

// SubmitVoiceTask 提交语音合成任务（异步），立即返回 task_id；后台调用 TTS 并更新任务状态
func (uc *ContentUsecase) SubmitVoiceTask(ctx context.Context, text, voice, format string) (taskID string, err error) {
	if uc.aiClient == nil || !uc.aiClient.IsConfigured() {
		return "", aiagent.ErrNotConfigured
	}
	if text == "" {
		return "", errors.New("text 必填")
	}
	taskID = "voice-" + uuid.New().String()
	if err := uc.voiceTaskRepo.SetTask(ctx, taskID, &repository.VoiceTaskState{Status: "pending"}); err != nil {
		return "", err
	}
	// 异步执行 TTS，不阻塞请求
	go uc.runVoiceTask(context.Background(), taskID, text, voice, format)
	return taskID, nil
}

// runVoiceTask 在后台执行 TTS 并更新 Redis 状态；相同 text+voice+format 优先走缓存
func (uc *ContentUsecase) runVoiceTask(ctx context.Context, taskID, text, voice, format string) {
	cacheKey := voiceCacheKey(text, voice, format)
	if cached, ok, _ := uc.voiceCacheRepo.Get(ctx, cacheKey); ok && cached != nil && cached.Status == "completed" {
		_ = uc.voiceTaskRepo.SetTask(ctx, taskID, &repository.VoiceTaskState{
			Status:    "completed",
			AudioData: cached.AudioData,
			Format:    cached.Format,
		})
		return
	}
	_ = uc.voiceTaskRepo.SetTask(ctx, taskID, &repository.VoiceTaskState{Status: "processing"})
	resp, err := uc.aiClient.VoiceSynthesize(ctx, aiagent.VoiceSynthesizeRequest{
		Text:   text,
		Voice:  voice,
		Format: format,
	})
	if err != nil {
		_ = uc.voiceTaskRepo.SetTask(ctx, taskID, &repository.VoiceTaskState{
			Status:  "failed",
			Message: err.Error(),
		})
		return
	}
	state := &repository.VoiceTaskState{
		Status:    "completed",
		AudioData: resp.AudioData,
		Format:    resp.Format,
	}
	_ = uc.voiceCacheRepo.Set(ctx, cacheKey, state)
	_ = uc.voiceTaskRepo.SetTask(ctx, taskID, state)
}

// voiceCacheKey 根据 text+voice+format 生成缓存 key，相同内容复用同一缓存
func voiceCacheKey(text, voice, format string) string {
	h := sha256.Sum256([]byte(text + "|" + voice + "|" + format))
	return hex.EncodeToString(h[:])
}

// GetVoiceTaskStatus 查询语音合成任务状态，用于轮询；任务不存在时 found=false
func (uc *ContentUsecase) GetVoiceTaskStatus(ctx context.Context, taskID string) (*repository.VoiceTaskState, bool, error) {
	return uc.voiceTaskRepo.GetTask(ctx, taskID)
}

// SubmitAnswerResult 答题结果
type SubmitAnswerResult struct {
	IsCorrect bool   // 是否正确
	Feedback  string // 反馈文案
}

// SubmitAnswer 提交答案并判定正误，同时持久化到数据库供批改页查看。
// 当 storyID 非空时从故事内容定位题目；当 storyID 为空且 assignmentID > 0 时直接从作业题目答题（无需先生成故事）。
func (uc *ContentUsecase) SubmitAnswer(ctx context.Context, storyID string, assignmentID uint64, questionID, userAnswer string) (*SubmitAnswerResult, error) {
	var assignment *model.Assignment
	var question *storyQuestion

	if storyID != "" {
		// 1. 有故事ID：从 story content 获取作业与题目
		sc, err := uc.storyRepo.FindByStoryID(ctx, storyID)
		if err != nil {
			return nil, err
		}
		if sc == nil {
			return nil, ErrStoryNotFound
		}
		var errA error
		assignment, errA = uc.assignmentRepo.FindByID(ctx, sc.AssignmentID)
		if errA != nil || assignment == nil {
			return nil, ErrStoryNotFound
		}
		var errQ error
		question, errQ = findQuestionFromStoryContent(sc.Questions, questionID)
		if errQ != nil {
			return nil, errQ
		}
	} else if assignmentID > 0 {
		// 2. 无故事ID：直接用作业ID 获取作业与题目（无需生成内容即可答题）
		var err error
		assignment, err = uc.assignmentRepo.FindByID(ctx, assignmentID)
		if err != nil || assignment == nil {
			return nil, ErrStoryNotFound
		}
		question = findQuestionFromAssignment(assignment.Questions, questionID)
		if question == nil {
			return nil, ErrQuestionNotFound
		}
	} else {
		return nil, errors.New("story_id 与 assignment_id 至少传其一")
	}

	var isCorrect bool
	var feedback string
	var isCorrectPtr *bool

	correctAnswer := strings.TrimSpace(question.Answer)
	if correctAnswer == "" {
		feedback = "回答完毕，需要人为确认是否正确。"
		isCorrect = false
	} else {
		userAnswerNorm := strings.TrimSpace(strings.ToUpper(userAnswer))
		correctAnswerNorm := strings.ToUpper(correctAnswer)
		isCorrect = userAnswerNorm == correctAnswerNorm
		isCorrectPtr = &isCorrect
		feedback = generateFeedback(isCorrect, question)
	}

	ans := &model.QuestionAnswer{
		AssignmentID: assignment.ID,
		QuestionID:   questionID,
		ChildID:      assignment.ChildID,
		UserAnswer:   strings.TrimSpace(userAnswer),
		IsCorrect:    isCorrectPtr,
	}
	if err := uc.questionAnswerRepo.SaveOrUpdate(ctx, ans); err != nil {
		return nil, err
	}

	return &SubmitAnswerResult{
		IsCorrect: isCorrect,
		Feedback:  feedback,
	}, nil
}

// findQuestionFromAssignment 从作业的 Questions 中查找题目（用于无故事时直接答题）
func findQuestionFromAssignment(questions model.Questions, questionID string) *storyQuestion {
	for _, q := range questions {
		if q.ID != questionID {
			continue
		}
		sq := &storyQuestion{ID: q.ID, QuestionNumber: int(q.QuestionNumber)}
		if q.StructuredData != nil {
			sq.Answer = q.StructuredData.Answer
			sq.Analysis = q.StructuredData.Analysis
			sq.Content = q.StructuredData.Stem
			if len(q.StructuredData.Options) > 0 {
				for _, o := range q.StructuredData.Options {
					sq.Options = append(sq.Options, o.Option+". "+o.Text)
				}
			}
		}
		return sq
	}
	return nil
}

// storyQuestion 用于解析 story_content.questions 中的题目数据
type storyQuestion struct {
	ID             string   `json:"id"`
	QuestionNumber int      `json:"questionNumber"`
	Content        string   `json:"content"`
	Options        []string `json:"options"`
	Answer         string   `json:"answer"`
	Analysis       string   `json:"analysis"`
}

// findQuestionFromStoryContent 从 StoryQuestions 中查找指定 ID 的题目
func findQuestionFromStoryContent(questions model.StoryQuestions, questionID string) (*storyQuestion, error) {
	for _, q := range questions {
		qMap, ok := q.(map[string]interface{})
		if !ok {
			continue
		}
		id, _ := qMap["id"].(string)
		if id == questionID {
			sq := &storyQuestion{
				ID: id,
			}
			if num, ok := qMap["questionNumber"].(float64); ok {
				sq.QuestionNumber = int(num)
			}
			if content, ok := qMap["content"].(string); ok {
				sq.Content = content
			}
			if options, ok := qMap["options"].([]interface{}); ok {
				for _, opt := range options {
					if s, ok := opt.(string); ok {
						sq.Options = append(sq.Options, s)
					}
				}
			}
			if answer, ok := qMap["answer"].(string); ok {
				sq.Answer = answer
			}
			if analysis, ok := qMap["analysis"].(string); ok {
				sq.Analysis = analysis
			}
			return sq, nil
		}
	}
	return nil, ErrQuestionNotFound
}

// generateFeedback 生成答题反馈
func generateFeedback(isCorrect bool, q *storyQuestion) string {
	if isCorrect {
		// 正确反馈
		if q.Analysis != "" {
			return fmt.Sprintf("回答正确！%s", q.Analysis)
		}
		return "回答正确！继续保持！"
	}
	// 错误反馈
	if q.Analysis != "" {
		return fmt.Sprintf("回答错误。正确答案是 %s。%s", q.Answer, q.Analysis)
	}
	return fmt.Sprintf("回答错误。正确答案是 %s。", q.Answer)
}
