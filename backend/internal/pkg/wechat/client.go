package wechat

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	code2SessionURL = "https://api.weixin.qq.com/sns/jscode2session"
	defaultTimeout  = 15 * time.Second
	retryCount      = 3
	retryInterval   = 2 * time.Second
)

// Code2SessionResp 微信 code2Session 响应
type Code2SessionResp struct {
	OpenID     string `json:"openid"`
	SessionKey string `json:"session_key"`
	UnionID    string `json:"unionid,omitempty"`
	ErrCode    int    `json:"errcode"`
	ErrMsg     string `json:"errmsg"`
}

// Client 微信小程序客户端（用于 code2Session 等）
type Client struct {
	appID      string
	appSecret  string
	httpClient *http.Client
}

// NewClient 创建微信客户端，appID 或 appSecret 为空时视为未配置
// timeout 为 0 时使用 defaultTimeout
func NewClient(appID, appSecret string, timeout time.Duration) *Client {
	if timeout <= 0 {
		timeout = defaultTimeout
	}
	return &Client{
		appID:     appID,
		appSecret: appSecret,
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

// IsConfigured 是否已配置
func (c *Client) IsConfigured() bool {
	return c.appID != "" && c.appSecret != ""
}

var ErrWechatNotConfigured = errors.New("微信登录未配置，请在 config 中设置 wechat.app_id 和 wechat.app_secret")
var ErrInvalidCode = errors.New("登录凭证无效或已过期")

func isRetryable(err error) bool {
	if err == nil {
		return false
	}
	s := strings.ToLower(err.Error())
	return strings.Contains(s, "timeout") ||
		strings.Contains(s, "deadline exceeded") ||
		strings.Contains(s, "connection refused") ||
		strings.Contains(s, "connection reset") ||
		strings.Contains(s, "tls:") ||
		strings.Contains(s, "dial tcp")
}

// Code2Session 用 code 换取 openid 和 session_key
// 参见: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
// 超时、网络错误时自动重试最多 retryCount 次
func (c *Client) Code2Session(ctx context.Context, code string) (openID, sessionKey string, err error) {
	if !c.IsConfigured() {
		return "", "", ErrWechatNotConfigured
	}
	if code == "" {
		return "", "", ErrInvalidCode
	}

	params := url.Values{}
	params.Set("appid", c.appID)
	params.Set("secret", c.appSecret)
	params.Set("js_code", code)
	params.Set("grant_type", "authorization_code")
	urlStr := code2SessionURL + "?" + params.Encode()

	var lastErr error
	for i := 0; i < retryCount; i++ {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, urlStr, nil)
		if err != nil {
			return "", "", fmt.Errorf("wechat code2session: %w", err)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if isRetryable(err) && i < retryCount-1 {
				time.Sleep(retryInterval)
				continue
			}
			return "", "", fmt.Errorf("wechat code2session: %w", err)
		}

		var r Code2SessionResp
		decErr := json.NewDecoder(resp.Body).Decode(&r)
		resp.Body.Close()
		if decErr != nil {
			return "", "", fmt.Errorf("wechat code2session 解析响应: %w", decErr)
		}

		if r.ErrCode != 0 {
			// 40029: invalid code, 40163: code been used
			return "", "", ErrInvalidCode
		}

		return r.OpenID, r.SessionKey, nil
	}

	if lastErr != nil {
		return "", "", fmt.Errorf("wechat code2session: %w", lastErr)
	}
	return "", "", ErrInvalidCode
}
