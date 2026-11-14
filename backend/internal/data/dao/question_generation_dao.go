package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.QuestionGenerationRepository = (*questionGenerationDao)(nil)

type questionGenerationDao struct {
	data *Data
}

// NewQuestionGenerationRepository 创建单题生成状态仓储
func NewQuestionGenerationRepository(data *Data) repository.QuestionGenerationRepository {
	return &questionGenerationDao{data: data}
}

func (r *questionGenerationDao) Create(ctx context.Context, s *model.QuestionGenerationStatus) error {
	return r.data.db.WithContext(ctx).Create(s).Error
}

func (r *questionGenerationDao) FindByAssignmentQuestion(ctx context.Context, assignmentID uint64, questionID string) (*model.QuestionGenerationStatus, error) {
	var s model.QuestionGenerationStatus
	err := r.data.db.WithContext(ctx).Where("assignment_id = ? AND question_id = ?", assignmentID, questionID).First(&s).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &s, nil
}

func (r *questionGenerationDao) ListByAssignmentID(ctx context.Context, assignmentID uint64) ([]*model.QuestionGenerationStatus, error) {
	var list []*model.QuestionGenerationStatus
	err := r.data.db.WithContext(ctx).Where("assignment_id = ?", assignmentID).Find(&list).Error
	if err != nil {
		return nil, err
	}
	return list, nil
}

func (r *questionGenerationDao) Update(ctx context.Context, s *model.QuestionGenerationStatus) error {
	return r.data.db.WithContext(ctx).Save(s).Error
}
