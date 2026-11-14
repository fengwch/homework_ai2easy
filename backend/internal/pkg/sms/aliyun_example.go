// +build ignore

// 这是一个示例文件，展示如何集成阿里云短信服务
// 实际使用时，请将代码集成到 sms.go 中

package sms

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi"
	"github.com/go-kratos/kratos/v2/log"
)

// sendAliyunSMS 发送阿里云短信（完整实现示例）
func (s *SMSService) sendAliyunSMS(ctx context.Context, phone, code string) error {
	// 创建客户端
	client, err := dysmsapi.NewClientWithAccessKey(s.region, s.accessKeyID, s.accessKeySecret)
	if err != nil {
		return fmt.Errorf("failed to create aliyun sms client: %w", err)
	}

	// 构建模板参数（JSON 格式）
	templateParam := map[string]string{
		"code": code,
	}
	paramBytes, err := json.Marshal(templateParam)
	if err != nil {
		return fmt.Errorf("failed to marshal template param: %w", err)
	}

	// 创建请求
	request := dysmsapi.CreateSendSmsRequest()
	request.Scheme = "https"
	request.PhoneNumbers = phone
	request.SignName = s.signName
	request.TemplateCode = s.templateCode
	request.TemplateParam = string(paramBytes)

	// 发送短信
	response, err := client.SendSms(request)
	if err != nil {
		return fmt.Errorf("failed to send sms: %w", err)
	}

	// 检查响应
	if response.Code != "OK" {
		return fmt.Errorf("aliyun sms error: code=%s, message=%s, requestId=%s",
			response.Code, response.Message, response.RequestId)
	}

	s.log.Infof("aliyun sms sent successfully: phone=%s, requestId=%s", phone, response.RequestId)
	return nil
}
