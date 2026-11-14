package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// UserRepository 用户仓储接口
type UserRepository interface {
	Create(ctx context.Context, user *model.User) error
	FindByID(ctx context.Context, id uint64) (*model.User, error)
	FindByPhone(ctx context.Context, phone string) (*model.User, error)
	FindByWechatOpenID(ctx context.Context, openID string) (*model.User, error)
	Update(ctx context.Context, user *model.User) error
	Delete(ctx context.Context, id uint64) error
}
