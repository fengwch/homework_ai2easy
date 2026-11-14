package testutil

import (
	"context"
	"sync"

	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.VoiceCacheRepository = (*FakeVoiceCacheRepository)(nil)

// FakeVoiceCacheRepository 内存版朗读内容缓存仓储，用于单测
type FakeVoiceCacheRepository struct {
	mu    sync.Mutex
	cache map[string]*repository.VoiceTaskState
}

// NewFakeVoiceCacheRepository 创建内存朗读缓存仓储
func NewFakeVoiceCacheRepository() *FakeVoiceCacheRepository {
	return &FakeVoiceCacheRepository{
		cache: make(map[string]*repository.VoiceTaskState),
	}
}

func (r *FakeVoiceCacheRepository) Get(ctx context.Context, cacheKey string) (*repository.VoiceTaskState, bool, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	s, ok := r.cache[cacheKey]
	if !ok {
		return nil, false, nil
	}
	cp := *s
	return &cp, true, nil
}

func (r *FakeVoiceCacheRepository) Set(ctx context.Context, cacheKey string, state *repository.VoiceTaskState) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if state == nil {
		return nil
	}
	cp := *state
	r.cache[cacheKey] = &cp
	return nil
}
