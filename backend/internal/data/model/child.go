package model

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

// LearningStats 学习统计
type LearningStats struct {
	TotalStudyTime       int64   `json:"total_study_time"`
	CompletedAssignments int32   `json:"completed_assignments"`
	AverageScore         float32 `json:"average_score"`
	LastStudyDate        string  `json:"last_study_date"`
}

// LearningStatsValue 实现 driver.Valuer 接口
func (s LearningStats) Value() (driver.Value, error) {
	return json.Marshal(s)
}

// LearningStatsScan 实现 sql.Scanner 接口
func (s *LearningStats) Scan(value interface{}) error {
	if value == nil {
		*s = LearningStats{}
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}
	return json.Unmarshal(bytes, s)
}

// Child 儿童档案模型
type Child struct {
	ID           uint64         `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID       uint64         `gorm:"type:bigint unsigned;not null;index" json:"user_id"`
	Name         string         `gorm:"type:varchar(50);not null" json:"name"`
	Nickname     string         `gorm:"type:varchar(50)" json:"nickname"`
	Gender       int32          `gorm:"type:tinyint;default:0" json:"gender"` // 0:未知 1:男 2:女
	BirthDate    *time.Time     `gorm:"type:date" json:"birth_date"`
	Grade        string         `gorm:"type:varchar(20)" json:"grade"`
	AvatarURL    string         `gorm:"type:varchar(500)" json:"avatar_url"`
	Interests    StringArray    `gorm:"type:json" json:"interests"`
	CustomInterests StringArray `gorm:"type:json" json:"custom_interests"`
	LearningStyle string        `gorm:"type:varchar(20)" json:"learning_style"`
	AttentionSpan int32         `gorm:"type:int" json:"attention_span"` // 专注时长（分钟）
	WeakSubjects  StringArray   `gorm:"type:json" json:"weak_subjects"`
	LearningStats LearningStats `gorm:"type:json" json:"learning_stats"`
	CreatedAt     time.Time     `json:"created_at"`
	UpdatedAt     time.Time     `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
}

// TableName 指定表名
func (Child) TableName() string {
	return "children"
}
