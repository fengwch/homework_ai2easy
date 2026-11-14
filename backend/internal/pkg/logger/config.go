package logger

import (
	"strings"

	"homework_ai2easy/backend/internal/conf"
)

// LoggerConfig 日志配置，用于 NewLoggerFromConfig。
type LoggerConfig struct {
	Level            string // debug, info, warn, error, fatal
	Format           string // json, text
	Output           string // stdout, file, both
	FilePath         string // 如 logs/app.log
	MaxSize          int    // MB
	MaxBackups       int
	MaxAge           int    // 天
	Compress         bool
	EnableCaller     bool
	EnableStacktrace bool
}

// DefaultConfig 返回默认 LoggerConfig。
func DefaultConfig() LoggerConfig {
	return LoggerConfig{
		Level:            "info",
		Format:           "json",
		Output:           "stdout",
		FilePath:         "logs/app.log",
		MaxSize:          100,
		MaxBackups:       5,
		MaxAge:           30,
		Compress:         true,
		EnableCaller:     true,
		EnableStacktrace: false,
	}
}

// ConfigFromProto 将 Proto 配置转为 LoggerConfig，未设置项使用 DefaultConfig 默认值。
func ConfigFromProto(c *conf.Logger) LoggerConfig {
	cfg := DefaultConfig()
	if c == nil {
		return cfg
	}
	if s := strings.TrimSpace(c.GetLevel()); s != "" {
		cfg.Level = strings.ToLower(s)
	}
	if s := strings.TrimSpace(c.GetFormat()); s != "" {
		cfg.Format = strings.ToLower(s)
	}
	if s := strings.TrimSpace(c.GetOutput()); s != "" {
		cfg.Output = strings.ToLower(s)
	}
	if s := strings.TrimSpace(c.GetFilePath()); s != "" {
		cfg.FilePath = s
	}
	if n := c.GetMaxSize(); n > 0 {
		cfg.MaxSize = int(n)
	}
	if n := c.GetMaxBackups(); n > 0 {
		cfg.MaxBackups = int(n)
	}
	if n := c.GetMaxAge(); n > 0 {
		cfg.MaxAge = int(n)
	}
	cfg.Compress = c.GetCompress()
	cfg.EnableCaller = c.GetEnableCaller()
	cfg.EnableStacktrace = c.GetEnableStacktrace()
	return cfg
}
