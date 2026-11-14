package testutil

import (
	"context"
	"sync"

	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.VoiceTaskRepository = (*FakeVoiceTaskRepository)(nil)

// FakeVoiceTaskRepository 内存版 VoiceTaskRepository，用于单测
type FakeVoiceTaskRepository struct {
	mu   sync.Mutex
	task map[string]*repository.VoiceTaskState
}

// NewFakeVoiceTaskRepository 创建内存语音任务仓储
func NewFakeVoiceTaskRepository() *FakeVoiceTaskRepository {
	return &FakeVoiceTaskRepository{
		task: make(map[string]*repository.VoiceTaskState),
	}
}

func (r *FakeVoiceTaskRepository) SetTask(ctx context.Context, taskID string, state *repository.VoiceTaskState) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if state == nil {
		return nil
	}
	cp := *state
	r.task[taskID] = &cp
	return nil
}

func (r *FakeVoiceTaskRepository) GetTask(ctx context.Context, taskID string) (*repository.VoiceTaskState, bool, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	s, ok := r.task[taskID]
	if !ok {
		return nil, false, nil
	}
	cp := *s
	return &cp, true, nil
}
