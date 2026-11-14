package testutil

import (
	"context"
	"sync"
	"time"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.UserRepository = (*FakeUserRepository)(nil)

// FakeUserRepository 内存版 UserRepository，用于单测
type FakeUserRepository struct {
	mu      sync.Mutex
	users   map[uint64]*model.User
	byPhone map[string]uint64
	nextID  uint64
}

// NewFakeUserRepository 创建内存仓储
func NewFakeUserRepository() *FakeUserRepository {
	return &FakeUserRepository{
		users:   make(map[uint64]*model.User),
		byPhone: make(map[string]uint64),
		nextID:  1,
	}
}

// Create 创建用户，自动分配 ID、CreatedAt、UpdatedAt
func (r *FakeUserRepository) Create(ctx context.Context, user *model.User) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	user.ID = r.nextID
	r.nextID++
	user.CreatedAt = time.Now()
	user.UpdatedAt = user.CreatedAt
	u := *user
	u.DeletedAt = gorm.DeletedAt{}
	r.users[user.ID] = &u
	if user.Phone != "" {
		r.byPhone[user.Phone] = user.ID
	}
	return nil
}

// FindByID 按 ID 查找，已删除返回 nil
func (r *FakeUserRepository) FindByID(ctx context.Context, id uint64) (*model.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	u, ok := r.users[id]
	if !ok || u.DeletedAt.Valid {
		return nil, nil
	}
	cp := *u
	return &cp, nil
}

// FindByPhone 按手机号查找
func (r *FakeUserRepository) FindByPhone(ctx context.Context, phone string) (*model.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	id, ok := r.byPhone[phone]
	if !ok {
		return nil, nil
	}
	u, ok := r.users[id]
	if !ok || u.DeletedAt.Valid {
		return nil, nil
	}
	cp := *u
	return &cp, nil
}

// FindByWechatOpenID 按微信 OpenID 查找
func (r *FakeUserRepository) FindByWechatOpenID(ctx context.Context, openID string) (*model.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, u := range r.users {
		if u.DeletedAt.Valid {
			continue
		}
		if u.WechatOpenID == openID {
			cp := *u
			return &cp, nil
		}
	}
	return nil, nil
}

// Update 更新用户
func (r *FakeUserRepository) Update(ctx context.Context, user *model.User) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	old, ok := r.users[user.ID]
	if !ok {
		return nil
	}
	if old.Phone != "" {
		delete(r.byPhone, old.Phone)
	}
	user.UpdatedAt = time.Now()
	user.CreatedAt = old.CreatedAt
	user.DeletedAt = old.DeletedAt
	u := *user
	r.users[user.ID] = &u
	if user.Phone != "" {
		r.byPhone[user.Phone] = user.ID
	}
	return nil
}

// Delete 软删除：设置 DeletedAt，并从 byPhone 移除
func (r *FakeUserRepository) Delete(ctx context.Context, id uint64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	u, ok := r.users[id]
	if !ok {
		return nil
	}
	if u.Phone != "" {
		delete(r.byPhone, u.Phone)
	}
	t := time.Now()
	u.DeletedAt = gorm.DeletedAt{Time: t, Valid: true}
	return nil
}

// CreateForTest 测试用便捷方法：创建用户并返回 ID
func (r *FakeUserRepository) CreateForTest(phone, nickname, passwordHash string) uint64 {
	u := &model.User{
		Phone:        phone,
		Nickname:     nickname,
		PasswordHash: passwordHash,
		Status:       1,
	}
	_ = r.Create(context.Background(), u)
	return u.ID
}
