package test

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	v1 "homework_ai2easy/backend/api/auth/v1"
	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/pkg/wechat"
	"homework_ai2easy/backend/internal/pkg/aiagent"
	grpcService "homework_ai2easy/backend/internal/service/grpc"
	"homework_ai2easy/backend/internal/server"
	"homework_ai2easy/backend/internal/testutil"
)

type sendSMSResp struct {
	Code    int32  `json:"code"`
	Message string `json:"message"`
}

type loginResp struct {
	Code    int32       `json:"code"`
	Message string      `json:"message"`
	Data    *loginData  `json:"data"`
}

type loginData struct {
	Token   string     `json:"token"`
	UserInfo *userInfo `json:"user_info"`
}

type userInfo struct {
	Id       int64  `json:"id"`
	Phone    string `json:"phone"`
	Nickname string `json:"nickname"`
}

// newAuthHTTPServer 创建仅注册 Auth 的 HTTP 测试服务（使用 testutil 依赖）
func newAuthHTTPServer(t *testing.T) (*httptest.Server, *testutil.AuthTestDeps) {
	return newAuthHTTPServerWithCORS(t, nil)
}

// newAuthHTTPServerWithCORS 创建 HTTP 测试服务；cors 非 nil 且 Enabled 时启用 CORS。
func newAuthHTTPServerWithCORS(t *testing.T, cors *conf.CORS) (*httptest.Server, *testutil.AuthTestDeps) {
	t.Helper()
	d := testutil.NewAuthTestDeps(t)
	uc := usecase.NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, "")
	authSvc := grpcService.NewAuthService(uc, d.Logger)
	userUc := usecase.NewUserUsecase(d.Repo, d.Logger)
	userSvc := grpcService.NewUserService(userUc, d.SMS, "", d.Logger)
	childRepo := testutil.NewFakeChildRepository()
	childUc := usecase.NewChildUsecase(childRepo, d.Logger)
	childSvc := grpcService.NewChildService(childUc, d.Logger)
	assignRepo := testutil.NewFakeAssignmentRepository()
	storyRepo := testutil.NewFakeStoryContentRepository()
	questionGenRepo := testutil.NewFakeQuestionGenerationRepository()
	questionAnswerRepo := testutil.NewFakeQuestionAnswerRepository()
	assignUc := usecase.NewAssignmentUsecase(assignRepo, childRepo, storyRepo, questionGenRepo, questionAnswerRepo, aiagent.NewClient("", 0), d.Logger)
	assignSvc := grpcService.NewAssignmentService(assignUc, d.Logger)
	voiceTaskRepo := testutil.NewFakeVoiceTaskRepository()
	voiceCacheRepo := testutil.NewFakeVoiceCacheRepository()
	contentUc := usecase.NewContentUsecase(storyRepo, assignRepo, questionAnswerRepo, voiceTaskRepo, voiceCacheRepo, aiagent.NewClient("", 0))
	contentSvc := grpcService.NewContentService(contentUc, d.Logger)
	cfg := &conf.Server{Http: &conf.HTTP{}, Cors: cors}
	fileSvc := grpcService.NewFileService(d.Logger)
	srv := server.NewHTTPServer(cfg, d.Logger, d.JWT, authSvc, userSvc, childSvc, assignSvc, contentSvc, fileSvc, contentUc, d.Redis)
	ts := httptest.NewServer(srv)
	return ts, d
}

func TestAuthAPI_SendSMS(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	body, _ := json.Marshal(map[string]string{"phone": "13800138000", "scene": "login"})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/send-sms", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r sendSMSResp
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
	assert.Contains(t, r.Message, "验证码")
}

