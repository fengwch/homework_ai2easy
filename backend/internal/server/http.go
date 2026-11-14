package server

import (
	"net/http"
	"path/filepath"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/middleware/recovery"
	kratosHttp "github.com/go-kratos/kratos/v2/transport/http"
	"github.com/redis/go-redis/v9"

	v1Assignment "homework_ai2easy/backend/api/assignment/v1"
	v1Auth "homework_ai2easy/backend/api/auth/v1"
	v1Child "homework_ai2easy/backend/api/child/v1"
	v1Content "homework_ai2easy/backend/api/content/v1"
	v1File "homework_ai2easy/backend/api/file/v1"
	v1User "homework_ai2easy/backend/api/user/v1"
	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/pkg/jwt"
	"homework_ai2easy/backend/internal/biz/usecase"
	grpcService "homework_ai2easy/backend/internal/service/grpc"
)

// NewHTTPServer 创建 HTTP 服务器；contentService 提供 GET /api/v1/contents/{story_id} 等学习内容接口
func NewHTTPServer(c *conf.Server, logger log.Logger,
	j *jwt.JWT,
	authService *grpcService.AuthService,
	userService *grpcService.UserService,
	childService *grpcService.ChildService,
	assignmentService *grpcService.AssignmentService,
	contentService *grpcService.ContentService,
	fileService *grpcService.FileService,
	contentUsecase *usecase.ContentUsecase,
	rdb *redis.Client,
) *kratosHttp.Server {
	var opts = []kratosHttp.ServerOption{
		kratosHttp.RequestDecoder(MultipartAwareRequestDecoder),
		kratosHttp.Middleware(
			recovery.Recovery(),
			JWTAuthMiddleware(j, logger),
		),
		kratosHttp.Filter(JWTAuthFilter(j, logger)),
	}
	// CORS：测试环境启用后前端可直连后端接口
	if c != nil && c.Cors != nil && c.Cors.GetEnabled() {
		opts = append(opts, kratosHttp.Filter(CORSFilter(c.Cors)))
		log.NewHelper(logger).Info("CORS enabled (allow_origins from config)")
	}
	// 设置监听地址
	if c.Http != nil && c.Http.Addr != "" {
		opts = append(opts, kratosHttp.Address(c.Http.Addr))
	}
	if c.Http != nil && c.Http.Timeout != nil {
		opts = append(opts, kratosHttp.Timeout(c.Http.Timeout.AsDuration()))
	}
	srv := kratosHttp.NewServer(opts...)

	// 注册 Swagger UI（需要在服务注册之前，避免路由冲突）
	openAPIPath := filepath.Join("docs", "api", "openapi.yaml")
	RegisterSwaggerUI(srv, openAPIPath)

	// 静态文件：作业上传图片
	srv.HandlePrefix("/uploads/", http.StripPrefix("/uploads", http.FileServer(http.Dir("uploads"))))

	// 注册服务
	v1Auth.RegisterAuthServiceHTTPServer(srv, authService)
	v1User.RegisterUserServiceHTTPServer(srv, userService)
	v1Child.RegisterChildServiceHTTPServer(srv, childService)
	v1Assignment.RegisterAssignmentServiceHTTPServer(srv, assignmentService)
	v1Content.RegisterContentServiceHTTPServer(srv, contentService)
	v1File.RegisterFileServiceHTTPServer(srv, fileService)
	RegisterContentRoutes(srv, logger, c, contentUsecase, rdb)

	return srv
}
