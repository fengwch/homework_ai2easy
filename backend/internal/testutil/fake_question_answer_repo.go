package testutil

import (
	"context"
	"sync"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.QuestionAnswerRepository = (*FakeQuestionAnswerRepository)(nil)

// FakeQuestionAnswerRepository 内存版 QuestionAnswerRepository，用于单测
type FakeQuestionAnswerRepository struct {
	mu   sync.Mutex
	list []*model.QuestionAnswer
}

// NewFakeQuestionAnswerRepository 创建内存题目作答仓储
func NewFakeQuestionAnswerRepository() *FakeQuestionAnswerRepository {
	return &FakeQuestionAnswerRepository{list: make([]*model.QuestionAnswer, 0)}
}

func (r *FakeQuestionAnswerRepository) SaveOrUpdate(ctx context.Context, ans *model.QuestionAnswer) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for i, a := range r.list {
		if a.AssignmentID == ans.AssignmentID && a.QuestionID == ans.QuestionID && a.ChildID == ans.ChildID {
			r.list[i] = ans
			return nil
		}
	}
	cp := *ans
	r.list = append(r.list, &cp)
	return nil
}

func (r *FakeQuestionAnswerRepository) ListByAssignmentAndChild(ctx context.Context, assignmentID, childID uint64) ([]*model.QuestionAnswer, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*model.QuestionAnswer
	for _, a := range r.list {
		if a.AssignmentID == assignmentID && a.ChildID == childID {
			cp := *a
			out = append(out, &cp)
		}
	}
	return out, nil
}

func (r *FakeQuestionAnswerRepository) ListByAssignmentIDsAndChild(ctx context.Context, assignmentIDs []uint64, childID uint64) ([]*model.QuestionAnswer, error) {
	if len(assignmentIDs) == 0 {
		return nil, nil
	}
	set := make(map[uint64]struct{})
	for _, id := range assignmentIDs {
		set[id] = struct{}{}
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []*model.QuestionAnswer
	for _, a := range r.list {
		if _, ok := set[a.AssignmentID]; ok && a.ChildID == childID {
			cp := *a
			out = append(out, &cp)
		}
	}
	return out, nil
}