func TestAuthAPI_Login(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	phone := "13800138001"
	code, err := d.SMS.SendCode(context.Background(), phone, "login")
	require.NoError(t, err)

	body, _ := json.Marshal(map[string]string{"phone": phone, "code": code})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/login", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	raw, _ := io.ReadAll(resp.Body)
	var r struct {
		Code    int32 `json:"code"`
		Message string `json:"message"`
		Data    *struct {
			Token   string `json:"token"`
			UserInfo *struct {
				Id       interface{} `json:"id"` // API 可能返回 string 或 number
				Phone    string      `json:"phone"`
				Nickname string      `json:"nickname"`
			} `json:"userInfo"`
		} `json:"data"`
	}
	require.NoError(t, json.Unmarshal(raw, &r))
	assert.Equal(t, int32(0), r.Code, "login failed: %s", r.Message)
	require.NotNil(t, r.Data, "code=0 but data nil")
	assert.NotEmpty(t, r.Data.Token)
	require.NotNil(t, r.Data.UserInfo)
	assert.Equal(t, phone, r.Data.UserInfo.Phone)
}

func TestAuthAPI_Login_InvalidCode(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	_, _ = d.SMS.SendCode(context.Background(), "13800138002", "login")

	body, _ := json.Marshal(map[string]string{"phone": "13800138002", "code": "000000"})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/login", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r loginResp
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.NotEqual(t, int32(0), r.Code)
	assert.Contains(t, r.Message, "验证码")
}

func TestAuthAPI_Register(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	phone := "13800138003"
	code, err := d.SMS.SendCode(context.Background(), phone, "login")
	require.NoError(t, err)

	body, _ := json.Marshal(map[string]string{"phone": phone, "code": code, "password": "Test123456"})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/register", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r loginResp
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
	require.NotNil(t, r.Data)
	assert.NotEmpty(t, r.Data.Token)
}

func TestAuthAPI_PasswordLogin(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	phone := "13800138004"
	pwd := "Abc12345"
	code, _ := d.SMS.SendCode(context.Background(), phone, "login")
	uc := usecase.NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, "")
	_, _, _ = uc.Register(context.Background(), phone, code, &pwd)

	body, _ := json.Marshal(map[string]string{"phone": phone, "password": pwd})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/password-login", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r loginResp
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
	require.NotNil(t, r.Data)
	assert.NotEmpty(t, r.Data.Token)
}

func TestAuthAPI_ResetPassword(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	phone := "13800138005"
	code, _ := d.SMS.SendCode(context.Background(), phone, "login")
	uc := usecase.NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, "")
	_, _, _ = uc.Register(context.Background(), phone, code, nil)

	resetCode, err := d.SMS.SendCode(context.Background(), phone, "reset_password")
	require.NoError(t, err)

	body, _ := json.Marshal(map[string]string{
		"phone":        phone,
		"code":         resetCode,
		"new_password": "NewPass123",
	})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/reset-password", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r struct {
		Code    int32  `json:"code"`
		Message string `json:"message"`
	}
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
}

