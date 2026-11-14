package usecase

import (
	"context"
	"errors"
	"time"

	"github.com/go-kratos/kratos/v2/log"

	"homework_ai2easy/backend/internal/biz/model"
	dataModel "homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
	"homework_ai2easy/backend/internal/pkg/password"
)

var (
	ErrPasswordWrong = errors.New("原密码错误")
	ErrPhoneExists   = errors.New("手机号已被使用")
)

// UserUsecase 用户业务用例
type UserUsecase struct {
	userRepo repository.UserRepository
	log      *log.Helper
}

// NewUserUsecase 创建用户业务用例
func NewUserUsecase(userRepo repository.UserRepository, logger log.Logger) *UserUsecase {
	return &UserUsecase{
		userRepo: userRepo,
		log:      log.NewHelper(logger),
	}
}

// GetProfile 获取用户信息
func (uc *UserUsecase) GetProfile(ctx context.Context, userID uint64) (*model.User, error) {
	user, err := uc.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if user == nil {
		return nil, ErrUserNotFound
	}
	return uc.toBizUser(user), nil
}

// UpdateProfile 更新用户信息
func (uc *UserUsecase) UpdateProfile(ctx context.Context, userID uint64, req *UpdateProfileRequest) (*model.User, error) {
	user, err := uc.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if user == nil {
		return nil, ErrUserNotFound
	}

	if req.Nickname != nil {
		user.Nickname = *req.Nickname
	}
	if req.AvatarURL != nil {
		user.AvatarURL = *req.AvatarURL
	}
	if req.Email != nil {
		user.Email = *req.Email
	}
	if req.Gender != nil {
		user.Gender = *req.Gender
	}
	if req.Birthday != nil {
		user.Birthday = req.Birthday
	}
	if req.Phone != nil {
		// 检查新手机号是否已被他人使用
		existing, err := uc.userRepo.FindByPhone(ctx, *req.Phone)
		if err != nil {
			return nil, err
		}
		if existing != nil && existing.ID != userID {
			return nil, ErrPhoneExists
		}
		user.Phone = *req.Phone
	}

	if err := uc.userRepo.Update(ctx, user); err != nil {
		return nil, err
	}

	return uc.toBizUser(user), nil
}

// ChangePassword 修改密码
func (uc *UserUsecase) ChangePassword(ctx context.Context, userID uint64, oldPassword, newPassword string) error {
	user, err := uc.userRepo.FindByID(ctx, userID)
	if err != nil {
		return err
	}
	if user == nil {
		return ErrUserNotFound
	}

	// 验证原密码
	if !password.CheckPassword(oldPassword, user.PasswordHash) {
		return ErrPasswordWrong
	}

	// 更新密码
	hash, err := password.HashPassword(newPassword)
	if err != nil {
		return err
	}
	user.PasswordHash = hash

	return uc.userRepo.Update(ctx, user)
}

// BindPhone 绑定手机号
func (uc *UserUsecase) BindPhone(ctx context.Context, userID uint64, phone string) error {
	// 检查手机号是否已被使用
	existing, err := uc.userRepo.FindByPhone(ctx, phone)
	if err != nil {
		return err
	}
	if existing != nil && existing.ID != userID {
		return ErrPhoneExists
	}

	user, err := uc.userRepo.FindByID(ctx, userID)
	if err != nil {
		return err
	}
	if user == nil {
		return ErrUserNotFound
	}

	user.Phone = phone
	return uc.userRepo.Update(ctx, user)
}

// GetSubscription 获取订阅信息
func (uc *UserUsecase) GetSubscription(ctx context.Context, userID uint64) (*SubscriptionInfo, error) {
	user, err := uc.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if user == nil {
		return nil, ErrUserNotFound
	}

	plan := "free"
	if user.SubscriptionLevel == 1 {
		plan = "basic"
	} else if user.SubscriptionLevel == 2 {
		plan = "premium"
	}

	status := "expired"
	if user.SubscriptionExpiresAt != nil && user.SubscriptionExpiresAt.After(time.Now()) {
		status = "active"
	}

	return &SubscriptionInfo{
		Plan:      plan,
		Status:    status,
		ExpiresAt: user.SubscriptionExpiresAt,
		Features: SubscriptionFeatures{
			UnlimitedChildren:    user.SubscriptionLevel >= 1,
			UnlimitedAssignments: user.SubscriptionLevel >= 2,
			AdvancedReports:     user.SubscriptionLevel >= 2,
		},
	}, nil
}

// UpdateProfileRequest 更新用户信息请求
type UpdateProfileRequest struct {
	Nickname  *string
	AvatarURL *string
	Email     *string
	Gender    *int32
	Birthday  *time.Time
	Phone     *string // 新手机号，修改时需已在 service 层完成验证码校验
}

// SubscriptionInfo 订阅信息
type SubscriptionInfo struct {
	Plan      string
	Status    string
	ExpiresAt *time.Time
	Features  SubscriptionFeatures
}

// SubscriptionFeatures 订阅功能
type SubscriptionFeatures struct {
	UnlimitedChildren    bool
	UnlimitedAssignments bool
	AdvancedReports      bool
}

// toBizUser 转换为业务模型
func (uc *UserUsecase) toBizUser(user *dataModel.User) *model.User {
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
