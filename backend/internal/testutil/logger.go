package testutil

import (
	"io"
	"testing"

	"github.com/go-kratos/kratos/v2/log"
)

// NewTestLogger 返回用于单测的 logger，默认写向 io.Discard。可传入 t 用于失败时输出。
func NewTestLogger(t *testing.T, w io.Writer) log.Logger {
	if w == nil {
		w = io.Discard
	}
	return log.With(log.NewStdLogger(w),
		"ts", log.DefaultTimestamp,
		"caller", log.DefaultCaller,
	)
}
