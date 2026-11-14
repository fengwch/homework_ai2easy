package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// AssignmentRepository 作业仓储接口
type AssignmentRepository interface {
	Create(ctx context.Context, assignment *model.Assignment) error
	FindByID(ctx context.Context, id uint64) (*model.Assignment, error)
	FindByChildID(ctx context.Context, childID uint64, page, pageSize int) ([]*model.Assignment, int64, error)
	FindByChildIDWithFilters(ctx context.Context, childID uint64, status, subject string, hasAnswers *bool, page, pageSize int) ([]*model.Assignment, int64, error)
	FindByStatus(ctx context.Context, status string, page, pageSize int) ([]*model.Assignment, int64, error)
	Update(ctx context.Context, assignment *model.Assignment) error
	Delete(ctx context.Context, id uint64) error
}