func TestAuthAPI_CORS(t *testing.T) {
	t.Run("wildcard", func(t *testing.T) {
		cors := &conf.CORS{
			Enabled:      true,
			AllowOrigins: []string{"*"},
			AllowMethods: []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
			AllowHeaders: []string{"Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"},
		}
		ts, d := newAuthHTTPServerWithCORS(t, cors)
		defer ts.Close()
		defer d.Cleanup()

		opt, _ := http.NewRequestWithContext(context.Background(), http.MethodOptions, ts.URL+"/api/v1/auth/login", nil)
		opt.Header.Set("Origin", "http://localhost:3000")
		opt.Header.Set("Access-Control-Request-Method", "POST")
		opt.Header.Set("Access-Control-Request-Headers", "Content-Type,Authorization")
		resp, err := http.DefaultClient.Do(opt)
		require.NoError(t, err)
		defer resp.Body.Close()
		assert.Equal(t, http.StatusNoContent, resp.StatusCode)
		assert.Equal(t, "*", resp.Header.Get("Access-Control-Allow-Origin"))
	})

	t.Run("credentials_and_5173", func(t *testing.T) {
		cors := &conf.CORS{
			Enabled:          true,
			AllowOrigins:     []string{"http://localhost:5173", "http://127.0.0.1:5173"},
			AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
			AllowHeaders:     []string{"Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"},
			AllowCredentials: true,
		}
		ts, d := newAuthHTTPServerWithCORS(t, cors)
		defer ts.Close()
		defer d.Cleanup()

		opt, _ := http.NewRequestWithContext(context.Background(), http.MethodOptions, ts.URL+"/api/v1/auth/send-sms", nil)
		opt.Header.Set("Origin", "http://localhost:5173")
		opt.Header.Set("Access-Control-Request-Method", "POST")
		opt.Header.Set("Access-Control-Request-Headers", "Content-Type,Authorization")
		resp, err := http.DefaultClient.Do(opt)
		require.NoError(t, err)
		defer resp.Body.Close()
		assert.Equal(t, http.StatusNoContent, resp.StatusCode)
		assert.Equal(t, "http://localhost:5173", resp.Header.Get("Access-Control-Allow-Origin"))
		assert.Equal(t, "true", resp.Header.Get("Access-Control-Allow-Credentials"))

		body, _ := json.Marshal(map[string]string{"phone": "13800138007", "scene": "login"})
		post, _ := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/send-sms", bytes.NewReader(body))
		post.Header.Set("Content-Type", "application/json")
		post.Header.Set("Origin", "http://localhost:5173")
		r2, err := http.DefaultClient.Do(post)
		require.NoError(t, err)
		defer r2.Body.Close()
		assert.Equal(t, http.StatusOK, r2.StatusCode)
		assert.Equal(t, "http://localhost:5173", r2.Header.Get("Access-Control-Allow-Origin"))
		assert.Equal(t, "true", r2.Header.Get("Access-Control-Allow-Credentials"))
	})
}

func TestAuthAPI_Children_List(t *testing.T) {
	ts, d := newAuthHTTPServer(t)
	defer ts.Close()
	defer d.Cleanup()

	phone := "13800138999"
	code, err := d.SMS.SendCode(context.Background(), phone, "login")
	require.NoError(t, err)
	body, _ := json.Marshal(map[string]string{"phone": phone, "code": code})
	loginReq, _ := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/login", bytes.NewReader(body))
	loginReq.Header.Set("Content-Type", "application/json")
	loginResp, err := http.DefaultClient.Do(loginReq)
	require.NoError(t, err)
	require.Equal(t, http.StatusOK, loginResp.StatusCode)
	var lr struct {
		Code int32 `json:"code"`
		Data *struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	require.NoError(t, json.NewDecoder(loginResp.Body).Decode(&lr))
	loginResp.Body.Close()
	require.NotNil(t, lr.Data)
	require.NotEmpty(t, lr.Data.Token)

	req, err := http.NewRequestWithContext(context.Background(), http.MethodGet, ts.URL+"/api/v1/children", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+lr.Data.Token)
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r struct {
		Code    int32 `json:"code"`
		Message string `json:"message"`
		Data    []interface{} `json:"data"`
	}
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
	assert.NotNil(t, r.Data)
}

func TestAuthAPI_Login_TestCode(t *testing.T) {
	const testCode = "123456"
	d := testutil.NewAuthTestDeps(t)
	defer d.Cleanup()
	uc := usecase.NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, testCode)
	authSvc := grpcService.NewAuthService(uc, d.Logger)
	userUc := usecase.NewUserUsecase(d.Repo, d.Logger)
	userSvc := grpcService.NewUserService(userUc, d.SMS, testCode, d.Logger)
	childRepo := testutil.NewFakeChildRepository()
	childUc := usecase.NewChildUsecase(childRepo, d.Logger)
	childSvc := grpcService.NewChildService(childUc, d.Logger)
	assignRepo := testutil.NewFakeAssignmentRepository()
	storyRepo := testutil.NewFakeStoryContentRepository()
	questionGenRepo := testutil.NewFakeQuestionGenerationRepository()
	questionAnswerRepo := testutil.NewFakeQuestionAnswerRepository()
	assignUc := usecase.NewAssignmentUsecase(assignRepo, childRepo, storyRepo, questionGenRepo, questionAnswerRepo, aiagent.NewClient("", 0), d.Logger)
	assignSvc := grpcService.NewAssignmentService(assignUc, d.Logger)
	voiceTaskRepo := testutil.NewFakeVoiceTaskRepository()
	voiceCacheRepo := testutil.NewFakeVoiceCacheRepository()
	contentUc := usecase.NewContentUsecase(storyRepo, assignRepo, questionAnswerRepo, voiceTaskRepo, voiceCacheRepo, aiagent.NewClient("", 0))
	cfg := &conf.Server{Http: &conf.HTTP{}, Cors: nil}
	contentSvc := grpcService.NewContentService(contentUc, d.Logger)
	fileSvc := grpcService.NewFileService(d.Logger)
	ts := httptest.NewServer(server.NewHTTPServer(cfg, d.Logger, d.JWT, authSvc, userSvc, childSvc, assignSvc, contentSvc, fileSvc, contentUc, d.Redis))
	defer ts.Close()

	body, _ := json.Marshal(map[string]string{"phone": "13900139123", "code": testCode})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/login", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r struct {
		Code    int32  `json:"code"`
		Message string `json:"message"`
		Data    *struct {
			Token   string `json:"token"`
			UserInfo *struct {
				Id       interface{} `json:"id"`
				Phone    string      `json:"phone"`
				Nickname string      `json:"nickname"`
			} `json:"userInfo"`
		} `json:"data"`
	}
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(0), r.Code)
	require.NotNil(t, r.Data)
	assert.NotEmpty(t, r.Data.Token)
	assert.Equal(t, "13900139123", r.Data.UserInfo.Phone)
}

