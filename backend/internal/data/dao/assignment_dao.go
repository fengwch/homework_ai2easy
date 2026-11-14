package dao

import (
	"context"
	"errors"

	"gorm.io/gorm"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var _ repository.AssignmentRepository = (*assignmentDao)(nil)

type assignmentDao struct {
	data *Data
}

// NewAssignmentRepository 创建作业仓储
func NewAssignmentRepository(data *Data) repository.AssignmentRepository {
	return &assignmentDao{data: data}
}

func (r *assignmentDao) Create(ctx context.Context, assignment *model.Assignment) error {
	return r.data.db.WithContext(ctx).Create(assignment).Error
}

func (r *assignmentDao) FindByID(ctx context.Context, id uint64) (*model.Assignment, error) {
	var assignment model.Assignment
	err := r.data.db.WithContext(ctx).Where("id = ?", id).First(&assignment).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	return &assignment, nil
}

func (r *assignmentDao) FindByChildID(ctx context.Context, childID uint64, page, pageSize int) ([]*model.Assignment, int64, error) {
	return r.FindByChildIDWithFilters(ctx, childID, "", "", nil, page, pageSize)
}

func (r *assignmentDao) FindByChildIDWithFilters(ctx context.Context, childID uint64, status, subject string, hasAnswers *bool, page, pageSize int) ([]*model.Assignment, int64, error) {
	var assignments []*model.Assignment
	var total int64

	query := r.data.db.WithContext(ctx).Model(&model.Assignment{}).Where("child_id = ?", childID)
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if subject != "" {
		query = query.Where("subject = ?", subject)
	}
	if hasAnswers != nil {
		subQuery := r.data.db.Table("question_answers").
			Select("1").
			Where("question_answers.assignment_id = assignments.id").
			Where("question_answers.child_id = ?", childID).
			Where("question_answers.deleted_at IS NULL")
		if *hasAnswers {
			query = query.Where("EXISTS (?)", subQuery)
		} else {
			query = query.Where("NOT EXISTS (?)", subQuery)
		}
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&assignments).Error; err != nil {
		return nil, 0, err
	}

	return assignments, total, nil
}

func (r *assignmentDao) FindByStatus(ctx context.Context, status string, page, pageSize int) ([]*model.Assignment, int64, error) {
	var assignments []*model.Assignment
	var total int64

	query := r.data.db.WithContext(ctx).Model(&model.Assignment{}).Where("status = ?", status)
	
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&assignments).Error; err != nil {
		return nil, 0, err
	}

	return assignments, total, nil
}

func (r *assignmentDao) Update(ctx context.Context, assignment *model.Assignment) error {
	return r.data.db.WithContext(ctx).Save(assignment).Error
}

func (r *assignmentDao) Delete(ctx context.Context, id uint64) error {
	return r.data.db.WithContext(ctx).Delete(&model.Assignment{}, id).Error
}
