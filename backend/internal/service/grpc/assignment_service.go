package grpcService

import (
	"context"
	"fmt"
	"time"

	"github.com/go-kratos/kratos/v2/log"

	v1 "homework_ai2easy/backend/api/assignment/v1"
	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/pkg/ctxkey"
	"homework_ai2easy/backend/internal/pkg/upload"
)

var _ v1.AssignmentServiceServer = (*AssignmentService)(nil)
var _ v1.AssignmentServiceHTTPServer = (*AssignmentService)(nil)

// AssignmentService 作业服务
type AssignmentService struct {
	v1.UnimplementedAssignmentServiceServer
	uc     *usecase.AssignmentUsecase
	store  *upload.LocalStore
	log    *log.Helper
}

// NewAssignmentService 创建作业服务
func NewAssignmentService(uc *usecase.AssignmentUsecase, logger log.Logger) *AssignmentService {
	return &AssignmentService{
		uc:    uc,
		store: upload.NewLocalStore(""),
		log:   log.NewHelper(logger),
	}
}

func (s *AssignmentService) userID(ctx context.Context) (uint64, int32, string) {
	userID, ok := ctxkey.UserIDFromContext(ctx)
	if !ok {
		return 0, 401, "未登录或登录已过期"
	}
	return userID, 0, ""
}

func (s *AssignmentService) ListAssignments(ctx context.Context, req *v1.ListAssignmentsRequest) (*v1.ListAssignmentsReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.ListAssignmentsReply{Code: code, Message: msg}, nil
	}
	page, pageSize := int(req.GetPage()), int(req.GetPageSize())
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	rows, total, err := s.uc.ListAssignments(ctx, userID, uint64(req.GetChildId()), req.GetStatus(), req.GetSubject(), req.HasAnswers, page, pageSize)
	if err != nil {
		return &v1.ListAssignmentsReply{Code: 500, Message: err.Error()}, nil
	}
	items := make([]*v1.AssignmentListItem, 0, len(rows))
	for _, row := range rows {
		a := row.Assignment
		item := &v1.AssignmentListItem{
			Id:         int64(a.ID),
			ChildId:    int64(a.ChildID),
			Subject:    a.Subject,
			Title:      a.Title,
			Status:     a.Status,
			CreatedAt:  formatTimeUser(a.CreatedAt),
			HasAnswers: row.HasAnswers,
		}
		if row.Score != nil {
			item.Score = row.Score
		}
		items = append(items, item)
	}
	return &v1.ListAssignmentsReply{
		Code:    0,
		Message: "success",
		Data: &v1.ListAssignmentsData{
			List:     items,
			Total:    total,
			Page:     int32(page),
			PageSize: int32(pageSize),
		},
	}, nil
}

func (s *AssignmentService) GetAssignment(ctx context.Context, req *v1.GetAssignmentRequest) (*v1.GetAssignmentReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetAssignmentReply{Code: code, Message: msg}, nil
	}
	a, err := s.uc.GetAssignment(ctx, userID, uint64(req.GetId()))
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GetAssignmentReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetAssignmentReply{Code: 500, Message: err.Error()}, nil
	}
	statusMap, _ := s.uc.GetQuestionGenerateStatusMap(ctx, a.ID)
	return &v1.GetAssignmentReply{
		Code:    0,
		Message: "success",
		Data:    toAssignmentData(a, statusMap),
	}, nil
}

