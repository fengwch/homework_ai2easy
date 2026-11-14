package grpcService

import (
	"context"
	"errors"

	"github.com/go-kratos/kratos/v2/log"

	v1 "homework_ai2easy/backend/api/content/v1"
	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/pkg/aiagent"
)

var _ v1.ContentServiceServer = (*ContentService)(nil)
var _ v1.ContentServiceHTTPServer = (*ContentService)(nil)

// ContentService 学习内容服务
type ContentService struct {
	v1.UnimplementedContentServiceServer
	uc  *usecase.ContentUsecase
	log *log.Helper
}

// NewContentService 创建学习内容服务
func NewContentService(uc *usecase.ContentUsecase, logger log.Logger) *ContentService {
	return &ContentService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

// GetContent 获取学习材料
func (s *ContentService) GetContent(ctx context.Context, req *v1.GetContentRequest) (*v1.GetContentReply, error) {
	if req.StoryId == "" {
		return &v1.GetContentReply{
			Code:    400,
			Message: "story_id 不能为空",
		}, nil
	}

	sc, err := s.uc.GetStoryContent(ctx, req.StoryId)
	if err != nil {
		s.log.WithContext(ctx).Errorf("获取学习内容失败: %v", err)
		return &v1.GetContentReply{
			Code:    500,
			Message: "获取学习内容失败",
		}, nil
	}
	if sc == nil {
		return &v1.GetContentReply{
			Code:    404,
			Message: "学习内容不存在",
		}, nil
	}

	// 转换 questions
	questions := make([]*v1.ContentQuestion, 0)
	for _, q := range sc.Questions {
		qMap, ok := q.(map[string]interface{})
		if !ok {
			continue
		}
		cq := &v1.ContentQuestion{}
		if id, ok := qMap["id"].(string); ok {
			cq.Id = id
		}
		if num, ok := qMap["questionNumber"].(float64); ok {
			cq.QuestionNumber = int32(num)
		}
		if content, ok := qMap["content"].(string); ok {
			cq.Content = content
		}
		if options, ok := qMap["options"].([]interface{}); ok {
			for _, opt := range options {
				if s, ok := opt.(string); ok {
					cq.Options = append(cq.Options, s)
				}
			}
		}
		if answer, ok := qMap["answer"].(string); ok {
			cq.Answer = answer
		}
		if analysis, ok := qMap["analysis"].(string); ok {
			cq.Analysis = analysis
		}
		questions = append(questions, cq)
	}

	// 插图 URL 列表：仅当已生成并落库时非空，前端按有无 images 决定是否展示插图区
	images := []string(sc.IllustrationImages)
	if images == nil {
		images = []string{}
	}

	return &v1.GetContentReply{
		Code:    0,
		Message: "success",
		Data: &v1.ContentData{
			StoryId:   sc.StoryID,
			Title:     sc.Title,
			Summary:   sc.Summary,
			Story:     sc.Story,
			Questions: questions,
			Theme:     sc.Theme,
			Images:    images,
		},
	}, nil
}

// SubmitAnswer 提交题目答案
func (s *ContentService) SubmitAnswer(ctx context.Context, req *v1.SubmitAnswerRequest) (*v1.SubmitAnswerReply, error) {
	// 参数验证
	if req.QuestionId == "" {
		return &v1.SubmitAnswerReply{
			Code:    400,
			Message: "question_id 不能为空",
		}, nil
	}
	if req.Answer == "" {
		return &v1.SubmitAnswerReply{
			Code:    400,
			Message: "answer 不能为空",
		}, nil
	}
	if req.StoryId == "" && req.AssignmentId <= 0 {
		return &v1.SubmitAnswerReply{
			Code:    400,
			Message: "story_id 与 assignment_id 至少传其一；无故事时请传 assignment_id 直接答题",
		}, nil
	}

	result, err := s.uc.SubmitAnswer(ctx, req.StoryId, uint64(req.AssignmentId), req.QuestionId, req.Answer)
	if err != nil {
		s.log.WithContext(ctx).Errorf("提交答案失败: %v", err)
		if errors.Is(err, usecase.ErrStoryNotFound) {
			return &v1.SubmitAnswerReply{
				Code:    404,
				Message: "学习内容不存在",
			}, nil
		}
		if errors.Is(err, usecase.ErrQuestionNotFound) {
			return &v1.SubmitAnswerReply{
				Code:    404,
				Message: "题目不存在",
			}, nil
		}
		return &v1.SubmitAnswerReply{
			Code:    500,
			Message: "提交答案失败",
		}, nil
	}

	return &v1.SubmitAnswerReply{
		Code:    0,
		Message: "success",
		Data: &v1.SubmitAnswerData{
			IsCorrect: result.IsCorrect,
			Feedback:  result.Feedback,
		},
	}, nil
}

// GetSolutionGuide 解题引导
func (s *ContentService) GetSolutionGuide(ctx context.Context, req *v1.GetSolutionGuideRequest) (*v1.GetSolutionGuideReply, error) {
	if req.QuestionId == "" || req.StoryId == "" {
		return &v1.GetSolutionGuideReply{
			Code:    400,
			Message: "question_id 和 story_id 不能为空",
		}, nil
	}

	// 获取解题引导
	resp, err := s.uc.GetSolutionGuide(ctx, aiagent.SolutionGuideRequest{
		Question: aiagent.SolutionGuideQuestion{
			ID: req.QuestionId,
		},
	})
	if err != nil {
		s.log.WithContext(ctx).Errorf("获取解题引导失败: %v", err)
		return &v1.GetSolutionGuideReply{
			Code:    500,
			Message: "获取解题引导失败",
		}, nil
	}

	// 转换步骤
	steps := make([]*v1.GuideStep, 0, len(resp.Steps))
	for _, step := range resp.Steps {
		steps = append(steps, &v1.GuideStep{
			StepNumber:  int32(step.Order),
			Hint:        step.Text,
			Explanation: "",
		})
	}

	return &v1.GetSolutionGuideReply{
		Code:    0,
		Message: "success",
		Data: &v1.SolutionGuideData{
			Steps: steps,
		},
	}, nil
}
