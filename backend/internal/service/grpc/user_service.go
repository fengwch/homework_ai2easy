package grpcService

import (
	"context"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"google.golang.org/protobuf/types/known/emptypb"

	v1 "homework_ai2easy/backend/api/user/v1"
	"homework_ai2easy/backend/internal/biz/model"
	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/pkg/ctxkey"
	"homework_ai2easy/backend/internal/pkg/sms"
	"homework_ai2easy/backend/internal/pkg/upload"
)

var _ v1.UserServiceServer = (*UserService)(nil)
var _ v1.UserServiceHTTPServer = (*UserService)(nil)

// UserService 用户服务
type UserService struct {
	v1.UnimplementedUserServiceServer
	uc       *usecase.UserUsecase
	store    *upload.LocalStore
	smsSvc   *sms.SMSService
	testCode string
	log      *log.Helper
}

// NewUserService 创建用户服务
func NewUserService(uc *usecase.UserUsecase, smsSvc *sms.SMSService, testCode string, logger log.Logger) *UserService {
	return &UserService{
		uc:       uc,
		store:    upload.NewLocalStore(""),
		smsSvc:   smsSvc,
		testCode: testCode,
		log:      log.NewHelper(logger),
	}
}

func (s *UserService) userID(ctx context.Context) (uint64, int32, string) {
	userID, ok := ctxkey.UserIDFromContext(ctx)
	if !ok {
		return 0, 401, "未登录或登录已过期"
	}
	return userID, 0, ""
}