func (s *AssignmentService) GetAssignmentAnswers(ctx context.Context, req *v1.GetAssignmentAnswersRequest) (*v1.GetAssignmentAnswersReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetAssignmentAnswersReply{Code: code, Message: msg}, nil
	}
	if req.GetId() <= 0 {
		return &v1.GetAssignmentAnswersReply{Code: 400, Message: "作业ID无效"}, nil
	}
	result, err := s.uc.GetAssignmentAnswers(ctx, userID, uint64(req.GetId()))
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GetAssignmentAnswersReply{Code: 404, Message: "作业不存在"}, nil
		}
		return &v1.GetAssignmentAnswersReply{Code: 500, Message: err.Error()}, nil
	}
	items := make([]*v1.AnswerQuestionItem, 0, len(result.Questions))
	for _, q := range result.Questions {
		item := &v1.AnswerQuestionItem{
			QuestionId:        q.QuestionID,
			QuestionText:      q.QuestionText,
			UserAnswer:        q.UserAnswer,
			CorrectAnswer:     q.CorrectAnswer,
			Analysis:          q.Analysis,
			HasStandardAnswer: q.HasStandardAnswer,
		}
		if q.IsCorrect != nil {
			item.IsCorrect = q.IsCorrect
		}
		items = append(items, item)
	}
	data := &v1.AssignmentAnswersData{
		AssignmentId:   int64(result.AssignmentID),
		Questions:      items,
		TotalQuestions: int32(result.TotalQuestions),
		CorrectCount:   int32(result.CorrectCount),
		WrongCount:     int32(result.WrongCount),
		CorrectRate:    int32(result.CorrectRate),
	}
	if result.Score != nil {
		data.Score = result.Score
	}
	return &v1.GetAssignmentAnswersReply{
		Code:    0,
		Message: "success",
		Data:    data,
	}, nil
}

func (s *AssignmentService) UploadImage(ctx context.Context, req *v1.UploadImageRequest) (*v1.UploadImageReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.UploadImageReply{Code: code, Message: msg}, nil
	}
	if req.GetChildId() <= 0 {
		return &v1.UploadImageReply{Code: 400, Message: "childId 必填"}, nil
	}
	imageURL := ""
	if len(req.GetFile()) > 0 {
		// 先创建作业获取 ID，再保存图片并更新
		a, err := s.uc.CreateAssignment(ctx, userID, uint64(req.GetChildId()), "")
		if err != nil {
			if err == usecase.ErrAssignmentNotFound {
				return &v1.UploadImageReply{Code: 403, Message: "无权限操作该儿童档案"}, nil
			}
			return &v1.UploadImageReply{Code: 500, Message: err.Error()}, nil
		}
		filename := "image.jpg"
		if n := req.GetFile(); len(n) >= 4 {
			if n[0] == 0x89 && n[1] == 0x50 && n[2] == 0x4e {
				filename = "image.png"
			}
		}
		imageURL, err = s.store.SaveAssignmentImage(ctx, a.ID, req.GetFile(), filename)
		if err != nil {
			return &v1.UploadImageReply{Code: 500, Message: fmt.Sprintf("保存图片失败: %v", err)}, nil
		}
		if err := s.uc.UpdateAssignmentImages(ctx, userID, a.ID, model.StringArray{imageURL}); err != nil {
			return &v1.UploadImageReply{Code: 500, Message: err.Error()}, nil
		}
		return &v1.UploadImageReply{
			Code:    0,
			Message: "上传成功",
			Data:    &v1.UploadImageData{Id: int64(a.ID)},
		}, nil
	}
	// 无文件时仅创建作业
	a, err := s.uc.CreateAssignment(ctx, userID, uint64(req.GetChildId()), "")
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.UploadImageReply{Code: 403, Message: "无权限操作该儿童档案"}, nil
		}
		return &v1.UploadImageReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.UploadImageReply{
		Code:    0,
		Message: "上传成功",
		Data:    &v1.UploadImageData{Id: int64(a.ID)},
	}, nil
}

func (s *AssignmentService) Scan(ctx context.Context, _ *v1.ScanRequest) (*v1.ScanReply, error) {
	return &v1.ScanReply{Code: 500, Message: "请使用 POST /api/v1/assignments/{id}/scan 按作业ID触发识别"}, nil
}

func (s *AssignmentService) TriggerScan(ctx context.Context, req *v1.TriggerScanRequest) (*v1.ScanReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.ScanReply{Code: code, Message: msg}, nil
	}
	if req.GetId() <= 0 {
		return &v1.ScanReply{Code: 400, Message: "作业ID无效"}, nil
	}
	a, err := s.uc.TriggerScan(ctx, userID, uint64(req.GetId()), req.GetSubject())
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.ScanReply{Code: 404, Message: "作业不存在"}, nil
		}
		if err == usecase.ErrNoImagesToScan {
			return &v1.ScanReply{Code: 400, Message: err.Error()}, nil
		}
		if err == usecase.ErrScanAlreadyTriggered {
			return &v1.ScanReply{Code: 400, Message: err.Error()}, nil
		}
		return &v1.ScanReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.ScanReply{
		Code:    0,
		Message: "识别任务已提交",
		Data: &v1.ScanData{
			AssignmentId:  int64(a.ID),
			Status:        a.Status,
			Progress:      0,
			EstimatedTime: 30,
		},
	}, nil
}

