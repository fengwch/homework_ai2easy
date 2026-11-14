package usecase

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"
	"unicode"

	"github.com/go-kratos/kratos/v2/log"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
	"homework_ai2easy/backend/internal/pkg/aiagent"
)

var (
	ErrAssignmentNotFound       = errors.New("作业不存在")
	ErrNoImagesToScan           = errors.New("作业暂无图片，请先上传")
	ErrScanAlreadyTriggered     = errors.New("作业已在识别中或已完成")
	ErrNoQuestionsToGenerate    = errors.New("作业尚未完成识别，请先完成扫描")
	ErrGenerateAlreadyStarted   = errors.New("内容生成已启动或已完成")
	ErrQuestionNotFound         = errors.New("题目不存在")
	ErrQuestionGenerateStarted  = errors.New("该题内容生成已启动或已完成")
)

// AssignmentUsecase 作业业务用例
type AssignmentUsecase struct {
	assignRepo         repository.AssignmentRepository
	childRepo          repository.ChildRepository
	storyContentRepo   repository.StoryContentRepository
	questionGenRepo    repository.QuestionGenerationRepository
	questionAnswerRepo repository.QuestionAnswerRepository
	aiClient           *aiagent.Client
	log                *log.Helper
}

// StoryContentRepo 暴露 StoryContent 仓储供 service 层读取插图状态
func (uc *AssignmentUsecase) StoryContentRepo() repository.StoryContentRepository {
	return uc.storyContentRepo
}

// NewAssignmentUsecase 创建作业业务用例
func NewAssignmentUsecase(
	assignRepo repository.AssignmentRepository,
	childRepo repository.ChildRepository,
	storyContentRepo repository.StoryContentRepository,
	questionGenRepo repository.QuestionGenerationRepository,
	questionAnswerRepo repository.QuestionAnswerRepository,
	aiClient *aiagent.Client,
	logger log.Logger,
) *AssignmentUsecase {
	return &AssignmentUsecase{
		assignRepo:         assignRepo,
		childRepo:          childRepo,
		storyContentRepo:   storyContentRepo,
		questionGenRepo:    questionGenRepo,
		questionAnswerRepo: questionAnswerRepo,
		aiClient:           aiClient,
		log:                log.NewHelper(logger),
	}
}

// AssignmentListRow 作业列表项（含作答情况）
type AssignmentListRow struct {
	Assignment *model.Assignment
	HasAnswers bool
	Score      *float32
}

// ListAssignments 获取作业列表，校验儿童归属当前用户；childID 为 0 时返回空列表；含 has_answers、score
func (uc *AssignmentUsecase) ListAssignments(ctx context.Context, userID uint64, childID uint64, status, subject string, hasAnswers *bool, page, pageSize int) ([]*AssignmentListRow, int64, error) {
	if childID == 0 {
		return []*AssignmentListRow{}, 0, nil
	}
	child, err := uc.childRepo.FindByID(ctx, childID)
	if err != nil {
		return nil, 0, err
	}
	if child == nil || child.UserID != userID {
		return []*AssignmentListRow{}, 0, nil
	}
	list, total, err := uc.assignRepo.FindByChildIDWithFilters(ctx, childID, status, subject, hasAnswers, page, pageSize)
	if err != nil {
		return nil, 0, err
	}
	if len(list) == 0 {
		return []*AssignmentListRow{}, total, nil
	}

	// 批量获取作答记录
	ids := make([]uint64, 0, len(list))
	for _, a := range list {
		ids = append(ids, a.ID)
	}
	allAnswers, err := uc.questionAnswerRepo.ListByAssignmentIDsAndChild(ctx, ids, childID)
	if err != nil {
		return nil, 0, err
	}
	answersByAssign := make(map[uint64][]*model.QuestionAnswer)
	for _, ans := range allAnswers {
		answersByAssign[ans.AssignmentID] = append(answersByAssign[ans.AssignmentID], ans)
	}

	rows := make([]*AssignmentListRow, 0, len(list))
	for _, a := range list {
		answers := answersByAssign[a.ID]
		hasAnswers := len(answers) > 0
		score := computeScoreFromAnswers(a, answers)
		rows = append(rows, &AssignmentListRow{
			Assignment: a,
			HasAnswers: hasAnswers,
			Score:      score,
		})
	}
	return rows, total, nil
}

