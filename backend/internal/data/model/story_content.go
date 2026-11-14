package model

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

// StoryContent 故事/学习材料内容
type StoryContent struct {
	ID                uint64         `gorm:"primaryKey;autoIncrement" json:"id"`
	StoryID           string         `gorm:"type:varchar(64);uniqueIndex;not null" json:"story_id"`
	AssignmentID      uint64         `gorm:"type:bigint unsigned;index;not null" json:"assignment_id"`
	QuestionID        string         `gorm:"type:varchar(64);index" json:"question_id"` // 单题生成时非空
	Title             string         `gorm:"type:varchar(200)" json:"title"`
	Summary           string         `gorm:"type:text" json:"summary"`
	Story             string         `gorm:"type:longtext;not null" json:"story"`
	Questions         StoryQuestions `gorm:"type:json" json:"questions"`
	Theme               string         `gorm:"type:varchar(100)" json:"theme"`
	IllustrationImages  StringArray   `gorm:"type:json" json:"illustration_images"`  // 漫画/插图地址列表
	IllustrationStatus  string         `gorm:"type:varchar(20);default:''" json:"illustration_status"` // pending|processing|completed|failed
	IllustrationProgress int32         `gorm:"type:int;default:0" json:"illustration_progress"`        // 插图生成进度 0-100
	CreatedAt           time.Time      `json:"created_at"`
	UpdatedAt           time.Time      `json:"updated_at"`
	DeletedAt           gorm.DeletedAt `gorm:"index" json:"-"`
}

// StoryQuestions 存储题目摘要（用于展示），兼容任意结构
type StoryQuestions []interface{}

func (s StoryQuestions) Value() (driver.Value, error) {
	if len(s) == 0 {
		return "[]", nil
	}
	return json.Marshal(s)
}

func (s *StoryQuestions) Scan(value interface{}) error {
	if value == nil {
		*s = []interface{}{}
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}
	return json.Unmarshal(bytes, s)
}

func (StoryContent) TableName() string {
	return "story_contents"
}