func (s *AssignmentService) GetScanStatus(ctx context.Context, req *v1.GetScanStatusRequest) (*v1.GetScanStatusReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetScanStatusReply{Code: code, Message: msg}, nil
	}
	if req.GetId() <= 0 {
		return &v1.GetScanStatusReply{Code: 400, Message: "作业ID无效"}, nil
	}
	a, err := s.uc.GetAssignment(ctx, userID, uint64(req.GetId()))
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GetScanStatusReply{Code: 404, Message: "作业不存在"}, nil
		}
		return &v1.GetScanStatusReply{Code: 500, Message: err.Error()}, nil
	}
	progress := int32(0)
	estimatedTime := int32(30)
	switch a.Status {
	case "processing":
		progress = 50
		estimatedTime = 10
	case "completed":
		progress = 100
		estimatedTime = 0
	case "failed":
		progress = 0
	}
	statusMap, _ := s.uc.GetQuestionGenerateStatusMap(ctx, a.ID)
	questions := make([]*v1.QuestionData, 0, len(a.Questions))
	for _, q := range a.Questions {
		var gen *model.QuestionGenerationStatus
		if statusMap != nil {
			gen = statusMap[q.ID]
		}
		questions = append(questions, toQuestionData(&q, gen))
	}
	return &v1.GetScanStatusReply{
		Code:    0,
		Message: "success",
		Data: &v1.ScanStatusData{
			AssignmentId:  int64(a.ID),
			Status:        a.Status,
			Progress:      progress,
			EstimatedTime: estimatedTime,
			Questions:     questions,
		},
	}, nil
}

func (s *AssignmentService) UpdateQuestion(ctx context.Context, _ *v1.UpdateQuestionRequest) (*v1.UpdateQuestionReply, error) {
	return &v1.UpdateQuestionReply{Code: 500, Message: "编辑识别结果功能暂未实现"}, nil
}

func (s *AssignmentService) SplitQuestions(ctx context.Context, _ *v1.SplitQuestionsRequest) (*v1.SplitQuestionsReply, error) {
	return &v1.SplitQuestionsReply{Code: 500, Message: "题目分割确认功能暂未实现"}, nil
}

func (s *AssignmentService) UpdateQuestionType(ctx context.Context, _ *v1.UpdateQuestionTypeRequest) (*v1.UpdateQuestionTypeReply, error) {
	return &v1.UpdateQuestionTypeReply{Code: 500, Message: "题目类型标注功能暂未实现"}, nil
}

func (s *AssignmentService) GetKnowledgePoints(ctx context.Context, _ *v1.GetKnowledgePointsRequest) (*v1.GetKnowledgePointsReply, error) {
	return &v1.GetKnowledgePointsReply{Code: 500, Message: "知识点匹配功能暂未实现"}, nil
}

func (s *AssignmentService) UpdateKnowledgePoints(ctx context.Context, _ *v1.UpdateKnowledgePointsRequest) (*v1.UpdateKnowledgePointsReply, error) {
	return &v1.UpdateKnowledgePointsReply{Code: 500, Message: "更新知识点功能暂未实现"}, nil
}

func (s *AssignmentService) UpdateAssignment(ctx context.Context, req *v1.UpdateAssignmentRequest) (*v1.UpdateAssignmentReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.UpdateAssignmentReply{Code: code, Message: msg}, nil
	}
	if req.GetId() <= 0 {
		return &v1.UpdateAssignmentReply{Code: 400, Message: "作业ID无效"}, nil
	}
	questions := questionDataToModel(req.GetQuestions())
	a, err := s.uc.UpdateAssignment(ctx, userID, uint64(req.GetId()), req.GetSubject(), questions, req.GetStatus())
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.UpdateAssignmentReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.UpdateAssignmentReply{Code: 500, Message: err.Error()}, nil
	}
	statusMap, _ := s.uc.GetQuestionGenerateStatusMap(ctx, a.ID)
	return &v1.UpdateAssignmentReply{
		Code:    0,
		Message: "success",
		Data:    toAssignmentData(a, statusMap),
	}, nil
}