// computeScoreFromAnswers 根据作业题目与作答记录计算得分（与 GetAssignmentAnswers 一致）
func computeScoreFromAnswers(a *model.Assignment, answers []*model.QuestionAnswer) *float32 {
	answerMap := make(map[string]*model.QuestionAnswer)
	for _, ans := range answers {
		answerMap[ans.QuestionID] = ans
	}
	var totalScore float32
	var scoredCount int
	for _, q := range a.Questions {
		if q.StructuredData == nil || strings.TrimSpace(q.StructuredData.Answer) == "" {
			continue
		}
		ans, ok := answerMap[q.ID]
		if !ok || ans.IsCorrect == nil {
			continue
		}
		scoredCount++
		if *ans.IsCorrect {
			totalScore += 100
		}
	}
	if scoredCount == 0 {
		return nil
	}
	avg := totalScore / float32(scoredCount)
	return &avg
}

// GetQuestionGenerateStatusMap 获取作业下所有题目的生成状态，key 为 question_id，用于作业详情/识别结果页展示各题生成状态
func (uc *AssignmentUsecase) GetQuestionGenerateStatusMap(ctx context.Context, assignmentID uint64) (map[string]*model.QuestionGenerationStatus, error) {
	list, err := uc.questionGenRepo.ListByAssignmentID(ctx, assignmentID)
	if err != nil {
		return nil, err
	}
	m := make(map[string]*model.QuestionGenerationStatus, len(list))
	for _, s := range list {
		m[s.QuestionID] = s
	}
	return m, nil
}

// GetAssignment 获取作业详情，校验儿童归属当前用户
func (uc *AssignmentUsecase) GetAssignment(ctx context.Context, userID uint64, id uint64) (*model.Assignment, error) {
	a, err := uc.assignRepo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if a == nil {
		return nil, ErrAssignmentNotFound
	}
	child, err := uc.childRepo.FindByID(ctx, a.ChildID)
	if err != nil {
		return nil, err
	}
	if child == nil || child.UserID != userID {
		return nil, ErrAssignmentNotFound
	}
	return a, nil
}

// CreateAssignment 创建作业（可带首张图片 URL），校验儿童归属当前用户。
func (uc *AssignmentUsecase) CreateAssignment(ctx context.Context, userID uint64, childID uint64, imageURL string) (*model.Assignment, error) {
	child, err := uc.childRepo.FindByID(ctx, childID)
	if err != nil {
		return nil, err
	}
	if child == nil || child.UserID != userID {
		return nil, ErrAssignmentNotFound // 无权限或儿童不存在
	}
	a := &model.Assignment{
		ChildID:        childID,
		Subject:        "",
		Status:         "pending",
		OriginalImages: model.StringArray{},
	}
	if imageURL != "" {
		a.OriginalImages = model.StringArray{imageURL}
	}
	if err := uc.assignRepo.Create(ctx, a); err != nil {
		return nil, err
	}
	return a, nil
}

// UpdateAssignmentImages 更新作业的 OriginalImages
func (uc *AssignmentUsecase) UpdateAssignmentImages(ctx context.Context, userID uint64, assignmentID uint64, images model.StringArray) error {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return err
	}
	a.OriginalImages = images
	return uc.assignRepo.Update(ctx, a)
}

// UpdateAssignment 更新作业信息（科目、题目列表、状态等），用于保存 OCR 结果
func (uc *AssignmentUsecase) UpdateAssignment(ctx context.Context, userID uint64, assignmentID uint64, subject string, questions model.Questions, status string) (*model.Assignment, error) {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return nil, err
	}
	if subject != "" {
		a.Subject = subject
	}
	if len(questions) > 0 {
		a.Questions = questions
	}
	if status != "" {
		a.Status = status
	}
	// 识别结果保存时生成/更新作业标题
	a.Title = generateAssignmentTitle(a)
	if err := uc.assignRepo.Update(ctx, a); err != nil {
		return nil, err
	}
	return a, nil
}

