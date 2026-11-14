package testutil

import (
	"context"
	"sync"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.StoryContentRepository = (*FakeStoryContentRepository)(nil)

// FakeStoryContentRepository 内存版 StoryContentRepository，用于单测
type FakeStoryContentRepository struct {
	mu      sync.Mutex
	byStory map[string]*model.StoryContent
}

// NewFakeStoryContentRepository 创建内存故事内容仓储
func NewFakeStoryContentRepository() *FakeStoryContentRepository {
	return &FakeStoryContentRepository{
		byStory: make(map[string]*model.StoryContent),
	}
}

func (r *FakeStoryContentRepository) Create(ctx context.Context, sc *model.StoryContent) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	c := *sc
	r.byStory[sc.StoryID] = &c
	return nil
}

func (r *FakeStoryContentRepository) FindByStoryID(ctx context.Context, storyID string) (*model.StoryContent, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	sc, ok := r.byStory[storyID]
	if !ok {
		return nil, nil
	}
	cp := *sc
	return &cp, nil
}

func (r *FakeStoryContentRepository) UpdateIllustrationImages(ctx context.Context, storyID string, images model.StringArray) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	sc, ok := r.byStory[storyID]
	if !ok {
		return nil
	}
	cp := *sc
	cp.IllustrationImages = images
	r.byStory[storyID] = &cp
	return nil
}

func (r *FakeStoryContentRepository) UpdateIllustrationStatus(ctx context.Context, storyID string, status string, images model.StringArray) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	sc, ok := r.byStory[storyID]
	if !ok {
		return nil
	}
	cp := *sc
	cp.IllustrationStatus = status
	if images != nil {
		cp.IllustrationImages = images
	}
	r.byStory[storyID] = &cp
	return nil
}
