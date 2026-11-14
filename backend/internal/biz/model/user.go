package model

import "time"

// User 用户业务模型
type User struct {
	ID                  uint64
	Phone               string
	Nickname            string
	AvatarURL           string
	WechatOpenID        string
	Email               string
	Gender              int32
	Birthday            *time.Time
	SubscriptionLevel   int32
	SubscriptionExpiresAt *time.Time
	Status              int32
	CreatedAt           time.Time
	UpdatedAt           time.Time
}
