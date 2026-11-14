package server

import (
	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/middleware/recovery"
	"github.com/go-kratos/kratos/v2/transport/grpc"

	v1 "homework_ai2easy/backend/api/auth/v1"
	"homework_ai2easy/backend/internal/conf"
	grpcService "homework_ai2easy/backend/internal/service/grpc"
)

// NewGRPCServer 创建gRPC服务器
func NewGRPCServer(c *conf.Server, logger log.Logger,
	authService *grpcService.AuthService,
) *grpc.Server {
	var opts = []grpc.ServerOption{
		grpc.Middleware(
			recovery.Recovery(),
		),
	}
	// 设置监听地址
	if c.Grpc != nil && c.Grpc.Addr != "" {
		opts = append(opts, grpc.Address(c.Grpc.Addr))
	}
	if c.Grpc != nil && c.Grpc.Timeout != nil {
		opts = append(opts, grpc.Timeout(c.Grpc.Timeout.AsDuration()))
	}
	srv := grpc.NewServer(opts...)

	// 注册服务
	v1.RegisterAuthServiceServer(srv, authService)

	return srv
}
