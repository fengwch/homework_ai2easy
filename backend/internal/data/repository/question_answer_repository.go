package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// QuestionAnswerRepository 题目作答仓储接口
type QuestionAnswerRepository interface {
	SaveOrUpdate(ctx context.Context, ans *model.QuestionAnswer) error
	ListByAssignmentAndChild(ctx context.Context, assignmentID, childID uint64) ([]*model.QuestionAnswer, error)
	// ListByAssignmentIDsAndChild 批量获取多个作业的作答记录，用于列表页 has_answers/score
	ListByAssignmentIDsAndChild(ctx context.Context, assignmentIDs []uint64, childID uint64) ([]*model.QuestionAnswer, error)
}
