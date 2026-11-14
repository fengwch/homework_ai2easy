package pkg

import (
	"strings"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/google/wire"
	"github.com/redis/go-redis/v9"

	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/pkg/aiagent"
	"homework_ai2easy/backend/internal/pkg/jwt"
	"homework_ai2easy/backend/internal/pkg/sms"
	"homework_ai2easy/backend/internal/pkg/wechat"
)

// ProviderSet is pkg providers.
var ProviderSet = wire.NewSet(
	NewJWT,
	NewSMSService,
	NewAiAgentClient,
	NewWechatClient,
)

// NewJWT 创建JWT实例
func NewJWT(conf *conf.JWT) *jwt.JWT {
	expiresIn := 720 * time.Hour // 默认30天
	if conf.ExpiresIn != nil {
		expiresIn = conf.ExpiresIn.AsDuration()
	}
	return jwt.NewJWT(conf.Secret, expiresIn)
}

// NewAiAgentClient 创建 AI-Agent 客户端，c 为空或 url 为空时返回未配置的客户端（调用将回退 mock）
func NewAiAgentClient(c *conf.AiAgent) *aiagent.Client {
	if c == nil {
		return aiagent.NewClient("", 0)
	}
	timeout := time.Duration(0)
	if c.Timeout != nil {
		timeout = c.Timeout.AsDuration()
	}
	return aiagent.NewClient(strings.TrimSpace(c.GetUrl()), timeout)
}

// NewWechatClient 创建微信客户端，c 为空或未配置时返回未配置的客户端
func NewWechatClient(c *conf.Wechat) *wechat.Client {
	if c == nil {
		return wechat.NewClient("", "", 0)
	}
	timeout := time.Duration(0)
	if c.Timeout != nil {
		timeout = c.Timeout.AsDuration()
	}
	return wechat.NewClient(strings.TrimSpace(c.GetAppId()), strings.TrimSpace(c.GetAppSecret()), timeout)
}

// NewSMSService 创建短信服务实例
// 参数:
//   - rdb: Redis 客户端
//   - c: SMS 配置（包含服务商、密钥等信息）
//   - logger: 日志记录器
// 返回: SMSService 实例
// 说明: 这是 Wire 依赖注入的 Provider 函数
func NewSMSService(rdb *redis.Client, c *conf.SMS, logger log.Logger) *sms.SMSService {
	return sms.NewSMSService(rdb, c, logger)
}