// TriggerScan 触发作业扫描识别，校验权限后更新状态为 processing，异步执行 OCR（当前为 mock）。
func (uc *AssignmentUsecase) TriggerScan(ctx context.Context, userID uint64, assignmentID uint64, subject string) (*model.Assignment, error) {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return nil, err
	}
	if len(a.OriginalImages) == 0 {
		return nil, ErrNoImagesToScan
	}
	if a.Status != "pending" {
		return nil, ErrScanAlreadyTriggered
	}
	a.Status = "processing"
	if subject != "" {
		a.Subject = subject
	}
	if err := uc.assignRepo.Update(ctx, a); err != nil {
		return nil, err
	}
	go uc.runOCR(assignmentID, a.Subject, a.OriginalImages)
	return a, nil
}

// runOCR 执行 OCR 识别：若 AI-Agent 已配置则调用，否则使用 mock
func (uc *AssignmentUsecase) runOCR(assignmentID uint64, subject string, images model.StringArray) {
	bg := context.Background()
	var questions model.Questions
	if uc.aiClient != nil && uc.aiClient.IsConfigured() && len(images) > 0 {
		imgPath := images[0]
		qs, err := uc.aiClient.OCRRecognize(bg, imgPath, subject)
		if err != nil {
			uc.log.Warnw("ocr", "assignment_id", assignmentID, "err", err.Error())
			questions = mockQuestions()
		} else {
			questions = qs
		}
	} else {
		time.Sleep(2 * time.Second)
		questions = mockQuestions()
	}
	a, err := uc.assignRepo.FindByID(bg, assignmentID)
	if err != nil || a == nil {
		return
	}
	if a.Status != "processing" {
		return
	}
	a.Status = "completed"
	a.Questions = questions
	a.EstimatedTime = 30
	// 识别完成后生成作业标题
	a.Title = generateAssignmentTitle(a)
	_ = uc.assignRepo.Update(bg, a)
}

// generateAssignmentTitle 根据题目内容与科目生成 8-14 个汉字左右的「主题名」风格标题，不含标点。
func generateAssignmentTitle(a *model.Assignment) string {
	// 优先使用首题的结构化题干或原始文本
	var candidate string
	for _, q := range a.Questions {
		if q.StructuredData.Stem != "" {
			candidate = q.StructuredData.Stem
		} else if q.OriginalText != "" {
			candidate = q.OriginalText
		}
		if candidate != "" {
			break
		}
	}
	// 若没有题目文本，退化为科目 + “作业”
	if candidate == "" {
		if a.Subject != "" {
			candidate = a.Subject + "作业"
		} else {
			candidate = "作业练习"
		}
	}
	// 将科目前置，便于形成“数学分数加减”类似主题
	if a.Subject != "" && !strings.Contains(candidate, a.Subject) {
		candidate = a.Subject + candidate
	}
	candidate = stripPunctuationAndSpace(candidate)
	rs := []rune(candidate)
	if len(rs) > 14 {
		rs = rs[:14]
	}
	if len(rs) >= 8 {
		return string(rs)
	}
	// 太短时，用“科目+练习”兜底
	base := a.Subject
	if base == "" {
		base = "作业练习"
	} else {
		base = base + "练习"
	}
	base = stripPunctuationAndSpace(base)
	brs := []rune(base)
	if len(brs) > 14 {
		brs = brs[:14]
	}
	return string(brs)
}