// TestAuthAPI_WechatLogin_NotConfigured 微信登录未配置时返回 400
func TestAuthAPI_WechatLogin_NotConfigured(t *testing.T) {
	d := testutil.NewAuthTestDeps(t)
	defer d.Cleanup()
	uc := usecase.NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, "")
	authSvc := grpcService.NewAuthService(uc, d.Logger)
	userUc := usecase.NewUserUsecase(d.Repo, d.Logger)
	userSvc := grpcService.NewUserService(userUc, d.SMS, "", d.Logger)
	childRepo := testutil.NewFakeChildRepository()
	childUc := usecase.NewChildUsecase(childRepo, d.Logger)
	childSvc := grpcService.NewChildService(childUc, d.Logger)
	assignRepo := testutil.NewFakeAssignmentRepository()
	storyRepo := testutil.NewFakeStoryContentRepository()
	questionGenRepo := testutil.NewFakeQuestionGenerationRepository()
	questionAnswerRepo := testutil.NewFakeQuestionAnswerRepository()
	assignUc := usecase.NewAssignmentUsecase(assignRepo, childRepo, storyRepo, questionGenRepo, questionAnswerRepo, aiagent.NewClient("", 0), d.Logger)
	assignSvc := grpcService.NewAssignmentService(assignUc, d.Logger)
	voiceTaskRepo := testutil.NewFakeVoiceTaskRepository()
	voiceCacheRepo := testutil.NewFakeVoiceCacheRepository()
	contentUc := usecase.NewContentUsecase(storyRepo, assignRepo, questionAnswerRepo, voiceTaskRepo, voiceCacheRepo, aiagent.NewClient("", 0))
	cfg := &conf.Server{Http: &conf.HTTP{}}
	contentSvc := grpcService.NewContentService(contentUc, d.Logger)
	fileSvc := grpcService.NewFileService(d.Logger)
	ts := httptest.NewServer(server.NewHTTPServer(cfg, d.Logger, d.JWT, authSvc, userSvc, childSvc, assignSvc, contentSvc, fileSvc, contentUc, d.Redis))
	defer ts.Close()

	body, _ := json.Marshal(map[string]string{"code": "test_code"})
	req, err := http.NewRequestWithContext(context.Background(), http.MethodPost, ts.URL+"/api/v1/auth/wechat-login", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	var r struct {
		Code    int32  `json:"code"`
		Message string `json:"message"`
	}
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&r))
	assert.Equal(t, int32(400), r.Code)
	assert.Contains(t, r.Message, "微信登录未配置")
}

// 确保 v1 包被引用（如用于生成代码）
var _ = v1.SendSMSRequest{}