func questionDataToModel(qs []*v1.QuestionData) model.Questions {
	if len(qs) == 0 {
		return nil
	}
	out := make(model.Questions, 0, len(qs))
	for _, q := range qs {
		if q == nil {
			continue
		}
		mq := model.Question{
			ID:             q.GetId(),
			QuestionNumber: q.GetQuestionNumber(),
			QuestionType:   q.GetQuestionType(),
			OriginalText:   q.GetOriginalText(),
		}
		if sd := q.GetStructuredData(); sd != nil {
			opts := make([]model.Option, 0, len(sd.GetOptions()))
			for _, o := range sd.GetOptions() {
				if o != nil {
					opts = append(opts, model.Option{Option: o.GetOption(), Text: o.GetText()})
				}
			}
			mq.StructuredData = &model.StructuredData{
				Stem:     sd.GetStem(),
				Options:  opts,
				Answer:   sd.GetAnswer(),
				Analysis: sd.GetAnalysis(),
			}
		}
		for _, kp := range q.GetKnowledgePoints() {
			if kp != nil {
				mq.KnowledgePoints = append(mq.KnowledgePoints, model.KnowledgePoint{
					Subject:     kp.GetSubject(),
					Topic:       kp.GetTopic(),
					Subtopic:    kp.GetSubtopic(),
					Difficulty:  kp.GetDifficulty(),
					Confidence:  kp.GetConfidence(),
					Description: kp.GetDescription(),
				})
			}
		}
		if meta := q.GetMetadata(); meta != nil {
			mq.Metadata = &model.QuestionMetadata{
				WordCount:  meta.GetWordCount(),
				HasImage:   meta.GetHasImage(),
				HasFormula: meta.GetHasFormula(),
				Confidence: meta.GetConfidence(),
			}
		}
		out = append(out, mq)
	}
	return out
}

func (s *AssignmentService) DeleteQuestion(ctx context.Context, _ *v1.DeleteQuestionRequest) (*v1.DeleteQuestionReply, error) {
	return &v1.DeleteQuestionReply{Code: 500, Message: "删除题目功能暂未实现"}, nil
}

func (s *AssignmentService) GenerateQuestionContent(ctx context.Context, req *v1.GenerateQuestionContentRequest) (*v1.GenerateContentReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GenerateContentReply{Code: code, Message: msg}, nil
	}
	if req.GetAssignmentId() <= 0 || req.GetQuestionId() == "" {
		return &v1.GenerateContentReply{Code: 400, Message: "assignmentId 和 questionId 必填"}, nil
	}
	sts, err := s.uc.TriggerQuestionGenerateContent(ctx, userID, uint64(req.GetAssignmentId()), req.GetQuestionId())
	if err != nil {
		if err == usecase.ErrAssignmentNotFound || err == usecase.ErrQuestionNotFound {
			return &v1.GenerateContentReply{Code: 404, Message: err.Error()}, nil
		}
		if err == usecase.ErrQuestionGenerateStarted {
			return &v1.GenerateContentReply{Code: 400, Message: err.Error()}, nil
		}
		return &v1.GenerateContentReply{Code: 500, Message: err.Error()}, nil
	}
	contentID := fmt.Sprintf("content-%d-%s", req.GetAssignmentId(), req.GetQuestionId())
	return &v1.GenerateContentReply{
		Code:    0,
		Message: "开始生成",
		Data: &v1.GenerateContentData{
			ContentId: contentID,
			Status:    sts.Status,
		},
	}, nil
}

