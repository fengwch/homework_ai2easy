package usecase

import (
	"strings"

	"github.com/google/wire"

	"homework_ai2easy/backend/internal/conf"
)

// ProviderSet is biz providers.
var ProviderSet = wire.NewSet(
	ProvideAuthTestCode,
	NewAuthUsecase,
	NewUserUsecase,
	NewChildUsecase,
	NewAssignmentUsecase,
	NewContentUsecase,
)

// ProvideAuthTestCode 从 SMS 配置提取测试环境万能验证码，未配置则返回空字符串。
func ProvideAuthTestCode(c *conf.SMS) string {
	if c == nil {
		return ""
	}
	return strings.TrimSpace(c.GetTestCode())
}
