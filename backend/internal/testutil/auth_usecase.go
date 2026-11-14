package testutil

import (
	"testing"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/redis/go-redis/v9"

	"homework_ai2easy/backend/internal/pkg/jwt"
	"homework_ai2easy/backend/internal/pkg/sms"
)

// AuthTestDeps 认证用例单测依赖（不含 usecase，由调用方自行 NewAuthUsecase）
type AuthTestDeps struct {
	Redis   *redis.Client
	SMS     *sms.SMSService
	JWT     *jwt.JWT
	Repo    *FakeUserRepository
	Logger  log.Logger
	Cleanup func()
}

// NewAuthTestDeps 创建认证单测依赖（miniredis + mock SMS + JWT + fake user repo），不引用 usecase
func NewAuthTestDeps(t *testing.T) *AuthTestDeps {
	t.Helper()
	mr, rdb := NewMiniredis(t)
	logger := NewTestLogger(t, nil)
	smsSvc := sms.NewSMSService(rdb, TestSMSConf(), logger)
	jwtConf := TestJWTConf()
	exp := 24 * time.Hour
	if d := jwtConf.GetExpiresIn(); d != nil {
		exp = d.AsDuration()
	}
	j := jwt.NewJWT(jwtConf.Secret, exp)
	repo := NewFakeUserRepository()
	return &AuthTestDeps{
		Redis:   rdb,
		SMS:     smsSvc,
		JWT:     j,
		Repo:    repo,
		Logger:  logger,
		Cleanup: func() { mr.Close() },
	}
}
