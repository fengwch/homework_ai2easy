package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// QuestionGenerationRepository 单题内容生成状态仓储
type QuestionGenerationRepository interface {
	Create(ctx context.Context, s *model.QuestionGenerationStatus) error
	FindByAssignmentQuestion(ctx context.Context, assignmentID uint64, questionID string) (*model.QuestionGenerationStatus, error)
	ListByAssignmentID(ctx context.Context, assignmentID uint64) ([]*model.QuestionGenerationStatus, error)
	Update(ctx context.Context, s *model.QuestionGenerationStatus) error
}
