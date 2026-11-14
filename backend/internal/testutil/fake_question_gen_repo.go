package testutil

import (
	"context"
	"fmt"
	"sync"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.QuestionGenerationRepository = (*FakeQuestionGenerationRepository)(nil)

// FakeQuestionGenerationRepository 内存版单题生成状态仓储
type FakeQuestionGenerationRepository struct {
	mu    sync.Mutex
	byKey map[string]*model.QuestionGenerationStatus
}

// NewFakeQuestionGenerationRepository 创建
func NewFakeQuestionGenerationRepository() *FakeQuestionGenerationRepository {
	return &FakeQuestionGenerationRepository{
		byKey: make(map[string]*model.QuestionGenerationStatus),
	}
}

func key(aid uint64, qid string) string { return fmt.Sprintf("%d:%s", aid, qid) }

func (r *FakeQuestionGenerationRepository) Create(ctx context.Context, s *model.QuestionGenerationStatus) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	k := key(s.AssignmentID, s.QuestionID)
	c := *s
	r.byKey[k] = &c
	return nil
}

func (r *FakeQuestionGenerationRepository) FindByAssignmentQuestion(ctx context.Context, assignmentID uint64, questionID string) (*model.QuestionGenerationStatus, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	s, ok := r.byKey[key(assignmentID, questionID)]
	if !ok {
		return nil, nil
	}
	c := *s
	return &c, nil
}

func (r *FakeQuestionGenerationRepository) ListByAssignmentID(ctx context.Context, assignmentID uint64) ([]*model.QuestionGenerationStatus, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var list []*model.QuestionGenerationStatus
	prefix := fmt.Sprintf("%d:", assignmentID)
	for k, s := range r.byKey {
		if len(k) > len(prefix) && k[:len(prefix)] == prefix {
			c := *s
			list = append(list, &c)
		}
	}
	return list, nil
}

func (r *FakeQuestionGenerationRepository) Update(ctx context.Context, s *model.QuestionGenerationStatus) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	k := key(s.AssignmentID, s.QuestionID)
	c := *s
	r.byKey[k] = &c
	return nil
}
