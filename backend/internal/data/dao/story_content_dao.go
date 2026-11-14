package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.StoryContentRepository = (*storyContentDao)(nil)

type storyContentDao struct {
	data *Data
}

// NewStoryContentRepository 创建故事内容仓储
func NewStoryContentRepository(data *Data) repository.StoryContentRepository {
	return &storyContentDao{data: data}
}

func (r *storyContentDao) Create(ctx context.Context, sc *model.StoryContent) error {
	return r.data.db.WithContext(ctx).Create(sc).Error
}

func (r *storyContentDao) FindByStoryID(ctx context.Context, storyID string) (*model.StoryContent, error) {
	var sc model.StoryContent
	err := r.data.db.WithContext(ctx).Where("story_id = ?", storyID).First(&sc).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &sc, nil
}

func (r *storyContentDao) UpdateIllustrationImages(ctx context.Context, storyID string, images model.StringArray) error {
	if storyID == "" {
		return nil
	}
	return r.data.db.WithContext(ctx).
		Model(&model.StoryContent{}).
		Where("story_id = ?", storyID).
		Update("illustration_images", images).Error
}

func (r *storyContentDao) UpdateIllustrationStatus(ctx context.Context, storyID string, status string, images model.StringArray) error {
	if storyID == "" {
		return nil
	}
	updates := map[string]interface{}{
		"illustration_status":   status,
		"illustration_progress": illustrationProgressForStatus(status),
	}
	if images != nil {
		updates["illustration_images"] = images
	}
	return r.data.db.WithContext(ctx).
		Model(&model.StoryContent{}).
		Where("story_id = ?", storyID).
		Updates(updates).Error
}

// illustrationProgressForStatus 根据插图状态返回一个 0-100 的进度值，供前端展示。
// 约定：pending=10, processing=20, completed=100, failed=0，其它默认为 0。
func illustrationProgressForStatus(status string) int {
	switch status {
	case "pending":
		return 10
	case "processing":
		return 20
	case "completed":
		return 100
	case "failed":
		return 0
	default:
		return 0
	}
}
