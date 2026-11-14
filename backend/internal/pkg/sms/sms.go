package sms

import (
	"context"
	"fmt"
	"math/rand"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/redis/go-redis/v9"

	"homework_ai2easy/backend/internal/conf"
)

// SMSService 短信服务
// 支持多种短信服务商：mock（开发模式）、aliyun（阿里云）、tencent（腾讯云）、huawei（华为云）
// 开发模式下验证码会打印在日志中，不会实际发送短信
// 生产环境需要配置正式的服务商并实现对应的发送逻辑
type SMSService struct {
	rdb            *redis.Client  // Redis 客户端，用于存储验证码
	log            *log.Helper    // 日志助手
	expiresIn      time.Duration  // 验证码过期时间
	provider       string         // 短信服务商：mock/aliyun/tencent/huawei
	accessKeyID    string         // 服务商 AccessKey ID / SecretId / AK
	accessKeySecret string        // 服务商 AccessKey Secret / SecretKey / SK
	signName       string         // 短信签名（需要在服务商平台申请）
	templateCode   string         // 模板代码（需要在服务商平台申请）
	region         string         // 服务区域（如：cn-hangzhou, ap-guangzhou）
}

// NewSMSService 创建短信服务实例
// 参数:
//   - rdb: Redis 客户端，用于存储和验证验证码
//   - c: SMS 配置，包含服务商信息、密钥、签名等
//   - logger: 日志记录器
// 返回: SMSService 实例
// 说明:
//   - 如果配置为空或 provider 为空，默认使用 mock 模式（开发模式）
//   - mock 模式下验证码会打印在日志中，不会实际发送短信
//   - 生产环境需要配置 provider 为 aliyun/tencent/huawei 并填写相应的密钥信息
func NewSMSService(rdb *redis.Client, c *conf.SMS, logger log.Logger) *SMSService {
	// 默认验证码过期时间为 5 分钟
	expiresIn := 5 * time.Minute
	if c != nil && c.ExpiresIn != nil {
		expiresIn = c.ExpiresIn.AsDuration()
	}

	// 默认使用 mock 模式（开发模式，不实际发送短信）
	provider := "mock"
	accessKeyID := ""
	accessKeySecret := ""
	signName := ""
	templateCode := ""
	region := ""

	// 从配置中读取服务商信息
	if c != nil {
		if c.Provider != "" {
			provider = c.Provider
		}
		accessKeyID = c.AccessKeyId
		accessKeySecret = c.AccessKeySecret
		signName = c.SignName
		templateCode = c.TemplateCode
		region = c.Region
	}

	return &SMSService{
		rdb:            rdb,
		log:            log.NewHelper(logger),
		expiresIn:      expiresIn,
		provider:       provider,
		accessKeyID:    accessKeyID,
		accessKeySecret: accessKeySecret,
		signName:       signName,
		templateCode:   templateCode,
		region:         region,
	}
}

// SendCode 发送验证码到指定手机号
// 参数:
//   - ctx: 上下文
//   - phone: 手机号（11位）
//   - scene: 场景（login/reset_password等）
// 返回:
//   - string: 生成的验证码
//   - error: 错误信息
// 说明:
//   1. 生成6位随机验证码
//   2. 将验证码存储到 Redis，设置过期时间
//   3. 根据配置的服务商发送短信（mock 模式只打印日志）
//   4. 即使短信发送失败，验证码已存储，用户仍可使用验证码登录
func (s *SMSService) SendCode(ctx context.Context, phone, scene string) (string, error) {
	// 生成6位随机验证码（000000-999999）
	code := fmt.Sprintf("%06d", rand.Intn(1000000))
	
	// 存储到Redis，设置过期时间
	// 键格式: sms:code:{phone}:{scene}
	key := fmt.Sprintf("sms:code:%s:%s", phone, scene)
	if err := s.rdb.Set(ctx, key, code, s.expiresIn).Err(); err != nil {
		s.log.Errorf("failed to store sms code: %v", err)
		return "", err
	}

	// 根据配置的服务商发送短信
	switch s.provider {
	case "aliyun":
		// 阿里云短信服务
		if err := s.sendAliyunSMS(ctx, phone, code); err != nil {
			s.log.Errorf("failed to send aliyun sms: %v", err)
			// 注意：即使发送失败，验证码已存储，用户仍可使用验证码登录
			// 可以根据业务需求决定是否返回错误
		}
	case "tencent":
		// 腾讯云短信服务
		if err := s.sendTencentSMS(ctx, phone, code); err != nil {
			s.log.Errorf("failed to send tencent sms: %v", err)
		}
	case "huawei":
		// 华为云短信服务
		if err := s.sendHuaweiSMS(ctx, phone, code); err != nil {
			s.log.Errorf("failed to send huawei sms: %v", err)
		}
	case "mock", "":
		// 开发模式：只打印日志，不实际发送短信
		// 验证码可以在日志中查看，方便开发和测试
		s.log.Infof("[MOCK] send sms code to %s: %s (scene: %s)", phone, code, scene)
	default:
		// 未知服务商，使用 mock 模式
		s.log.Warnf("unknown sms provider: %s, using mock mode", s.provider)
		s.log.Infof("[MOCK] send sms code to %s: %s (scene: %s)", phone, code, scene)
	}

	return code, nil
}

