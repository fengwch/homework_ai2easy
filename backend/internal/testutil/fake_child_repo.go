package testutil

import (
	"context"
	"sync"
	"time"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.ChildRepository = (*FakeChildRepository)(nil)

// FakeChildRepository 内存版 ChildRepository，用于单测
type FakeChildRepository struct {
	mu     sync.Mutex
	byID   map[uint64]*model.Child
	nextID uint64
}

// NewFakeChildRepository 创建内存儿童仓储
func NewFakeChildRepository() *FakeChildRepository {
	return &FakeChildRepository{
		byID:   make(map[uint64]*model.Child),
		nextID: 1,
	}
}

func (r *FakeChildRepository) Create(ctx context.Context, child *model.Child) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	child.ID = r.nextID
	r.nextID++
	child.CreatedAt = time.Now()
	child.UpdatedAt = child.CreatedAt
	c := *child
	r.byID[child.ID] = &c
	return nil
}

func (r *FakeChildRepository) FindByID(ctx context.Context, id uint64) (*model.Child, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	c, ok := r.byID[id]
	if !ok {
		return nil, nil
	}
	cp := *c
	return &cp, nil
}

func (r *FakeChildRepository) FindByUserID(ctx context.Context, userID uint64) ([]*model.Child, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*model.Child
	for _, c := range r.byID {
		if c.UserID == userID {
			cp := *c
			out = append(out, &cp)
		}
	}
	return out, nil
}

func (r *FakeChildRepository) Update(ctx context.Context, child *model.Child) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.byID[child.ID]; !ok {
		return nil
	}
	child.UpdatedAt = time.Now()
	c := *child
	r.byID[child.ID] = &c
	return nil
}

func (r *FakeChildRepository) Delete(ctx context.Context, id uint64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.byID, id)
	return nil
}

func (r *FakeChildRepository) CountByUserID(ctx context.Context, userID uint64) (int64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var n int64
	for _, c := range r.byID {
		if c.UserID == userID {
			n++
		}
	}
	return n, nil
}
