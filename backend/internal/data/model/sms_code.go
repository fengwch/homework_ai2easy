package model

import (
	"time"
)

// SMSCode 短信验证码模型（存储在 Redis 中）
type SMSCode struct {
	Phone     string    `json:"phone"`
	Code      string    `json:"code"`
	Scene     string    `json:"scene"` // login/reset_password
	ExpiresAt time.Time `json:"expires_at"`
}

// CacheKey 生成缓存键
func (s *SMSCode) CacheKey() string {
	return "sms:code:" + s.Phone + ":" + s.Scene
}
