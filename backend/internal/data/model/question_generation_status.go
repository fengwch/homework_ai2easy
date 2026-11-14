package model

import (
	"time"

	"gorm.io/gorm"
)

// QuestionGenerationStatus 单题内容生成状态
type QuestionGenerationStatus struct {
	ID            uint64         `gorm:"primaryKey;autoIncrement" json:"id"`
	AssignmentID  uint64         `gorm:"type:bigint unsigned;uniqueIndex:uq_assignment_question;not null" json:"assignment_id"`
	QuestionID    string         `gorm:"type:varchar(64);uniqueIndex:uq_assignment_question;not null" json:"question_id"`
	Status        string         `gorm:"type:varchar(20);default:'pending';index" json:"status"` // pending/processing/completed/failed
	StoryID       string         `gorm:"type:varchar(64)" json:"story_id"`
	CreatedAt     time.Time      `json:"created_at"`
	UpdatedAt     time.Time      `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
}

func (QuestionGenerationStatus) TableName() string {
	return "question_generation_statuses"
}
