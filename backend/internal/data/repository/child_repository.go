package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// ChildRepository 儿童档案仓储接口
type ChildRepository interface {
	Create(ctx context.Context, child *model.Child) error
	FindByID(ctx context.Context, id uint64) (*model.Child, error)
	FindByUserID(ctx context.Context, userID uint64) ([]*model.Child, error)
	Update(ctx context.Context, child *model.Child) error
	Delete(ctx context.Context, id uint64) error
	CountByUserID(ctx context.Context, userID uint64) (int64, error)
}
