package testutil

import (
	"time"

	"google.golang.org/protobuf/types/known/durationpb"

	"homework_ai2easy/backend/internal/conf"
)

// TestJWTConf 返回测试用 JWT 配置
func TestJWTConf() *conf.JWT {
	return &conf.JWT{
		Secret:    "test-jwt-secret-do-not-use-in-production",
		ExpiresIn: durationpb.New(24 * time.Hour),
	}
}

// TestSMSConf 返回测试用 SMS 配置（mock 模式，不真实发短信）
func TestSMSConf() *conf.SMS {
	return &conf.SMS{
		ExpiresIn: durationpb.New(5 * time.Minute),
		Provider:  "mock",
	}
}
