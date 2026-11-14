package logger

import (
	"os"
	"path/filepath"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Option 用于 NewLogger / NewLoggerFromConfig 的可选参数。
type Option func(*LoggerConfig)

// WithMaxSize 设置单文件最大大小（MB）。
func WithMaxSize(n int) Option {
	return func(c *LoggerConfig) { c.MaxSize = n }
}

// WithMaxBackups 设置保留备份个数。
func WithMaxBackups(n int) Option {
	return func(c *LoggerConfig) { c.MaxBackups = n }
}

// WithMaxAge 设置保留天数。
func WithMaxAge(n int) Option {
	return func(c *LoggerConfig) { c.MaxAge = n }
}

// WithCompress 设置是否压缩历史文件。
func WithCompress(v bool) Option {
	return func(c *LoggerConfig) { c.Compress = v }
}

// WithEnableCaller 设置是否记录调用者。
func WithEnableCaller(v bool) Option {
	return func(c *LoggerConfig) { c.EnableCaller = v }
}

// WithEnableStacktrace 设置 Error 及以上是否记录堆栈。
func WithEnableStacktrace(v bool) Option {
	return func(c *LoggerConfig) { c.EnableStacktrace = v }
}

// parseLevel 将字符串解析为 zapcore.Level，无效则返回 InfoLevel。
func parseLevel(s string) zapcore.Level {
	switch s {
	case "debug":
		return zapcore.DebugLevel
	case "info":
		return zapcore.InfoLevel
	case "warn", "warning":
		return zapcore.WarnLevel
	case "error":
		return zapcore.ErrorLevel
	case "fatal":
		return zapcore.FatalLevel
	default:
		return zapcore.InfoLevel
	}
}

// NewLogger 根据显式参数创建 zap.Logger，opts 可覆盖部分配置。
// 返回 *zap.Logger 与 cleanup（Sync），调用方应在退出时 defer cleanup()。
func NewLogger(level, format, output, filePath string, opts ...Option) (*zap.Logger, func(), error) {
	cfg := LoggerConfig{
		Level:            level,
		Format:           format,
		Output:           output,
		FilePath:         filePath,
		MaxSize:          100,
		MaxBackups:       5,
		MaxAge:           30,
		Compress:         true,
		EnableCaller:     true,
		EnableStacktrace: false,
	}
	for _, o := range opts {
		o(&cfg)
	}
	return NewLoggerFromConfig(cfg)
}

// NewLoggerFromConfig 根据 LoggerConfig 创建 zap.Logger，使用 lumberjack 写文件。
// 返回 *zap.Logger 与 cleanup（Sync），调用方应在退出时 defer cleanup()。
func NewLoggerFromConfig(cfg LoggerConfig) (*zap.Logger, func(), error) {
	var ws []zapcore.WriteSyncer
	switch cfg.Output {
	case "file":
		w, err := fileWriter(cfg.FilePath, &cfg)
		if err != nil {
			return nil, nil, err
		}
		ws = append(ws, w)
	case "both":
		ws = append(ws, zapcore.AddSync(os.Stdout))
		w, err := fileWriter(cfg.FilePath, &cfg)
		if err != nil {
			return nil, nil, err
		}
		ws = append(ws, w)
	default: // stdout
		ws = append(ws, zapcore.AddSync(os.Stdout))
	}

	enc := encoder(cfg.Format)
	core := zapcore.NewCore(enc, zapcore.NewMultiWriteSyncer(ws...), parseLevel(cfg.Level))
	opts := []zap.Option{zap.AddCallerSkip(1)}
	if cfg.EnableCaller {
		opts = append(opts, zap.AddCaller())
	}
	if cfg.EnableStacktrace {
		opts = append(opts, zap.AddStacktrace(zapcore.ErrorLevel))
	}
	l := zap.New(core, opts...)
	cleanup := func() { _ = l.Sync() }
	return l, cleanup, nil
}

func fileWriter(filePath string, cfg *LoggerConfig) (zapcore.WriteSyncer, error) {
	dir := filepath.Dir(filePath)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return nil, err
		}
	}
	lj := &lumberjack.Logger{
		Filename:   filePath,
		MaxSize:    cfg.MaxSize,
		MaxBackups: cfg.MaxBackups,
		MaxAge:     cfg.MaxAge,
		Compress:   cfg.Compress,
	}
	return zapcore.AddSync(lj), nil
}

func encoder(format string) zapcore.Encoder {
	ec := zapcore.EncoderConfig{
		TimeKey:        "ts",
		LevelKey:       "level",
		CallerKey:      "caller",
		MessageKey:     "msg",
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.ISO8601TimeEncoder,
		EncodeDuration: zapcore.StringDurationEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
	}
	if format == "text" {
		return zapcore.NewConsoleEncoder(ec)
	}
	return zapcore.NewJSONEncoder(ec)
}
