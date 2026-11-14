package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.ChildRepository = (*childDao)(nil)

type childDao struct {
	data *Data
}

// NewChildRepository 创建儿童档案仓储
func NewChildRepository(data *Data) repository.ChildRepository {
	return &childDao{data: data}
}

func (r *childDao) Create(ctx context.Context, child *model.Child) error {
	return r.data.db.WithContext(ctx).Create(child).Error
}

func (r *childDao) FindByID(ctx context.Context, id uint64) (*model.Child, error) {
	var child model.Child
	err := r.data.db.WithContext(ctx).Where("id = ?", id).First(&child).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &child, nil
}

func (r *childDao) FindByUserID(ctx context.Context, userID uint64) ([]*model.Child, error) {
	var children []*model.Child
	err := r.data.db.WithContext(ctx).Where("user_id = ?", userID).Find(&children).Error
	if err != nil {
		return nil, err
	}
	return children, nil
}

func (r *childDao) Update(ctx context.Context, child *model.Child) error {
	return r.data.db.WithContext(ctx).Save(child).Error
}

func (r *childDao) Delete(ctx context.Context, id uint64) error {
	return r.data.db.WithContext(ctx).Delete(&model.Child{}, id).Error
}

func (r *childDao) CountByUserID(ctx context.Context, userID uint64) (int64, error) {
	var count int64
	err := r.data.db.WithContext(ctx).Model(&model.Child{}).Where("user_id = ?", userID).Count(&count).Error
	return count, err
}
