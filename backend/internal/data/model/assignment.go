package model

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

// Questions 题目数组类型
type Questions []Question

// Value 实现 driver.Valuer 接口
func (q Questions) Value() (driver.Value, error) {
	if len(q) == 0 {
		return "[]", nil
	}
	return json.Marshal(q)
}

// Scan 实现 sql.Scanner 接口
func (q *Questions) Scan(value interface{}) error {
	if value == nil {
		*q = Questions{}
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}
	return json.Unmarshal(bytes, q)
}

// Question 题目结构
type Question struct {
	ID             string          `json:"id"`
	QuestionNumber int32          `json:"question_number"`
	QuestionType   string          `json:"question_type"`
	OriginalText   string          `json:"original_text"`
	StructuredData *StructuredData `json:"structured_data,omitempty"`
	KnowledgePoints []KnowledgePoint `json:"knowledge_points,omitempty"`
	Metadata       *QuestionMetadata `json:"metadata,omitempty"`
}

// StructuredData 结构化数据
type StructuredData struct {
	Stem     string   `json:"stem"`
	Options  []Option  `json:"options,omitempty"`
	Answer   string   `json:"answer,omitempty"`
	Analysis string   `json:"analysis,omitempty"`
}

// Option 选项
type Option struct {
	Option string `json:"option"`
	Text   string `json:"text"`
}

// KnowledgePoint 知识点
type KnowledgePoint struct {
	Subject     string  `json:"subject"`
	Topic       string  `json:"topic"`
	Subtopic    string  `json:"subtopic"`
	Difficulty  string  `json:"difficulty"`
	Confidence  float32 `json:"confidence,omitempty"`
	Description string  `json:"description,omitempty"`
}

// QuestionMetadata 题目元数据
type QuestionMetadata struct {
	WordCount  int32   `json:"word_count"`
	HasImage   bool    `json:"has_image"`
	HasFormula bool    `json:"has_formula"`
	Confidence float32 `json:"confidence"`
}

// GeneratedContent 生成的内容
type GeneratedContent struct {
	StoryID string `json:"story_id"`
	Status  string `json:"status"` // pending/processing/completed/failed
}

// GeneratedContentValue 实现 driver.Valuer 接口
func (g GeneratedContent) Value() (driver.Value, error) {
	return json.Marshal(g)
}

// GeneratedContentScan 实现 sql.Scanner 接口
func (g *GeneratedContent) Scan(value interface{}) error {
	if value == nil {
		*g = GeneratedContent{}
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}
	return json.Unmarshal(bytes, g)
}

// Assignment 作业模型
type Assignment struct {
	ID              uint64           `gorm:"primaryKey;autoIncrement" json:"id"`
	ChildID         uint64           `gorm:"type:bigint unsigned;not null;index" json:"child_id"`
	Subject         string           `gorm:"type:varchar(20);not null" json:"subject"`
	Title           string           `gorm:"type:varchar(200)" json:"title"`
	OriginalImages  StringArray      `gorm:"type:json" json:"original_images"`
	Questions       Questions         `gorm:"type:json;not null" json:"questions"`
	GeneratedContent *GeneratedContent `gorm:"type:json" json:"generated_content,omitempty"`
	Status          string           `gorm:"type:varchar(20);default:'pending';index" json:"status"`
	EstimatedTime   int32            `gorm:"type:int" json:"estimated_time"`
	ActualTime      int32            `gorm:"type:int" json:"actual_time"`
	Score           *float32         `gorm:"type:decimal(5,2)" json:"score"`
	CompletedAt     *time.Time       `gorm:"type:datetime" json:"completed_at"`
	CreatedAt       time.Time        `json:"created_at"`
	UpdatedAt       time.Time        `json:"updated_at"`
	DeletedAt       gorm.DeletedAt   `gorm:"index" json:"-"`
}

// TableName 指定表名
func (Assignment) TableName() string {
	return "assignments"
}
