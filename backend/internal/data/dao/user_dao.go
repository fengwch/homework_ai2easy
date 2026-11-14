package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.UserRepository = (*userDao)(nil)

type userDao struct {
	data *Data
}

// NewUserRepository 创建用户仓储
func NewUserRepository(data *Data) repository.UserRepository {
	return &userDao{data: data}
}

func (r *userDao) Create(ctx context.Context, user *model.User) error {
	return r.data.db.WithContext(ctx).Create(user).Error
}

func (r *userDao) FindByID(ctx context.Context, id uint64) (*model.User, error) {
	var user model.User
	err := r.data.db.WithContext(ctx).Where("id = ?", id).First(&user).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &user, nil
}

func (r *userDao) FindByPhone(ctx context.Context, phone string) (*model.User, error) {
	var user model.User
	err := r.data.db.WithContext(ctx).Where("phone = ?", phone).First(&user).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &user, nil
}

func (r *userDao) FindByWechatOpenID(ctx context.Context, openID string) (*model.User, error) {
	var user model.User
	// GORM 默认将 WechatOpenID 转为列名 wechat_open_id
	err := r.data.db.WithContext(ctx).Where("wechat_open_id = ?", openID).First(&user).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &user, nil
}

func (r *userDao) Update(ctx context.Context, user *model.User) error {
	return r.data.db.WithContext(ctx).Save(user).Error
}

func (r *userDao) Delete(ctx context.Context, id uint64) error {
	return r.data.db.WithContext(ctx).Delete(&model.User{}, id).Error
}
