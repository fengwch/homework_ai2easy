package usecase

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/go-kratos/kratos/v2/log"

	"homework_ai2easy/backend/internal/biz/model"
	dataModel "homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
	"homework_ai2easy/backend/internal/pkg/jwt"
	"homework_ai2easy/backend/internal/pkg/password"
	"homework_ai2easy/backend/internal/pkg/sms"
	"homework_ai2easy/backend/internal/pkg/wechat"
)

var (
	ErrUserNotFound       = errors.New("用户不存在")
	ErrUserAlreadyExists  = errors.New("用户已存在")
	ErrInvalidCode        = errors.New("验证码错误或已过期")
	ErrInvalidPassword    = errors.New("密码错误")
	ErrWechatCodeInvalid  = errors.New("登录凭证无效或已过期")
	ErrWechatNotConfigured = errors.New("微信登录未配置")
)

// AuthUsecase 认证业务用例
type AuthUsecase struct {
	userRepo     repository.UserRepository
	smsSvc       *sms.SMSService
	jwt          *jwt.JWT
	wechatClient *wechat.Client
	log          *log.Helper
	testCode     string // 测试环境万能验证码，配置后登录/注册/重置密码填此码即跳过校验
}

// NewAuthUsecase 创建认证业务用例
func NewAuthUsecase(
	userRepo repository.UserRepository,
	smsSvc *sms.SMSService,
	jwt *jwt.JWT,
	wechatClient *wechat.Client,
	logger log.Logger,
	testCode string,
) *AuthUsecase {
	return &AuthUsecase{
		userRepo:     userRepo,
		smsSvc:       smsSvc,
		jwt:          jwt,
		wechatClient: wechatClient,
		log:          log.NewHelper(logger),
		testCode:     testCode,
	}
}

// SendSMS 发送验证码
func (uc *AuthUsecase) SendSMS(ctx context.Context, phone, scene string) error {
	if scene == "" {
		scene = "login"
	}
	_, err := uc.smsSvc.SendCode(ctx, phone, scene)
	return err
}

// Login 验证码登录
func (uc *AuthUsecase) Login(ctx context.Context, phone, code string) (*model.User, string, error) {
	// 测试环境万能验证码：配置后填此码即跳过校验
	if uc.testCode != "" && code == uc.testCode {
		// 跳过 VerifyCode，直接查找或创建用户
	} else {
		valid, err := uc.smsSvc.VerifyCode(ctx, phone, code, "login")
		if err != nil {
			return nil, "", err
		}
		if !valid {
			return nil, "", ErrInvalidCode
		}
	}

	// 查找或创建用户
	user, err := uc.userRepo.FindByPhone(ctx, phone)
	if err != nil {
		return nil, "", err
	}

	if user == nil {
		// 创建新用户
		user = &dataModel.User{
			Phone:    phone,
			Nickname: fmt.Sprintf("用户%s", phone[len(phone)-4:]),
			Status:   1,
		}
		if err := uc.userRepo.Create(ctx, user); err != nil {
			return nil, "", err
		}
	}

	// 生成Token
	token, err := uc.jwt.GenerateToken(user.ID)
	if err != nil {
		return nil, "", err
	}

	return uc.toBizUser(user), token, nil
}

// WechatLogin 微信一键登录（小程序静默登录：用 code 换 openid，查/建用户，返回 token 与 userInfo）
// nickName、avatarUrl 可选，由前端通过 getUserProfile 等获取后传入，用于个人中心/列表展示
func (uc *AuthUsecase) WechatLogin(ctx context.Context, code, nickName, avatarURL string) (*model.User, string, error) {
	openID, _, err := uc.wechatClient.Code2Session(ctx, code)
	if err != nil {
		if errors.Is(err, wechat.ErrWechatNotConfigured) {
			return nil, "", ErrWechatNotConfigured
		}
		if errors.Is(err, wechat.ErrInvalidCode) {
			return nil, "", ErrWechatCodeInvalid
		}
		return nil, "", err
	}

	user, err := uc.userRepo.FindByWechatOpenID(ctx, openID)
	if err != nil {
		return nil, "", err
	}

	if user == nil {
		// 自动创建账号
		phonePlaceholder := "wx" + openID
		if len(phonePlaceholder) > 20 {
			phonePlaceholder = phonePlaceholder[:20]
		}
		hash, _ := password.HashPassword(fmt.Sprintf("wx_%d", time.Now().UnixNano()))
		nick := "微信用户"
		if nickName != "" {
			nick = nickName
		}
		user = &dataModel.User{
			Phone:        phonePlaceholder,
			PasswordHash: hash,
			Nickname:     nick,
			AvatarURL:    avatarURL,
			WechatOpenID: openID,
			Status:       1,
		}
		if err := uc.userRepo.Create(ctx, user); err != nil {
			return nil, "", err
		}
	} else {
		// 老用户：有传入头像/昵称时更新（微信头像、昵称可后续变更）
		needUpdate := false
		if nickName != "" && user.Nickname != nickName {
			user.Nickname = nickName
			needUpdate = true
		}
		if avatarURL != "" && user.AvatarURL != avatarURL {
			user.AvatarURL = avatarURL
			needUpdate = true
		}
		if needUpdate {
			_ = uc.userRepo.Update(ctx, user)
		}
	}

	token, err := uc.jwt.GenerateToken(user.ID)
	if err != nil {
		return nil, "", err
	}

	return uc.toBizUser(user), token, nil
}