func (s *AssignmentService) GetQuestionContentGenerateStatus(ctx context.Context, req *v1.GetQuestionContentGenerateStatusRequest) (*v1.GetGenerateStatusReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetGenerateStatusReply{Code: code, Message: msg}, nil
	}
	if req.GetAssignmentId() <= 0 || req.GetQuestionId() == "" {
		return &v1.GetGenerateStatusReply{Code: 400, Message: "assignmentId 和 questionId 必填"}, nil
	}
	sts, err := s.uc.GetQuestionGenerateStatus(ctx, userID, uint64(req.GetAssignmentId()), req.GetQuestionId())
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GetGenerateStatusReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetGenerateStatusReply{Code: 500, Message: err.Error()}, nil
	}
	contentID := fmt.Sprintf("content-%d-%s", req.GetAssignmentId(), req.GetQuestionId())
	status := "pending"
	progress := int32(0)
	estimatedTime := int32(30)
	var storyID string
	if sts != nil {
		status = sts.Status
		storyID = sts.StoryID
		switch sts.Status {
		case "processing":
			progress = 50
			estimatedTime = 15
		case "completed":
			progress = 100
			estimatedTime = 0
		case "failed":
			progress = 0
		default:
			progress = 0
		}
	}
	// 单题插图状态：从 story_contents 读取 illustration_status、illustration_progress 与 illustration_images
	imageStatus := ""
	imageProgress := int32(0)
	var imageUrls []string
	if storyID != "" {
		if sc, err := s.uc.StoryContentRepo().FindByStoryID(ctx, storyID); err == nil && sc != nil {
			imageStatus = sc.IllustrationStatus
			imageProgress = sc.IllustrationProgress
			imageUrls = []string(sc.IllustrationImages)
		}
	}
	return &v1.GetGenerateStatusReply{
		Code:    0,
		Message: "success",
		Data: &v1.GenerateStatusData{
			ContentId:     contentID,
			Status:        status,
			Progress:      progress,
			EstimatedTime: estimatedTime,
			StoryId:       storyID,
			ImageStatus:   imageStatus,
			ImageProgress: imageProgress,
			ImageUrls:     imageUrls,
		},
	}, nil
}

func (s *AssignmentService) GenerateContent(ctx context.Context, req *v1.GenerateContentRequest) (*v1.GenerateContentReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GenerateContentReply{Code: code, Message: msg}, nil
	}
	if req.GetAssignmentId() <= 0 {
		return &v1.GenerateContentReply{Code: 400, Message: "作业ID无效"}, nil
	}
	a, err := s.uc.TriggerGenerateContent(ctx, userID, uint64(req.GetAssignmentId()))
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GenerateContentReply{Code: 404, Message: "作业不存在"}, nil
		}
		if err == usecase.ErrNoQuestionsToGenerate {
			return &v1.GenerateContentReply{Code: 400, Message: err.Error()}, nil
		}
		if err == usecase.ErrGenerateAlreadyStarted {
			return &v1.GenerateContentReply{Code: 400, Message: err.Error()}, nil
		}
		return &v1.GenerateContentReply{Code: 500, Message: err.Error()}, nil
	}
	contentID := fmt.Sprintf("gen-%d", a.ID)
	return &v1.GenerateContentReply{
		Code:    0,
		Message: "开始生成",
		Data: &v1.GenerateContentData{
			ContentId: contentID,
			Status:    "processing",
		},
	}, nil
}

func (s *AssignmentService) GetGenerateStatus(ctx context.Context, req *v1.GetGenerateStatusRequest) (*v1.GetGenerateStatusReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetGenerateStatusReply{Code: code, Message: msg}, nil
	}
	if req.GetAssignmentId() <= 0 {
		return &v1.GetGenerateStatusReply{Code: 400, Message: "作业ID无效"}, nil
	}
	a, err := s.uc.GetAssignment(ctx, userID, uint64(req.GetAssignmentId()))
	if err != nil {
		if err == usecase.ErrAssignmentNotFound {
			return &v1.GetGenerateStatusReply{Code: 404, Message: "作业不存在"}, nil
		}
		return &v1.GetGenerateStatusReply{Code: 500, Message: err.Error()}, nil
	}
	contentID := fmt.Sprintf("gen-%d", a.ID)
	status := "pending"
	progress := int32(0)
	estimatedTime := int32(30)
	var storyID string
	if a.GeneratedContent != nil {
		status = a.GeneratedContent.Status
		storyID = a.GeneratedContent.StoryID
		switch status {
		case "processing":
			progress = 50
			estimatedTime = 15
		case "completed":
			progress = 100
			estimatedTime = 0
		case "failed":
			progress = 0
		}
	}
	// 图片/插图生成状态：从 story_contents 读取 illustration_status、illustration_progress 与 illustration_images
	imageStatus := ""
	imageProgress := int32(0)
	var imageUrls []string
	if storyID != "" {
		if sc, err := s.uc.StoryContentRepo().FindByStoryID(ctx, storyID); err == nil && sc != nil {
			imageStatus = sc.IllustrationStatus
			imageProgress = sc.IllustrationProgress
			imageUrls = []string(sc.IllustrationImages)
		}
	}
	return &v1.GetGenerateStatusReply{
		Code:    0,
		Message: "success",
		Data: &v1.GenerateStatusData{
			ContentId:     contentID,
			Status:        status,
			Progress:      progress,
			EstimatedTime: estimatedTime,
			StoryId:       storyID,
			ImageStatus:   imageStatus,
			ImageProgress: imageProgress,
			ImageUrls:     imageUrls,
		},
	}, nil
}

