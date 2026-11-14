package logger

import (
	"github.com/go-kratos/kratos/v2/log"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// kratosLoggerAdapter 适配 zap.Logger 为 Kratos log.Logger，供 log.NewHelper 使用。
type kratosLoggerAdapter struct {
	zap *zap.Logger
}

// Log 实现 log.Logger，将 keyvals 转为 zap 字段并按 level 写入。
func (a *kratosLoggerAdapter) Log(level log.Level, keyvals ...interface{}) error {
	if len(keyvals)%2 != 0 {
		keyvals = append(keyvals, "")
	}
	fields := make([]zap.Field, 0, len(keyvals)/2)
	var msg string
	for i := 0; i < len(keyvals); i += 2 {
		k, _ := keyvals[i].(string)
		v := keyvals[i+1]
		if k == "msg" {
			if s, ok := v.(string); ok {
				msg = s
			}
			continue
		}
		fields = append(fields, zap.Any(k, v))
	}
	if msg == "" {
		msg = "log"
	}

	zl := levelToZap(level)
	if ce := a.zap.Check(zl, msg); ce != nil {
		ce.Write(fields...)
	}
	return nil
}

func levelToZap(l log.Level) zapcore.Level {
	switch l {
	case log.LevelDebug:
		return zapcore.DebugLevel
	case log.LevelInfo:
		return zapcore.InfoLevel
	case log.LevelWarn:
		return zapcore.WarnLevel
	case log.LevelError:
		return zapcore.ErrorLevel
	case log.LevelFatal:
		return zapcore.FatalLevel
	default:
		return zapcore.InfoLevel
	}
}

// NewKratosLogger 将 *zap.Logger 包装为 log.Logger。调用方可用 log.With 添加 ts、caller、service.* 等。
func NewKratosLogger(z *zap.Logger) log.Logger {
	return &kratosLoggerAdapter{zap: z}
}