// PasswordLogin 密码登录
func (uc *AuthUsecase) PasswordLogin(ctx context.Context, phone, pwd string) (*model.User, string, error) {
	user, err := uc.userRepo.FindByPhone(ctx, phone)
	if err != nil {
		return nil, "", err
	}
	if user == nil {
		return nil, "", ErrUserNotFound
	}

	// 验证密码
	if !password.CheckPassword(pwd, user.PasswordHash) {
		return nil, "", ErrInvalidPassword
	}

	// 生成Token
	token, err := uc.jwt.GenerateToken(user.ID)
	if err != nil {
		return nil, "", err
	}

	return uc.toBizUser(user), token, nil
}

// Register 注册
func (uc *AuthUsecase) Register(ctx context.Context, phone, code string, pwd *string) (*model.User, string, error) {
	if uc.testCode != "" && code == uc.testCode {
		// 测试环境万能验证码，跳过校验
	} else {
		valid, err := uc.smsSvc.VerifyCode(ctx, phone, code, "login")
		if err != nil {
			return nil, "", err
		}
		if !valid {
			return nil, "", ErrInvalidCode
		}
	}

	// 检查用户是否已存在
	existing, err := uc.userRepo.FindByPhone(ctx, phone)
	if err != nil {
		return nil, "", err
	}
	if existing != nil {
		return nil, "", ErrUserAlreadyExists
	}

	// 创建用户
	user := &dataModel.User{
		Phone:    phone,
		Nickname: fmt.Sprintf("用户%s", phone[len(phone)-4:]),
		Status:   1,
	}

	// 如果提供了密码，则加密存储
	if pwd != nil && *pwd != "" {
		hash, err := password.HashPassword(*pwd)
		if err != nil {
			return nil, "", err
		}
		user.PasswordHash = hash
	} else {
		// 如果没有密码，设置一个随机密码（用户只能使用验证码登录）
		hash, _ := password.HashPassword(fmt.Sprintf("%d", time.Now().UnixNano()))
		user.PasswordHash = hash
	}

	if err := uc.userRepo.Create(ctx, user); err != nil {
		return nil, "", err
	}

	// 生成Token
	token, err := uc.jwt.GenerateToken(user.ID)
	if err != nil {
		return nil, "", err
	}

	return uc.toBizUser(user), token, nil
}

// ResetPassword 重置密码
func (uc *AuthUsecase) ResetPassword(ctx context.Context, phone, code, newPassword string) error {
	if uc.testCode != "" && code == uc.testCode {
		// 测试环境万能验证码，跳过校验
	} else {
		valid, err := uc.smsSvc.VerifyCode(ctx, phone, code, "reset_password")
		if err != nil {
			return err
		}
		if !valid {
			return ErrInvalidCode
		}
	}

	// 查找用户
	user, err := uc.userRepo.FindByPhone(ctx, phone)
	if err != nil {
		return err
	}
	if user == nil {
		return ErrUserNotFound
	}

	// 更新密码
	hash, err := password.HashPassword(newPassword)
	if err != nil {
		return err
	}
	user.PasswordHash = hash

	return uc.userRepo.Update(ctx, user)
}

// toBizUser 转换为业务模型
func (uc *AuthUsecase) toBizUser(user *dataModel.User) *model.User {
	return &model.User{
		ID:                  user.ID,
		Phone:               user.Phone,
		Nickname:            user.Nickname,
		AvatarURL:           user.AvatarURL,
		WechatOpenID:        user.WechatOpenID,
		Email:               user.Email,
		Gender:              user.Gender,
		Birthday:            user.Birthday,
		SubscriptionLevel:   user.SubscriptionLevel,
		SubscriptionExpiresAt: user.SubscriptionExpiresAt,
		Status:              user.Status,
		CreatedAt:           user.CreatedAt,
		UpdatedAt:           user.UpdatedAt,
	}
}
