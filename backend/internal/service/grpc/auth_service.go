package grpcService

import (
	"context"

	"github.com/go-kratos/kratos/v2/log"

	v1 "homework_ai2easy/backend/api/auth/v1"
	"homework_ai2easy/backend/internal/biz/usecase"
)

var _ v1.AuthServiceServer = (*AuthService)(nil)
var _ v1.AuthServiceHTTPServer = (*AuthService)(nil)

// AuthService 认证服务
type AuthService struct {
	v1.UnimplementedAuthServiceServer
	uc  *usecase.AuthUsecase
	log *log.Helper
}

// NewAuthService 创建认证服务
func NewAuthService(uc *usecase.AuthUsecase, logger log.Logger) *AuthService {
	return &AuthService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

// SendSMS 发送验证码
func (s *AuthService) SendSMS(ctx context.Context, req *v1.SendSMSRequest) (*v1.SendSMSReply, error) {
	scene := req.Scene
	if scene == "" {
		scene = "login"
	}

	if err := s.uc.SendSMS(ctx, req.Phone, scene); err != nil {
		return &v1.SendSMSReply{
			Code:    500,
			Message: err.Error(),
		}, nil
	}

	return &v1.SendSMSReply{
		Code:    0,
		Message: "验证码已发送",
		Data: &v1.SendSMSData{
			ExpiresIn: 300,
		},
	}, nil
}

// Login 手机号验证码登录
func (s *AuthService) Login(ctx context.Context, req *v1.LoginRequest) (*v1.LoginReply, error) {
	user, token, err := s.uc.Login(ctx, req.Phone, req.Code)
	if err != nil {
		return &v1.LoginReply{
			Code:    1001,
			Message: err.Error(),
		}, nil
	}

	return &v1.LoginReply{
		Code:    0,
		Message: "登录成功",
		Data: &v1.LoginData{
			Token: token,
			UserInfo: &v1.UserInfo{
				Id:          int64(user.ID),
				Phone:       user.Phone,
				Nickname:    user.Nickname,
				AvatarUrl:   user.AvatarURL,
				WechatOpenid: user.WechatOpenID,
			},
		},
	}, nil
}

// PasswordLogin 密码登录
func (s *AuthService) PasswordLogin(ctx context.Context, req *v1.PasswordLoginRequest) (*v1.LoginReply, error) {
	user, token, err := s.uc.PasswordLogin(ctx, req.Phone, req.Password)
	if err != nil {
		return &v1.LoginReply{
			Code:    1005,
			Message: err.Error(),
		}, nil
	}

	return &v1.LoginReply{
		Code:    0,
		Message: "登录成功",
		Data: &v1.LoginData{
			Token: token,
			UserInfo: &v1.UserInfo{
				Id:          int64(user.ID),
				Phone:       user.Phone,
				Nickname:    user.Nickname,
				AvatarUrl:   user.AvatarURL,
				WechatOpenid: user.WechatOpenID,
			},
		},
	}, nil
}

// WechatLogin 微信一键登录（小程序静默登录：仅传 code 即可）
func (s *AuthService) WechatLogin(ctx context.Context, req *v1.WechatLoginRequest) (*v1.LoginReply, error) {
	if req.GetCode() == "" {
		return &v1.LoginReply{
			Code:    400,
			Message: "code 必填",
		}, nil
	}

	user, token, err := s.uc.WechatLogin(ctx, req.GetCode(), req.GetNickName(), req.GetAvatarUrl())
	if err != nil {
		code := int32(500)
		if err == usecase.ErrWechatCodeInvalid || err == usecase.ErrWechatNotConfigured {
			code = 400
		}
		return &v1.LoginReply{
			Code:    code,
			Message: err.Error(),
		}, nil
	}

	return &v1.LoginReply{
		Code:    0,
		Message: "登录成功",
		Data: &v1.LoginData{
			Token: token,
			UserInfo: &v1.UserInfo{
				Id:          int64(user.ID),
				Phone:       user.Phone,
				Nickname:    user.Nickname,
				AvatarUrl:   user.AvatarURL,
				WechatOpenid: user.WechatOpenID,
			},
		},
	}, nil
}



// Register 用户注册
func (s *AuthService) Register(ctx context.Context, req *v1.RegisterRequest) (*v1.LoginReply, error) {
	var pwd *string
	if req.Password != "" {
		pwd = &req.Password
	}

	user, token, err := s.uc.Register(ctx, req.Phone, req.Code, pwd)
	if err != nil {
		return &v1.LoginReply{
			Code:    1001,
			Message: err.Error(),
		}, nil
	}

	return &v1.LoginReply{
		Code:    0,
		Message: "注册成功",
		Data: &v1.LoginData{
			Token: token,
			UserInfo: &v1.UserInfo{
				Id:          int64(user.ID),
				Phone:       user.Phone,
				Nickname:    user.Nickname,
				AvatarUrl:   user.AvatarURL,
				WechatOpenid: user.WechatOpenID,
			},
		},
	}, nil
}

// Refresh 刷新Token
func (s *AuthService) Refresh(ctx context.Context, _ *v1.RefreshRequest) (*v1.RefreshReply, error) {
	// TODO: 从context中获取用户ID，重新生成token
	return &v1.RefreshReply{
		Code:    500,
		Message: "刷新Token功能暂未实现",
	}, nil
}

// ResetPassword 重置密码
func (s *AuthService) ResetPassword(ctx context.Context, req *v1.ResetPasswordRequest) (*v1.ResetPasswordReply, error) {
	if err := s.uc.ResetPassword(ctx, req.Phone, req.Code, req.NewPassword); err != nil {
		return &v1.ResetPasswordReply{
			Code:    1001,
			Message: err.Error(),
		}, nil
	}

	return &v1.ResetPasswordReply{
		Code:    0,
		Message: "密码重置成功",
	}, nil
}