// stripPunctuationAndSpace 去掉空白与中英文常见标点，保留文字本身。
func stripPunctuationAndSpace(s string) string {
	var b strings.Builder
	for _, r := range s {
		if unicode.IsSpace(r) {
			continue
		}
		switch r {
		case '，', '。', '！', '？', '、', '：', '；', '“', '”', '‘', '’',
			'（', '）', '【', '】', '《', '》',
			',', '.', '!', '?', ':', ';', '"', '\'', '(', ')', '[', ']', '{', '}', '-', '_':
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

func mockQuestions() model.Questions {
	return model.Questions{
		{
			ID:             "q1",
			QuestionNumber: 1,
			QuestionType:   "multiple_choice",
			OriginalText:   "1. 下列哪个数是偶数？\nA. 1  B. 2  C. 3  D. 5",
			StructuredData: &model.StructuredData{
				Stem: "下列哪个数是偶数？",
				Options: []model.Option{
					{Option: "A", Text: "1"},
					{Option: "B", Text: "2"},
					{Option: "C", Text: "3"},
					{Option: "D", Text: "5"},
				},
				Answer:   "B",
				Analysis: "偶数是能被2整除的数，2÷2=1，所以2是偶数。",
			},
		},
	}
}

// TriggerGenerateContent 触发个性化内容生成，校验作业已完成识别，更新 GeneratedContent 为 processing，异步执行（当前为 mock）。
func (uc *AssignmentUsecase) TriggerGenerateContent(ctx context.Context, userID uint64, assignmentID uint64) (*model.Assignment, error) {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return nil, err
	}
	if len(a.Questions) == 0 {
		return nil, ErrNoQuestionsToGenerate
	}
	if a.GeneratedContent != nil {
		switch a.GeneratedContent.Status {
		case "processing", "completed":
			return nil, ErrGenerateAlreadyStarted
		}
	}
	a.GeneratedContent = &model.GeneratedContent{
		StoryID: "",
		Status:  "processing",
	}
	if err := uc.assignRepo.Update(ctx, a); err != nil {
		return nil, err
	}
	go uc.runGenerate(assignmentID)
	return a, nil
}

// runGenerate 执行内容生成：若 AI-Agent 已配置则调用，否则使用 mock；完成后落库 StoryContent
func (uc *AssignmentUsecase) runGenerate(assignmentID uint64) {
	bg := context.Background()
	a, err := uc.assignRepo.FindByID(bg, assignmentID)
	if err != nil || a == nil {
		return
	}
	if a.GeneratedContent == nil || a.GeneratedContent.Status != "processing" {
		return
	}
	child, _ := uc.childRepo.FindByID(bg, a.ChildID)
	storyID := fmt.Sprintf("story-%d", assignmentID)
	var title, summary, story, theme string
	var questionsForStory []interface{}
	var interests []string

	if uc.aiClient != nil && uc.aiClient.IsConfigured() && child != nil {
		interests = append([]string{}, child.Interests...)
		interests = append(interests, child.CustomInterests...)
		req := aiagent.ContentGenerateRequest{
			AssignmentID: fmt.Sprintf("%d", assignmentID),
			ChildProfile: aiagent.ChildProfile{
				Name:      child.Name,
				Grade:     child.Grade,
				Interests: interests,
			},
			Questions: questionsToContentQuestions(a.Questions),
			Subject:   a.Subject,
		}
		resp, err := uc.aiClient.ContentGenerate(bg, req)
		if err != nil {
			uc.log.Warnw("content_generate", "assignment_id", assignmentID, "err", err.Error())
		} else {
			storyID = resp.StoryID
			title = resp.Title
			summary = resp.Summary
			story = resp.Story
			theme = resp.Theme
			questionsForStory = resp.Questions
		}
	}
	if title == "" {
		time.Sleep(3 * time.Second)
		title = "小明的数学奇遇记"
		summary = "基于你的作业题目生成的个性化学习故事，帮助巩固「偶数的认识」等知识点。"
		story = mockStoryContent()
		theme = ""
		questionsForStory = questionsToInterfaces(mockQuestions())
	}
	// 落库 StoryContent（若将触发插图生成则先置 illustration_status=pending，progress≈10）
	illustrationStatus := ""
	illustrationProgress := int32(0)
	if strings.TrimSpace(story) != "" && uc.aiClient != nil && uc.aiClient.IsConfigured() {
		illustrationStatus = "pending"
		illustrationProgress = 10
	}
	_ = uc.storyContentRepo.Create(bg, &model.StoryContent{
		StoryID:              storyID,
		AssignmentID:         assignmentID,
		Title:                title,
		Summary:              summary,
		Story:                story,
		Questions:            model.StoryQuestions(questionsForStory),
		Theme:                theme,
		IllustrationStatus:   illustrationStatus,
		IllustrationProgress: illustrationProgress,
	})

	// 异步生成插图：仅用落库的 story 全文作为 illustration_prompts，不拆成多条
	if strings.TrimSpace(story) != "" && uc.aiClient != nil && uc.aiClient.IsConfigured() {
		go uc.runIllustration(bg, assignmentID, storyID, story, interests)
	}

	a, _ = uc.assignRepo.FindByID(bg, assignmentID)
	if a != nil && a.GeneratedContent != nil && a.GeneratedContent.Status == "processing" {
		a.GeneratedContent = &model.GeneratedContent{StoryID: storyID, Status: "completed"}
		_ = uc.assignRepo.Update(bg, a)
	}
}

// TriggerQuestionGenerateContent 触发单题个性化内容生成（2.4.3）
func (uc *AssignmentUsecase) TriggerQuestionGenerateContent(ctx context.Context, userID uint64, assignmentID uint64, questionID string) (*model.QuestionGenerationStatus, error) {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return nil, err
	}
	var targetQ *model.Question
	for i := range a.Questions {
		if a.Questions[i].ID == questionID {
			targetQ = &a.Questions[i]
			break
		}
	}
	if targetQ == nil {
		return nil, ErrQuestionNotFound
	}
	exist, _ := uc.questionGenRepo.FindByAssignmentQuestion(ctx, assignmentID, questionID)
	if exist != nil {
		switch exist.Status {
		case "processing", "completed":
			return nil, ErrQuestionGenerateStarted
		}
	}
	s := &model.QuestionGenerationStatus{
		AssignmentID: assignmentID,
		QuestionID:   questionID,
		Status:       "processing",
	}
	if exist != nil {
		exist.Status = "processing"
		exist.StoryID = ""
		if err := uc.questionGenRepo.Update(ctx, exist); err != nil {
			return nil, err
		}
		s = exist
	} else if err := uc.questionGenRepo.Create(ctx, s); err != nil {
		return nil, err
	}
	go uc.runQuestionGenerate(assignmentID, questionID, targetQ, a.Subject, a.ChildID)
	return s, nil
}

func (uc *AssignmentUsecase) runQuestionGenerate(assignmentID uint64, questionID string, q *model.Question, subject string, childID uint64) {
	bg := context.Background()
	storyID := fmt.Sprintf("story-%d-%s", assignmentID, questionID)
	var title, summary, story, theme string
	var questionsForStory []interface{}
	var interests []string

	child, _ := uc.childRepo.FindByID(bg, childID)
	if uc.aiClient != nil && uc.aiClient.IsConfigured() && child != nil {
		interests = append([]string{}, child.Interests...)
		interests = append(interests, child.CustomInterests...)
		req := aiagent.ContentGenerateRequest{
			AssignmentID: fmt.Sprintf("%d", assignmentID),
			ChildProfile: aiagent.ChildProfile{
				Name:      child.Name,
				Grade:     child.Grade,
				Interests: interests,
			},
			Questions: []aiagent.ContentQuestion{{
				ID:           q.ID,
				QuestionType: q.QuestionType,
				OriginalText: q.OriginalText,
			}},
			Subject: subject,
		}
		resp, err := uc.aiClient.ContentGenerate(bg, req)
		if err != nil {
			uc.log.Warnw("question_content_generate", "assignment_id", assignmentID, "question_id", questionID, "err", err.Error())
		} else {
			storyID = resp.StoryID
			title = resp.Title
			summary = resp.Summary
			story = resp.Story
			theme = resp.Theme
			questionsForStory = resp.Questions
		}
	}
	if title == "" {
		time.Sleep(3 * time.Second)
		title = "单题学习故事"
		summary = "基于该题生成的个性化学习内容"
		story = mockStoryContent()
		theme = ""
		questionsForStory = questionsToInterfaces(model.Questions{*q})
	}
	illustrationStatus := ""
	if strings.TrimSpace(story) != "" && uc.aiClient != nil && uc.aiClient.IsConfigured() {
		illustrationStatus = "pending"
	}
	_ = uc.storyContentRepo.Create(bg, &model.StoryContent{
		StoryID:             storyID,
		AssignmentID:        assignmentID,
		QuestionID:          questionID,
		Title:               title,
		Summary:             summary,
		Story:               story,
		Questions:           model.StoryQuestions(questionsForStory),
		Theme:               theme,
		IllustrationStatus:  illustrationStatus,
	})

	// 单题故事插图生成（异步）：仅用落库的 story 全文作为 illustration_prompts
	if strings.TrimSpace(story) != "" && uc.aiClient != nil && uc.aiClient.IsConfigured() {
		go uc.runIllustration(bg, assignmentID, storyID, story, interests)
	}
	sts, _ := uc.questionGenRepo.FindByAssignmentQuestion(bg, assignmentID, questionID)
	if sts != nil && sts.Status == "processing" {
		sts.Status = "completed"
		sts.StoryID = storyID
		_ = uc.questionGenRepo.Update(bg, sts)
	}
}

// runIllustration 调用 AI-Agent 生成插图，并上报状态与结果到 StoryContent。
// storyText 为 story_contents 表的 story 字段（整段故事正文），作为 illustration_prompts 的唯一元素。
func (uc *AssignmentUsecase) runIllustration(ctx context.Context, assignmentID uint64, storyID string, storyText string, interests []string) {
	if uc.aiClient == nil || !uc.aiClient.IsConfigured() {
		return
	}
	if strings.TrimSpace(storyText) == "" || storyID == "" {
		return
	}
	_ = uc.storyContentRepo.UpdateIllustrationStatus(ctx, storyID, "processing", nil)
	req := aiagent.IllustrateRequest{
		IllustrationPrompts: []string{strings.TrimSpace(storyText)},
		Interests:           interests,
	}
	resp, err := uc.aiClient.ContentIllustrate(ctx, req)
	if err != nil {
		uc.log.Warnw("content_illustrate", "assignment_id", assignmentID, "story_id", storyID, "err", err.Error())
		_ = uc.storyContentRepo.UpdateIllustrationStatus(ctx, storyID, "failed", nil)
		return
	}
	var images model.StringArray
	for _, item := range resp.Items {
		for _, img := range item.Images {
			if strings.TrimSpace(img) == "" {
				continue
			}
			images = append(images, img)
		}
	}
	_ = uc.storyContentRepo.UpdateIllustrationStatus(ctx, storyID, "completed", images)
}

// GetQuestionGenerateStatus 获取单题内容生成状态
func (uc *AssignmentUsecase) GetQuestionGenerateStatus(ctx context.Context, userID uint64, assignmentID uint64, questionID string) (*model.QuestionGenerationStatus, error) {
	if _, err := uc.GetAssignment(ctx, userID, assignmentID); err != nil {
		return nil, err
	}
	return uc.questionGenRepo.FindByAssignmentQuestion(ctx, assignmentID, questionID)
}

// AnswerQuestionItem 批改页单题作答信息
type AnswerQuestionItem struct {
	QuestionID        string
	QuestionText      string
	UserAnswer        string
	CorrectAnswer     string // 无标准答案时为空
	IsCorrect         *bool  // 无标准答案时为 nil
	Analysis          string
	HasStandardAnswer bool
}

// AssignmentAnswersResult 批改页作答汇总
type AssignmentAnswersResult struct {
	AssignmentID    uint64
	Questions       []AnswerQuestionItem
	Score           *float32 // 无标准答案题目时 nil
	TotalQuestions  int
	CorrectCount    int
	WrongCount      int
	CorrectRate     int // 0-100
}

// GetAssignmentAnswers 获取作业答题记录（批改页），需校验用户权限
func (uc *AssignmentUsecase) GetAssignmentAnswers(ctx context.Context, userID uint64, assignmentID uint64) (*AssignmentAnswersResult, error) {
	a, err := uc.GetAssignment(ctx, userID, assignmentID)
	if err != nil {
		return nil, err
	}

	answers, err := uc.questionAnswerRepo.ListByAssignmentAndChild(ctx, assignmentID, a.ChildID)
	if err != nil {
		return nil, err
	}

	answerMap := make(map[string]*model.QuestionAnswer)
	for _, ans := range answers {
		answerMap[ans.QuestionID] = ans
	}

	questions := make([]AnswerQuestionItem, 0)
	var correctCount, wrongCount int
	var totalScore float32
	var scoredCount int

	for _, q := range a.Questions {
		item := AnswerQuestionItem{
			QuestionID:   q.ID,
			QuestionText: q.OriginalText,
			UserAnswer:   "",
		}
		if q.StructuredData != nil {
			if q.StructuredData.Stem != "" {
				item.QuestionText = q.StructuredData.Stem
			}
			item.CorrectAnswer = q.StructuredData.Answer
			item.Analysis = q.StructuredData.Analysis
			item.HasStandardAnswer = strings.TrimSpace(q.StructuredData.Answer) != ""
		}

		if ans, ok := answerMap[q.ID]; ok {
			item.UserAnswer = ans.UserAnswer
			item.IsCorrect = ans.IsCorrect
			if ans.IsCorrect != nil {
				if *ans.IsCorrect {
					correctCount++
					totalScore += 100
				} else {
					wrongCount++
				}
				scoredCount++
			}
		}

		questions = append(questions, item)
	}

	result := &AssignmentAnswersResult{
		AssignmentID:   assignmentID,
		Questions:      questions,
		TotalQuestions: len(questions),
		CorrectCount:   correctCount,
		WrongCount:     wrongCount,
	}

	if scoredCount > 0 {
		rate := float32(correctCount) / float32(scoredCount) * 100
		result.CorrectRate = int(rate)
		avgScore := totalScore / float32(scoredCount)
		result.Score = &avgScore
	}

	return result, nil
}

func questionsToContentQuestions(qs model.Questions) []aiagent.ContentQuestion {
	out := make([]aiagent.ContentQuestion, 0, len(qs))
	for _, q := range qs {
		out = append(out, aiagent.ContentQuestion{
			ID:           q.ID,
			QuestionType: q.QuestionType,
			OriginalText: q.OriginalText,
		})
	}
	return out
}

func questionsToInterfaces(qs model.Questions) []interface{} {
	out := make([]interface{}, 0, len(qs))
	for _, q := range qs {
		m := map[string]interface{}{"id": q.ID, "questionNumber": q.QuestionNumber}
		if q.StructuredData != nil {
			m["content"] = q.StructuredData.Stem
			m["options"] = formatOptions(q.StructuredData.Options)
			m["answer"] = q.StructuredData.Answer
			m["analysis"] = q.StructuredData.Analysis
		}
		out = append(out, m)
	}
	return out
}

func formatOptions(opts []model.Option) []string {
	s := make([]string, 0, len(opts))
	for _, o := range opts {
		s = append(s, o.Option+". "+o.Text)
	}
	return s
}

func mockStoryContent() string {
	return `第一章 偶数的秘密

小明在做数学题时遇到了难题：「下列哪个数是偶数？A.1 B.2 C.3 D.5」

他想了想，偶数是能被2整除的数。1÷2除不尽，3÷2除不尽，5÷2也除不尽。只有2÷2=1，所以2是偶数！

小明选对了答案B，开心地继续学习了。

---

【学习要点】
• 偶数的定义：能被2整除的整数
• 常见偶数：2、4、6、8、10...
• 奇偶性判断：看个位数字，0、2、4、6、8为偶`
}
