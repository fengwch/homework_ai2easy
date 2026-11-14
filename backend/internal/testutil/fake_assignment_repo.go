package testutil

import (
	"context"
	"sync"
	"time"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.AssignmentRepository = (*FakeAssignmentRepository)(nil)

// FakeAssignmentRepository 内存版 AssignmentRepository，用于单测
type FakeAssignmentRepository struct {
	mu     sync.Mutex
	byID   map[uint64]*model.Assignment
	nextID uint64
}

// NewFakeAssignmentRepository 创建内存作业仓储
func NewFakeAssignmentRepository() *FakeAssignmentRepository {
	return &FakeAssignmentRepository{
		byID:   make(map[uint64]*model.Assignment),
		nextID: 1,
	}
}

func (r *FakeAssignmentRepository) Create(ctx context.Context, a *model.Assignment) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	a.ID = r.nextID
	r.nextID++
	a.CreatedAt = time.Now()
	a.UpdatedAt = a.CreatedAt
	c := *a
	r.byID[a.ID] = &c
	return nil
}

func (r *FakeAssignmentRepository) FindByID(ctx context.Context, id uint64) (*model.Assignment, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	a, ok := r.byID[id]
	if !ok {
		return nil, nil
	}
	cp := *a
	return &cp, nil
}

func (r *FakeAssignmentRepository) FindByChildID(ctx context.Context, childID uint64, page, pageSize int) ([]*model.Assignment, int64, error) {
	return r.FindByChildIDWithFilters(ctx, childID, "", "", nil, page, pageSize)
}

func (r *FakeAssignmentRepository) FindByChildIDWithFilters(ctx context.Context, childID uint64, status, subject string, hasAnswers *bool, page, pageSize int) ([]*model.Assignment, int64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*model.Assignment
	for _, a := range r.byID {
		if a.ChildID != childID {
			continue
		}
		if status != "" && a.Status != status {
			continue
		}
		if subject != "" && a.Subject != subject {
			continue
		}
		cp := *a
		out = append(out, &cp)
	}
	total := int64(len(out))
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	start := (page - 1) * pageSize
	if start >= len(out) {
		return []*model.Assignment{}, total, nil
	}
	end := start + pageSize
	if end > len(out) {
		end = len(out)
	}
	return out[start:end], total, nil
}

func (r *FakeAssignmentRepository) FindByStatus(ctx context.Context, status string, page, pageSize int) ([]*model.Assignment, int64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*model.Assignment
	for _, a := range r.byID {
		if a.Status == status {
			cp := *a
			out = append(out, &cp)
		}
	}
	total := int64(len(out))
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	start := (page - 1) * pageSize
	if start >= len(out) {
		return []*model.Assignment{}, total, nil
	}
	end := start + pageSize
	if end > len(out) {
		end = len(out)
	}
	return out[start:end], total, nil
}

func (r *FakeAssignmentRepository) Update(ctx context.Context, a *model.Assignment) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.byID[a.ID]; !ok {
		return nil
	}
	a.UpdatedAt = time.Now()
	c := *a
	r.byID[a.ID] = &c
	return nil
}

func (r *FakeAssignmentRepository) Delete(ctx context.Context, id uint64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.byID, id)
	return nil
}
