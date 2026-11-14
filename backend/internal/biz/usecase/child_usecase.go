package usecase

import (
	"context"
	"errors"
	"time"

	"github.com/go-kratos/kratos/v2/log"

	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/data/repository"
)

var (
	ErrChildNotFound     = errors.New("儿童档案不存在")
	ErrMaxChildrenReached = errors.New("已达到最大儿童数量限制")
)

const MaxChildrenPerUser = 3

// ChildUsecase 儿童档案业务用例
type ChildUsecase struct {
	childRepo repository.ChildRepository
	log       *log.Helper
}

// NewChildUsecase 创建儿童档案业务用例
func NewChildUsecase(childRepo repository.ChildRepository, logger log.Logger) *ChildUsecase {
	return &ChildUsecase{
		childRepo: childRepo,
		log:       log.NewHelper(logger),
	}
}

// ListChildren 获取儿童列表
func (uc *ChildUsecase) ListChildren(ctx context.Context, userID uint64) ([]*model.Child, error) {
	return uc.childRepo.FindByUserID(ctx, userID)
}

// GetChild 获取儿童详情
func (uc *ChildUsecase) GetChild(ctx context.Context, id uint64) (*model.Child, error) {
	child, err := uc.childRepo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if child == nil {
		return nil, ErrChildNotFound
	}
	return child, nil
}

// CreateChild 创建儿童档案
func (uc *ChildUsecase) CreateChild(ctx context.Context, userID uint64, req *CreateChildRequest) (*model.Child, error) {
	// 检查儿童数量限制
	count, err := uc.childRepo.CountByUserID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if count >= MaxChildrenPerUser {
		return nil, ErrMaxChildrenReached
	}

	// 合并兴趣标签
	allInterests := append(req.Interests, req.CustomInterests...)
	if len(allInterests) > 5 {
		allInterests = allInterests[:5]
	}

	var birthDate *time.Time
	if req.BirthDate != "" {
		t, err := time.Parse("2006-01-02", req.BirthDate)
		if err == nil {
			birthDate = &t
		}
	}

	child := &model.Child{
		UserID:         userID,
		Name:           req.Name,
		Nickname:       req.Nickname,
		Gender:         req.Gender,
		BirthDate:      birthDate,
		Grade:          req.Grade,
		AvatarURL:      req.AvatarURL,
		Interests:      req.Interests,
		CustomInterests: req.CustomInterests,
		LearningStyle:  req.LearningStyle,
		AttentionSpan:  req.AttentionSpan,
		WeakSubjects:   req.WeakSubjects,
		LearningStats: model.LearningStats{
			TotalStudyTime:       0,
			CompletedAssignments: 0,
			AverageScore:         0,
			LastStudyDate:        "",
		},
	}

	if err := uc.childRepo.Create(ctx, child); err != nil {
		return nil, err
	}

	return child, nil
}

// UpdateChild 更新儿童档案
func (uc *ChildUsecase) UpdateChild(ctx context.Context, id uint64, req *UpdateChildRequest) (*model.Child, error) {
	child, err := uc.childRepo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if child == nil {
		return nil, ErrChildNotFound
	}

	if req.Name != "" {
		child.Name = req.Name
	}
	if req.Nickname != "" {
		child.Nickname = req.Nickname
	}
	if req.Gender >= 0 {
		child.Gender = req.Gender
	}
	if req.BirthDate != "" {
		t, err := time.Parse("2006-01-02", req.BirthDate)
		if err == nil {
			child.BirthDate = &t
		}
	}
	if req.Grade != "" {
		child.Grade = req.Grade
	}
	if req.AvatarURL != "" {
		child.AvatarURL = req.AvatarURL
	}
	if len(req.Interests) > 0 {
		child.Interests = req.Interests
	}
	if len(req.CustomInterests) > 0 {
		child.CustomInterests = req.CustomInterests
	}
	if req.LearningStyle != "" {
		child.LearningStyle = req.LearningStyle
	}
	if req.AttentionSpan > 0 {
		child.AttentionSpan = req.AttentionSpan
	}
	if len(req.WeakSubjects) > 0 {
		child.WeakSubjects = req.WeakSubjects
	}

	if err := uc.childRepo.Update(ctx, child); err != nil {
		return nil, err
	}

	return child, nil
}

// DeleteChild 删除儿童档案
func (uc *ChildUsecase) DeleteChild(ctx context.Context, id uint64) error {
	return uc.childRepo.Delete(ctx, id)
}

// CreateChildRequest 创建儿童档案请求
type CreateChildRequest struct {
	Name            string
	Nickname        string
	Gender          int32
	BirthDate       string
	Grade           string
	AvatarURL       string
	Interests       []string
	CustomInterests []string
	LearningStyle   string
	AttentionSpan   int32
	WeakSubjects    []string
}

// UpdateChildRequest 更新儿童档案请求
type UpdateChildRequest struct {
	Name            string
	Nickname        string
	Gender          int32
	BirthDate       string
	Grade           string
	AvatarURL       string
	Interests       []string
	CustomInterests []string
	LearningStyle   string
	AttentionSpan   int32
	WeakSubjects    []string
}