// sendAliyunSMS 发送阿里云短信
// 参数:
//   - ctx: 上下文
//   - phone: 手机号
//   - code: 验证码
// 返回: error
// 说明:
//   - 需要安装阿里云 SDK: go get github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi
//   - 需要在阿里云平台申请签名和模板
//   - 详细配置步骤请参考: docs/sms-configuration.md
//   - 实现示例请参考: internal/pkg/sms/aliyun_example.go
func (s *SMSService) sendAliyunSMS(ctx context.Context, phone, code string) error { 
	// TODO: 实现阿里云短信发送
	// 需要安装: go get github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi
	// 参考文档: docs/sms-configuration.md
	// 参考示例: internal/pkg/sms/aliyun_example.go
	s.log.Infof("send aliyun sms to %s: %s (sign: %s, template: %s)", 
		phone, code, s.signName, s.templateCode)
	return fmt.Errorf("aliyun sms not implemented yet, please refer to docs/sms-configuration.md")
}

// sendTencentSMS 发送腾讯云短信
// 参数:
//   - ctx: 上下文
//   - phone: 手机号
//   - code: 验证码
// 返回: error
// 说明:
//   - 需要安装腾讯云 SDK: go get github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/sms/v20210111
//   - 需要在腾讯云平台申请签名和模板
//   - 详细配置步骤请参考: docs/sms-configuration.md
func (s *SMSService) sendTencentSMS(ctx context.Context, phone, code string) error {
	// TODO: 实现腾讯云短信发送
	// 需要安装: go get github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/sms/v20210111
	// 参考文档: docs/sms-configuration.md
	s.log.Infof("send tencent sms to %s: %s (sign: %s, template: %s)", 
		phone, code, s.signName, s.templateCode)
	return fmt.Errorf("tencent sms not implemented yet, please refer to docs/sms-configuration.md")
}

// sendHuaweiSMS 发送华为云短信
// 参数:
//   - ctx: 上下文
//   - phone: 手机号
//   - code: 验证码
// 返回: error
// 说明:
//   - 需要安装华为云 SDK: go get github.com/huaweicloud/huaweicloud-sdk-go-v3
//   - 需要在华为云平台申请签名和模板
//   - 详细配置步骤请参考: docs/sms-configuration.md
func (s *SMSService) sendHuaweiSMS(ctx context.Context, phone, code string) error {
	// TODO: 实现华为云短信发送
	// 需要安装: go get github.com/huaweicloud/huaweicloud-sdk-go-v3
	// 参考文档: docs/sms-configuration.md
	s.log.Infof("send huawei sms to %s: %s (sign: %s, template: %s)", 
		phone, code, s.signName, s.templateCode)
	return fmt.Errorf("huawei sms not implemented yet, please refer to docs/sms-configuration.md")
}

// VerifyCode 验证验证码是否正确
// 参数:
//   - ctx: 上下文
//   - phone: 手机号
//   - code: 用户输入的验证码
//   - scene: 场景（login/reset_password等）
// 返回:
//   - bool: true 表示验证码正确，false 表示验证码错误或已过期
//   - error: 错误信息（如 Redis 连接错误）
// 说明:
//   - 验证码验证成功后会自动删除，确保一次性使用
//   - 验证码过期后会自动从 Redis 中删除
func (s *SMSService) VerifyCode(ctx context.Context, phone, code, scene string) (bool, error) {
	// 构建 Redis 键
	key := fmt.Sprintf("sms:code:%s:%s", phone, scene)
	
	// 从 Redis 获取存储的验证码
	storedCode, err := s.rdb.Get(ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			// 验证码不存在（已过期或未发送）
			return false, nil
		}
		// Redis 连接错误
		return false, err
	}

	// 比较验证码
	if storedCode != code {
		// 验证码不匹配
		return false, nil
	}

	// 验证成功后删除验证码，确保一次性使用
	s.rdb.Del(ctx, key)

	return true, nil
}
