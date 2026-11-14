package usecase

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"homework_ai2easy/backend/internal/pkg/password"
	"homework_ai2easy/backend/internal/testutil"
)

func TestUserUsecase_GetProfile(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	hash, _ := password.HashPassword("old")
	id := repo.CreateForTest("13800138010", "测试用户", hash)

	user, err := uc.GetProfile(ctx, id)
	require.NoError(t, err)
	require.NotNil(t, user)
	assert.Equal(t, id, user.ID)
	assert.Equal(t, "13800138010", user.Phone)
	assert.Equal(t, "测试用户", user.Nickname)
}

func TestUserUsecase_GetProfile_NotFound(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	_, err := uc.GetProfile(ctx, 99999)
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrUserNotFound)
}

func TestUserUsecase_UpdateProfile(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	id := repo.CreateForTest("13800138011", "原名", "hash")

	nn := "新昵称"
	user, err := uc.UpdateProfile(ctx, id, &UpdateProfileRequest{Nickname: &nn})
	require.NoError(t, err)
	require.NotNil(t, user)
	assert.Equal(t, "新昵称", user.Nickname)
}

func TestUserUsecase_ChangePassword(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	old := "OldPass123"
	hash, _ := password.HashPassword(old)
	id := repo.CreateForTest("13800138012", "用户", hash)

	err := uc.ChangePassword(ctx, id, old, "NewPass456")
	require.NoError(t, err)

	u, _ := repo.FindByID(ctx, id)
	require.True(t, password.CheckPassword("NewPass456", u.PasswordHash))
}

func TestUserUsecase_ChangePassword_WrongOld(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	hash, _ := password.HashPassword("good")
	id := repo.CreateForTest("13800138013", "用户", hash)

	err := uc.ChangePassword(ctx, id, "wrong", "NewPass456")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrPasswordWrong)
}

func TestUserUsecase_BindPhone(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	id := repo.CreateForTest("13800138014", "用户", "hash")

	err := uc.BindPhone(ctx, id, "13900139014")
	require.NoError(t, err)

	u, _ := repo.FindByID(ctx, id)
	assert.Equal(t, "13900139014", u.Phone)
}

func TestUserUsecase_BindPhone_Exists(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	repo.CreateForTest("13800138015", "A", "hash")
	idB := repo.CreateForTest("13800138016", "B", "hash")

	err := uc.BindPhone(ctx, idB, "13800138015")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrPhoneExists)
}

func TestUserUsecase_GetSubscription(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	id := repo.CreateForTest("13800138017", "用户", "hash")

	sub, err := uc.GetSubscription(ctx, id)
	require.NoError(t, err)
	require.NotNil(t, sub)
	assert.Equal(t, "free", sub.Plan)
	assert.Equal(t, "expired", sub.Status)
}

func TestUserUsecase_GetSubscription_Active(t *testing.T) {
	repo := testutil.NewFakeUserRepository()
	logger := testutil.NewTestLogger(t, nil)
	uc := NewUserUsecase(repo, logger)
	ctx := context.Background()

	id := repo.CreateForTest("13800138018", "用户", "hash")
	u, _ := repo.FindByID(ctx, id)
	exp := time.Now().Add(24 * time.Hour)
	u.SubscriptionLevel = 1
	u.SubscriptionExpiresAt = &exp
	_ = repo.Update(ctx, u)

	sub, err := uc.GetSubscription(ctx, id)
	require.NoError(t, err)
	require.NotNil(t, sub)
	assert.Equal(t, "basic", sub.Plan)
	assert.Equal(t, "active", sub.Status)
}
