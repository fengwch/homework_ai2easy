package errors

import (
	"fmt"
)

// ErrorCode 错误码
type ErrorCode int32

const (
	// 通用错误码
	CodeSuccess ErrorCode = 0
	CodeBadRequest ErrorCode = 400
	CodeUnauthorized ErrorCode = 401
	CodeForbidden ErrorCode = 403
	CodeNotFound ErrorCode = 404
	CodeInternal ErrorCode = 500

	// 业务错误码 - 认证相关 (1000-1999)
	CodeInvalidSMS ErrorCode = 1001
	CodeSMSExpired ErrorCode = 1002
	CodePhoneExists ErrorCode = 1003
	CodePhoneNotExists ErrorCode = 1004
	CodePasswordWrong ErrorCode = 1005

	// 业务错误码 - 儿童档案相关 (2000-2999)
	CodeChildNotFound ErrorCode = 2001
	CodeMaxChildrenReached ErrorCode = 2002

	// 业务错误码 - 作业相关 (3000-3999)
	CodeAssignmentNotFound ErrorCode = 3001
	CodeScanFailed ErrorCode = 3002
	CodeImageFormatNotSupported ErrorCode = 3003
	CodeImageSizeExceeded ErrorCode = 3004
)

// Error 业务错误
type Error struct {
	Code    ErrorCode
	Message string
}

func (e *Error) Error() string {
	return fmt.Sprintf("code: %d, message: %s", e.Code, e.Message)
}

// New 创建错误
func New(code ErrorCode, message string) *Error {
	return &Error{
		Code:    code,
		Message: message,
	}
}

// Is 判断错误类型
func Is(err error, code ErrorCode) bool {
	if e, ok := err.(*Error); ok {
		return e.Code == code
	}
	return false
}
