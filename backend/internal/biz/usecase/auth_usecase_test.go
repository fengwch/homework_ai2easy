package usecase

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"homework_ai2easy/backend/internal/pkg/wechat"
	"homework_ai2easy/backend/internal/testutil"
)

func newAuthUsecaseForTest(t *testing.T) (*AuthUsecase, *testutil.AuthTestDeps) {
	d := testutil.NewAuthTestDeps(t)
	uc := NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, "")
	return uc, d
}

func newAuthUsecaseForTestWithTestCode(t *testing.T, testCode string) (*AuthUsecase, *testutil.AuthTestDeps) {
	d := testutil.NewAuthTestDeps(t)
	uc := NewAuthUsecase(d.Repo, d.SMS, d.JWT, wechat.NewClient("", "", 0), d.Logger, testCode)
	return uc, d
}

func TestAuthUsecase_SendSMS(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()

	err := uc.SendSMS(ctx, "13800138000", "login")
	require.NoError(t, err)

	err = uc.SendSMS(ctx, "13800138001", "")
	require.NoError(t, err)
}

func TestAuthUsecase_Login_NewUser(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138000"

	code, err := d.SMS.SendCode(ctx, phone, "login")
	require.NoError(t, err)

	user, token, err := uc.Login(ctx, phone, code)
	require.NoError(t, err)
	require.NotEmpty(t, token)
	require.NotNil(t, user)
	assert.Equal(t, phone, user.Phone)
	assert.Contains(t, user.Nickname, "8000")
}

func TestAuthUsecase_Login_InvalidCode(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138000"

	_, _ = d.SMS.SendCode(ctx, phone, "login")

	_, _, err := uc.Login(ctx, phone, "000000")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrInvalidCode)
}

func TestAuthUsecase_Login_TestCode(t *testing.T) {
	const testCode = "123456"
	uc, d := newAuthUsecaseForTestWithTestCode(t, testCode)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800999000"

	// 未发送验证码，直接使用 test_code 登录，应成功
	user, token, err := uc.Login(ctx, phone, testCode)
	require.NoError(t, err)
	require.NotEmpty(t, token)
	require.NotNil(t, user)
	assert.Equal(t, phone, user.Phone)

	// 错误验证码仍应失败
	_, _, err = uc.Login(ctx, "13800999001", "000000")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrInvalidCode)
}

func TestAuthUsecase_Register(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138001"

	code, err := d.SMS.SendCode(ctx, phone, "login")
	require.NoError(t, err)

	pwd := "Test123456"
	user, token, err := uc.Register(ctx, phone, code, &pwd)
	require.NoError(t, err)
	require.NotEmpty(t, token)
	require.NotNil(t, user)
	assert.Equal(t, phone, user.Phone)
}

func TestAuthUsecase_Register_AlreadyExists(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138002"

	code, err := d.SMS.SendCode(ctx, phone, "login")
	require.NoError(t, err)

	_, _, err = uc.Register(ctx, phone, code, nil)
	require.NoError(t, err)

	code2, _ := d.SMS.SendCode(ctx, phone, "login")
	_, _, err = uc.Register(ctx, phone, code2, nil)
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrUserAlreadyExists)
}

func TestAuthUsecase_PasswordLogin(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138003"
	plain := "Abc12345"

	code, err := d.SMS.SendCode(ctx, phone, "login")
	require.NoError(t, err)
	_, _, err = uc.Register(ctx, phone, code, &plain)
	require.NoError(t, err)

	user, token, err := uc.PasswordLogin(ctx, phone, plain)
	require.NoError(t, err)
	require.NotEmpty(t, token)
	require.NotNil(t, user)
	assert.Equal(t, phone, user.Phone)
}

func TestAuthUsecase_PasswordLogin_NotFound(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()

	_, _, err := uc.PasswordLogin(ctx, "13900139000", "any")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrUserNotFound)
}

func TestAuthUsecase_PasswordLogin_InvalidPassword(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138004"
	code, _ := d.SMS.SendCode(ctx, phone, "login")
	_, _, _ = uc.Register(ctx, phone, code, nil)

	_, _, err := uc.PasswordLogin(ctx, phone, "wrong")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrInvalidPassword)
}

func TestAuthUsecase_ResetPassword(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138005"
	code, _ := d.SMS.SendCode(ctx, phone, "login")
	_, _, _ = uc.Register(ctx, phone, code, nil)

	codeReset, err := d.SMS.SendCode(ctx, phone, "reset_password")
	require.NoError(t, err)

	err = uc.ResetPassword(ctx, phone, codeReset, "NewPass123")
	require.NoError(t, err)

	user, token, err := uc.PasswordLogin(ctx, phone, "NewPass123")
	require.NoError(t, err)
	require.NotEmpty(t, token)
	require.NotNil(t, user)
}

func TestAuthUsecase_ResetPassword_InvalidCode(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()
	phone := "13800138006"
	code, _ := d.SMS.SendCode(ctx, phone, "login")
	_, _, _ = uc.Register(ctx, phone, code, nil)

	err := uc.ResetPassword(ctx, phone, "999999", "NewPass123")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrInvalidCode)
}

func TestAuthUsecase_ResetPassword_UserNotFound(t *testing.T) {
	uc, d := newAuthUsecaseForTest(t)
	defer d.Cleanup()
	ctx := context.Background()

	code, _ := d.SMS.SendCode(ctx, "13900139001", "reset_password")
	err := uc.ResetPassword(ctx, "13900139001", code, "NewPass123")
	require.Error(t, err)
	assert.ErrorIs(t, err, ErrUserNotFound)
}
