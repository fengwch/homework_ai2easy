package repository

import (
	"context"

	"homework_ai2easy/backend/internal/data/model"
)

// StoryContentRepository 故事内容仓储接口
type StoryContentRepository interface {
	Create(ctx context.Context, sc *model.StoryContent) error
	FindByStoryID(ctx context.Context, storyID string) (*model.StoryContent, error)
	// UpdateIllustrationImages 更新故事内容的插图地址列表
	UpdateIllustrationImages(ctx context.Context, storyID string, images model.StringArray) error
	// UpdateIllustrationStatus 更新插图生成状态（及完成时的图片列表）
	UpdateIllustrationStatus(ctx context.Context, storyID string, status string, images model.StringArray) error
}
