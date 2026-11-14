package model

import (
	"time"

	"gorm.io/gorm"
)

// User 用户模型
type User struct {
	ID                  uint64         `gorm:"primaryKey;autoIncrement" json:"id"`
	Phone               string         `gorm:"type:varchar(20);uniqueIndex;not null" json:"phone"`
	PasswordHash        string         `gorm:"type:varchar(255);not null" json:"-"`
	Nickname            string         `gorm:"type:varchar(50)" json:"nickname"`
	AvatarURL           string         `gorm:"type:varchar(500)" json:"avatar_url"`
	WechatOpenID        string         `gorm:"column:wechat_open_id;type:varchar(100);index" json:"wechat_openid"`
	Email               string         `gorm:"type:varchar(100)" json:"email"`
	Gender              int32          `gorm:"type:tinyint;default:0" json:"gender"` // 0:未知 1:男 2:女
	Birthday            *time.Time     `gorm:"type:date" json:"birthday"`
	SubscriptionLevel   int32          `gorm:"type:tinyint;default:0" json:"subscription_level"` // 0:免费 1:基础 2:高级
	SubscriptionExpiresAt *time.Time   `gorm:"type:datetime" json:"subscription_expires_at"`
	Status              int32          `gorm:"type:tinyint;default:1" json:"status"` // 0:禁用 1:正常
	CreatedAt           time.Time      `json:"created_at"`
	UpdatedAt           time.Time      `json:"updated_at"`
	DeletedAt           gorm.DeletedAt `gorm:"index" json:"-"`
}

// TableName 指定表名
func (User) TableName() string {
	return "users"
}