func toAssignmentData(a *model.Assignment, statusMap map[string]*model.QuestionGenerationStatus) *v1.AssignmentData {
	if a == nil {
		return nil
	}
	images := []string(a.OriginalImages)
	questions := make([]*v1.QuestionData, 0, len(a.Questions))
	for _, q := range a.Questions {
		var gen *model.QuestionGenerationStatus
		if statusMap != nil {
			gen = statusMap[q.ID]
		}
		questions = append(questions, toQuestionData(&q, gen))
	}
	var gen *v1.GeneratedContent
	if a.GeneratedContent != nil {
		gen = &v1.GeneratedContent{
			StoryId: a.GeneratedContent.StoryID,
			Status:  a.GeneratedContent.Status,
		}
	}
	score := float32(0)
	if a.Score != nil {
		score = *a.Score
	}
	completedAt := ""
	if a.CompletedAt != nil {
		completedAt = a.CompletedAt.Format(time.RFC3339)
	}
	return &v1.AssignmentData{
		Id:             int64(a.ID),
		ChildId:        int64(a.ChildID),
		Subject:        a.Subject,
		Grade:          "",
		OriginalImages: images,
		Questions:      questions,
		GeneratedContent: gen,
		Status:         a.Status,
		EstimatedTime:  a.EstimatedTime,
		ActualTime:     a.ActualTime,
		Score:          score,
		CompletedAt:    completedAt,
		CreatedAt:      formatTimeUser(a.CreatedAt),
		UpdatedAt:      formatTimeUser(a.UpdatedAt),
	}
}

func toQuestionData(q *model.Question, gen *model.QuestionGenerationStatus) *v1.QuestionData {
	if q == nil {
		return nil
	}
	var sd *v1.StructuredData
	if q.StructuredData != nil {
		opts := make([]*v1.Option, 0, len(q.StructuredData.Options))
		for _, o := range q.StructuredData.Options {
			opts = append(opts, &v1.Option{Option: o.Option, Text: o.Text})
		}
		sd = &v1.StructuredData{
			Stem:     q.StructuredData.Stem,
			Options:  opts,
			Answer:   q.StructuredData.Answer,
			Analysis: q.StructuredData.Analysis,
		}
	}
	kps := make([]*v1.KnowledgePoint, 0, len(q.KnowledgePoints))
	for _, k := range q.KnowledgePoints {
		kps = append(kps, &v1.KnowledgePoint{
			Subject:     k.Subject,
			Topic:       k.Topic,
			Subtopic:    k.Subtopic,
			Difficulty:  k.Difficulty,
			Confidence:  k.Confidence,
			Description: k.Description,
		})
	}
	var meta *v1.QuestionMetadata
	if q.Metadata != nil {
		meta = &v1.QuestionMetadata{
			WordCount:  q.Metadata.WordCount,
			HasImage:   q.Metadata.HasImage,
			HasFormula: q.Metadata.HasFormula,
			Confidence: q.Metadata.Confidence,
		}
	}
	var gc *v1.GeneratedContent
	if gen != nil {
		gc = &v1.GeneratedContent{
			Status:  gen.Status,
			StoryId: gen.StoryID,
		}
	}
	return &v1.QuestionData{
		Id:               q.ID,
		QuestionNumber:   q.QuestionNumber,
		QuestionType:     q.QuestionType,
		OriginalText:     q.OriginalText,
		StructuredData:   sd,
		KnowledgePoints:  kps,
		Metadata:         meta,
		UpdatedAt:        "",
		GeneratedContent: gc,
	}
}
