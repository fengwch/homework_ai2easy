package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.QuestionAnswerRepository = (*questionAnswerDao)(nil)

type questionAnswerDao struct {
	data *Data
}

// NewQuestionAnswerRepository 创建题目作答仓储
func NewQuestionAnswerRepository(data *Data) repository.QuestionAnswerRepository {
	return &questionAnswerDao{data: data}
}

// SaveOrUpdate 保存或更新作答记录（同一作业+题目+儿童仅保留最新一条）
func (r *questionAnswerDao) SaveOrUpdate(ctx context.Context, ans *model.QuestionAnswer) error {
	var existing model.QuestionAnswer
	err := r.data.db.WithContext(ctx).
		Where("assignment_id = ? AND question_id = ? AND child_id = ?", ans.AssignmentID, ans.QuestionID, ans.ChildID).
		First(&existing).Error
	if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
		return err
	}
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return r.data.db.WithContext(ctx).Create(ans).Error
	}
	existing.UserAnswer = ans.UserAnswer
	existing.IsCorrect = ans.IsCorrect
	return r.data.db.WithContext(ctx).Save(&existing).Error
}

// ListByAssignmentAndChild 按作业ID和儿童ID获取作答记录
func (r *questionAnswerDao) ListByAssignmentAndChild(ctx context.Context, assignmentID, childID uint64) ([]*model.QuestionAnswer, error) {
	var list []*model.QuestionAnswer
	err := r.data.db.WithContext(ctx).
		Where("assignment_id = ? AND child_id = ?", assignmentID, childID).
		Order("question_id").
		Find(&list).Error
	return list, err
}

// ListByAssignmentIDsAndChild 批量获取多个作业的作答记录
func (r *questionAnswerDao) ListByAssignmentIDsAndChild(ctx context.Context, assignmentIDs []uint64, childID uint64) ([]*model.QuestionAnswer, error) {
	if len(assignmentIDs) == 0 {
		return nil, nil
	}
	var list []*model.QuestionAnswer
	err := r.data.db.WithContext(ctx).
		Where("assignment_id IN ? AND child_id = ?", assignmentIDs, childID).
		Order("assignment_id, question_id").
		Find(&list).Error
	return list, err
}
