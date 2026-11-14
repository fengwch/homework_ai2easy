package grpcService

import (
	"context"
	"fmt"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"google.golang.org/protobuf/types/known/emptypb"

	v1 "homework_ai2easy/backend/api/child/v1"
	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/data/model"
	"homework_ai2easy/backend/internal/pkg/ctxkey"
)

var _ v1.ChildServiceServer = (*ChildService)(nil)
var _ v1.ChildServiceHTTPServer = (*ChildService)(nil)

// ChildService 儿童档案服务
type ChildService struct {
	v1.UnimplementedChildServiceServer
	uc  *usecase.ChildUsecase
	log *log.Helper
}

// NewChildService 创建儿童档案服务
func NewChildService(uc *usecase.ChildUsecase, logger log.Logger) *ChildService {
	return &ChildService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

func (s *ChildService) userID(ctx context.Context) (uint64, int32, string) {
	userID, ok := ctxkey.UserIDFromContext(ctx)
	if !ok {
		s.log.Warnw("child_service", "action", "user_id_missing", "ctx_type", fmt.Sprintf("%T", ctx))
		return 0, 401, "未登录或登录已过期"
	}
	return userID, 0, ""
}

func (s *ChildService) ListChildren(ctx context.Context, _ *emptypb.Empty) (*v1.ListChildrenReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.ListChildrenReply{Code: code, Message: msg}, nil
	}
	list, err := s.uc.ListChildren(ctx, userID)
	if err != nil {
		return &v1.ListChildrenReply{Code: 500, Message: err.Error()}, nil
	}
	data := make([]*v1.ChildData, 0, len(list))
	for _, c := range list {
		data = append(data, toChildData(c))
	}
	return &v1.ListChildrenReply{Code: 0, Message: "success", Data: data}, nil
}

func (s *ChildService) GetChild(ctx context.Context, req *v1.GetChildRequest) (*v1.GetChildReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetChildReply{Code: code, Message: msg}, nil
	}
	child, err := s.uc.GetChild(ctx, uint64(req.GetId()))
	if err != nil {
		if err == usecase.ErrChildNotFound {
			return &v1.GetChildReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetChildReply{Code: 500, Message: err.Error()}, nil
	}
	if child.UserID != userID {
		return &v1.GetChildReply{Code: 403, Message: "无权限操作该档案"}, nil
	}
	return &v1.GetChildReply{Code: 0, Message: "success", Data: toChildData(child)}, nil
}

func (s *ChildService) CreateChild(ctx context.Context, req *v1.CreateChildRequest) (*v1.GetChildReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetChildReply{Code: code, Message: msg}, nil
	}
	ucReq := &usecase.CreateChildRequest{
		Name:            req.GetName(),
		Nickname:        req.GetNickname(),
		Gender:          req.GetGender(),
		BirthDate:       req.GetBirthDate(),
		Grade:           req.GetGrade(),
		AvatarURL:       req.GetAvatarUrl(),
		Interests:       req.GetInterests(),
		CustomInterests: req.GetCustomInterests(),
		LearningStyle:   req.GetLearningStyle(),
		AttentionSpan:   req.GetAttentionSpan(),
		WeakSubjects:    req.GetWeakSubjects(),
	}
	child, err := s.uc.CreateChild(ctx, userID, ucReq)
	if err != nil {
		if err == usecase.ErrMaxChildrenReached {
			return &v1.GetChildReply{Code: 400, Message: err.Error()}, nil
		}
		return &v1.GetChildReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.GetChildReply{Code: 0, Message: "success", Data: toChildData(child)}, nil
}

func (s *ChildService) UpdateChild(ctx context.Context, req *v1.UpdateChildRequest) (*v1.GetChildReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.GetChildReply{Code: code, Message: msg}, nil
	}
	id := uint64(req.GetId())
	child, err := s.uc.GetChild(ctx, id)
	if err != nil {
		if err == usecase.ErrChildNotFound {
			return &v1.GetChildReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.GetChildReply{Code: 500, Message: err.Error()}, nil
	}
	if child.UserID != userID {
		return &v1.GetChildReply{Code: 403, Message: "无权限操作该档案"}, nil
	}
	ucReq := &usecase.UpdateChildRequest{
		Name:            req.GetName(),
		Nickname:        req.GetNickname(),
		Gender:          req.GetGender(),
		BirthDate:       req.GetBirthDate(),
		Grade:           req.GetGrade(),
		AvatarURL:       req.GetAvatarUrl(),
		Interests:       req.GetInterests(),
		CustomInterests: req.GetCustomInterests(),
		LearningStyle:   req.GetLearningStyle(),
		AttentionSpan:   req.GetAttentionSpan(),
		WeakSubjects:    req.GetWeakSubjects(),
	}
	updated, err := s.uc.UpdateChild(ctx, id, ucReq)
	if err != nil {
		return &v1.GetChildReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.GetChildReply{Code: 0, Message: "success", Data: toChildData(updated)}, nil
}

func (s *ChildService) DeleteChild(ctx context.Context, req *v1.DeleteChildRequest) (*v1.DeleteChildReply, error) {
	userID, code, msg := s.userID(ctx)
	if code != 0 {
		return &v1.DeleteChildReply{Code: code, Message: msg}, nil
	}
	id := uint64(req.GetId())
	child, err := s.uc.GetChild(ctx, id)
	if err != nil {
		if err == usecase.ErrChildNotFound {
			return &v1.DeleteChildReply{Code: 404, Message: err.Error()}, nil
		}
		return &v1.DeleteChildReply{Code: 500, Message: err.Error()}, nil
	}
	if child.UserID != userID {
		return &v1.DeleteChildReply{Code: 403, Message: "无权限操作该档案"}, nil
	}
	if err := s.uc.DeleteChild(ctx, id); err != nil {
		return &v1.DeleteChildReply{Code: 500, Message: err.Error()}, nil
	}
	return &v1.DeleteChildReply{Code: 0, Message: "success"}, nil
}

func (s *ChildService) UploadAvatar(ctx context.Context, req *v1.UploadAvatarRequest) (*v1.UploadAvatarReply, error) {
	_, _ = req, s
	return &v1.UploadAvatarReply{
		Code:    500,
		Message: "上传儿童头像功能暂未实现",
	}, nil
}

func toChildData(c *model.Child) *v1.ChildData {
	if c == nil {
		return nil
	}
	bd := ""
	if c.BirthDate != nil {
		bd = c.BirthDate.Format("2006-01-02")
	}
	stats := &v1.LearningStats{
		TotalStudyTime:       c.LearningStats.TotalStudyTime,
		CompletedAssignments: c.LearningStats.CompletedAssignments,
		AverageScore:         c.LearningStats.AverageScore,
		LastStudyDate:        c.LearningStats.LastStudyDate,
	}
	return &v1.ChildData{
		Id:              int64(c.ID),
		Name:            c.Name,
		Nickname:        c.Nickname,
		Gender:          c.Gender,
		BirthDate:       bd,
		Grade:           c.Grade,
		AvatarUrl:       c.AvatarURL,
		Interests:       []string(c.Interests),
		CustomInterests: []string(c.CustomInterests),
		LearningStyle:   c.LearningStyle,
		AttentionSpan:   c.AttentionSpan,
		WeakSubjects:    []string(c.WeakSubjects),
		LearningStats:   stats,
		CreatedAt:       formatTime(c.CreatedAt),
		UpdatedAt:       formatTime(c.UpdatedAt),
	}
}

func formatTime(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.Format(time.RFC3339)
}
