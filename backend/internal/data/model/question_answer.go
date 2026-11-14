package model

import (
	"time"

	"gorm.io/gorm"
)

// QuestionAnswer 题目作答记录
type QuestionAnswer struct {
	ID           uint64         `gorm:"primaryKey;autoIncrement" json:"id"`
	AssignmentID uint64         `gorm:"type:bigint unsigned;not null;uniqueIndex:idx_assignment_question_child" json:"assignment_id"`
	QuestionID   string         `gorm:"type:varchar(64);not null;uniqueIndex:idx_assignment_question_child" json:"question_id"`
	ChildID      uint64         `gorm:"type:bigint unsigned;not null;uniqueIndex:idx_assignment_question_child;index" json:"child_id"`
	UserAnswer   string         `gorm:"type:text;not null" json:"user_answer"`
	IsCorrect    *bool          `gorm:"type:tinyint(1)" json:"is_correct"` // 有标准答案时为 true/false，无标准答案时为 null
	CreatedAt    time.Time      `json:"created_at"`
	UpdatedAt    time.Time      `json:"updated_at"`
	DeletedAt    gorm.DeletedAt `gorm:"index" json:"-"`
}

// TableName 指定表名
func (QuestionAnswer) TableName() string {
	return "question_answers"
}