func (s *UserService) GetProfile(ctx context.Context, _ *emptypb.Empty) (*v1.GetProfileReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetProfileReply{Code: code, Message: msg}, nil
	}
	user, err := s.uc.GetProfile(ctx, userID)
	if err != nil {
		if err == usecase.ErrUserNotFound {
			return &v1.GetProfileReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetProfileReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.GetProfileReply{
		Code:    0,
		Message: "success",
		Data:    toProfileData(user),
	}, nil
}

func (s *UserService) UpdateProfile(ctx context.Context, req *v1.UpdateProfileRequest) (*v1.GetProfileReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetProfileReply{Code: code, Message: msg}, nil
	}
	ucReq := &usecase.UpdateProfileRequest{}
	if v := req.GetNickname(); v != "" {
		ucReq.Nickname = &v
	}
	if v := req.GetAvatarUrl(); v != "" {
		ucReq.AvatarURL = &v
	}
	if v := req.GetEmail(); v != "" {
		ucReq.Email = &v
	}
	g := req.GetGender()
	ucReq.Gender = &g
	if v := req.GetBirthday(); v != "" {
		t, err := time.Parse("2006-01-02", v)
		if err == nil {
			ucReq.Birthday = &t
		}
	}
	// 修改手机号需验证码
	if phone := req.GetPhone(); phone != "" {
		cod := req.GetCode()
		if cod == "" {
			return &v1.GetProfileReply{Code: 400, Message: "修改手机号需提供验证码"}, nil
		}
		if s.testCode != "" && cod == s.testCode {
			// 测试环境万能验证码
		} else {
			valid, err := s.smsSvc.VerifyCode(ctx, phone, cod, "bind_phone")
			if err != nil {
				return &v1.GetProfileReply{Code: 500, Message: err.Error()}, nil
			}
			if !valid {
				return &v1.GetProfileReply{Code: 1001, Message: "验证码错误或已过期"}, nil
			}
		}
		ucReq.Phone = &phone
	}
	user, err := s.uc.UpdateProfile(ctx, userID, ucReq)
	if err != nil {
		if err == usecase.ErrUserNotFound {
			return &v1.GetProfileReply{Code: 404, Message: err.Error()}, nil
		}
		if err == usecase.ErrPhoneExists {
			return &v1.GetProfileReply{Code: 1003, Message: "手机号已被使用"}, nil
		}
		return &v1.GetProfileReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.GetProfileReply{Code: 0, Message: "更新成功", Data: toProfileData(user)}, nil
}

func (s *UserService) ChangePassword(ctx context.Context, req *v1.ChangePasswordRequest) (*v1.ChangePasswordReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.ChangePasswordReply{Code: code, Message: msg}, nil
	}
	err := s.uc.ChangePassword(ctx, userID, req.GetOldPassword(), req.GetNewPassword())
	if err != nil {
		if err == usecase.ErrPasswordWrong {
			return &v1.ChangePasswordReply{Code: 1005, Message: err.Error()}, nil
		}
		if err == usecase.ErrUserNotFound {
			return &v1.ChangePasswordReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.ChangePasswordReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.ChangePasswordReply{Code: 0, Message: "密码修改成功"}, nil
}

func (s *UserService) BindPhone(ctx context.Context, req *v1.BindPhoneRequest) (*v1.BindPhoneReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.BindPhoneReply{Code: code, Message: msg}, nil
	}
	phone, cod := req.GetPhone(), req.GetCode()
	if phone == "" {
		return &v1.BindPhoneReply{Code: 400, Message: "手机号不能为空"}, nil
	}
	if s.testCode != "" && cod == s.testCode {
		// 测试环境万能验证码，跳过校验
	} else {
		valid, err := s.smsSvc.VerifyCode(ctx, phone, cod, "bind_phone")
		if err != nil {
			return &v1.BindPhoneReply{Code: 500, Message: err.Error()}, nil
		}
		if !valid {
			return &v1.BindPhoneReply{Code: 1001, Message: "验证码错误或已过期"}, nil
		}
	}
	if err := s.uc.BindPhone(ctx, userID, phone); err != nil {
		if err == usecase.ErrPhoneExists {
			return &v1.BindPhoneReply{Code: 1003, Message: "手机号已被使用"}, nil
		}
		if err == usecase.ErrUserNotFound {
			return &v1.BindPhoneReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.BindPhoneReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.BindPhoneReply{
		Code:    0,
		Message: "绑定成功",
		Data:    &v1.BindPhoneData{Phone: phone},
	}, nil
}

func (s *UserService) GetSubscription(ctx context.Context, _ *emptypb.Empty) (*v1.GetSubscriptionReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetSubscriptionReply{Code: code, Message: msg}, nil
	}
	sub, err := s.uc.GetSubscription(ctx, userID)
	if err != nil {
		if err == usecase.ErrUserNotFound {
			return &v1.GetSubscriptionReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetSubscriptionReply{Code: 500, Message: err.Error()}, nil
	}
	exp := ""
	if sub.ExpiresAt != nil {
		exp = sub.ExpiresAt.Format(time.RFC3339)
	}
	return &v1.GetSubscriptionReply{
		Code:    0,
		Message: "success",
		Data: &v1.SubscriptionData{
			Plan:      sub.Plan,
			Status:    sub.Status,
			ExpiresAt: exp,
			Features: &v1.SubscriptionFeatures{
				UnlimitedChildren:    sub.Features.UnlimitedChildren,
				UnlimitedAssignments: sub.Features.UnlimitedAssignments,
				AdvancedReports:     sub.Features.AdvancedReports,
			},
		},
	}, nil
}

func (s *UserService) UploadAvatar(ctx context.Context, req *v1.UploadAvatarRequest) (*v1.UploadAvatarReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.UploadAvatarReply{Code: code, Message: msg}, nil
	}
	if len(req.GetFile()) == 0 {
		return &v1.UploadAvatarReply{Code: 400, Message: "请上传图片文件"}, nil
	}
	filename := "image.jpg"
	if n := req.GetFile(); len(n) >= 4 {
		if n[0] == 0x89 && n[1] == 0x50 && n[2] == 0x4e {
			filename = "image.png"
		} else if len(n) >= 12 && n[0] == 0x52 && n[1] == 0x49 && n[2] == 0x46 && n[3] == 0x46 {
			filename = "image.webp"
		} else if n[0] == 0x47 && n[1] == 0x49 && n[2] == 0x46 {
			filename = "image.gif"
		}
	}
	avatarURL, err := s.store.SaveUserAvatar(ctx, userID, req.GetFile(), filename)
	if err != nil {
		s.log.WithContext(ctx).Errorf("SaveUserAvatar failed: %v", err)
		return &v1.UploadAvatarReply{Code: 500, Message: "保存图片失败"}, nil
	}
	// 若配置了可访问的 baseURL，可在此拼接；当前返回相对路径，前端需拼接
	return &v1.UploadAvatarReply{
		Code:    0,
		Message: "上传成功",
		Data: &v1.UploadAvatarData{
			AvatarUrl: avatarURL,
		},
	}, nil
}

func (s *UserService) UpdateSubscription(ctx context.Context, _ *v1.UpdateSubscriptionRequest) (*v1.UpdateSubscriptionReply, error) {
	return &v1.UpdateSubscriptionReply{Code: 500, Message: "订阅管理功能暂未实现"}, nil
}

func toProfileData(u *model.User) *v1.ProfileData {
	if u == nil {
		return nil
	}
	bd := ""
	if u.Birthday != nil {
		bd = u.Birthday.Format("2006-01-02")
	}
	return &v1.ProfileData{
		Id:        int64(u.ID),
		Phone:     u.Phone,
		Nickname:  u.Nickname,
		AvatarUrl: u.AvatarURL,
		Email:     u.Email,
		Gender:    u.Gender,
		Birthday:  bd,
		CreatedAt: formatTimeUser(u.CreatedAt),
		UpdatedAt: formatTimeUser(u.UpdatedAt),
	}
}

func formatTimeUser(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.Format(time.RFC3339)
}
