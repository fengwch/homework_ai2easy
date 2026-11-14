package logger

import (
	"github.com/go-kratos/kratos/v2/log"
	"github.com/google/wire"

	"homework_ai2easy/backend/internal/conf"
)

// Meta 服务元信息，用于日志固定字段。
type Meta struct {
	ID      string
	Name    string
	Version string
}

// LoggerProviderSet 供 Wire 使用；需同时提供 *conf.Logger 与 Meta。
var LoggerProviderSet = wire.NewSet(NewLoggerFromProtoConfig)

// NewLoggerFromProtoConfig 根据 Proto 配置创建 log.Logger 与 cleanup，供 Wire 或 main 使用。
// 使用 ConfigFromProto 得到 LoggerConfig，再 NewLoggerFromConfig；最后包一层 log.With(ts, caller, service.*)。
func NewLoggerFromProtoConfig(c *conf.Logger, meta Meta) (log.Logger, func(), error) {
	cfg := ConfigFromProto(c)
	z, cleanup, err := NewLoggerFromConfig(cfg)
	if err != nil {
		return nil, nil, err
	}
	base := NewKratosLogger(z)
	// ts、caller 由 zap 编码器输出；此处仅加 service 固定字段
	l := log.With(base,
		"service.id", meta.ID,
		"service.name", meta.Name,
		"service.version", meta.Version,
	)
	return l, cleanup, nil
}
