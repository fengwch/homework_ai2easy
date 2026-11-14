package server

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/middleware"
	kratosHttp "github.com/go-kratos/kratos/v2/transport/http"

	"homework_ai2easy/backend/internal/pkg/ctxkey"
	"homework_ai2easy/backend/internal/pkg/jwt"
)

const (
	jwtAuthHeader      = "Authorization"
	jwtBearerPrefix    = "Bearer "
	jwtPathAPI  = "/api/v1/"
	jwtPathAuth = "/api/v1/auth"
)

// JWTAuthMiddleware 在 handler 链内从 Request 解析 JWT，将 user_id 注入 context。
// 仅对 /api/v1/* 且非 /api/v1/auth 的请求处理；其余直接 next。
// 依赖 JWTAuthFilter 已放行（已校验 Token），此处只解析并注入；若解析失败则放行，由业务按缺 user_id 返回 401。
func JWTAuthMiddleware(j *jwt.JWT, logger log.Logger) middleware.Middleware {
	hlp := log.NewHelper(logger)
	return func(next middleware.Handler) middleware.Handler {
		return func(ctx context.Context, req interface{}) (interface{}, error) {
			hr, ok := kratosHttp.RequestFromServerContext(ctx)
			if !ok {
				hlp.Warnw("jwt_middleware", "action", "skip", "reason", "RequestFromServerContext_ok_false", "ctx_type", fmt.Sprintf("%T", ctx))
				return next(ctx, req)
			}
			path := hr.URL.Path
			if !strings.HasPrefix(path, jwtPathAPI) || strings.HasPrefix(path, jwtPathAuth) {
				hlp.Infow("jwt_middleware", "path", path, "action", "skip_path")
				return next(ctx, req)
			}
			if hr.Method == http.MethodOptions {
				hlp.Infow("jwt_middleware", "path", path, "action", "skip_options")
				return next(ctx, req)
			}
			auth := hr.Header.Get(jwtAuthHeader)
			if auth == "" || !strings.HasPrefix(auth, jwtBearerPrefix) {
				hlp.Warnw("jwt_middleware", "path", path, "action", "skip", "reason", "no_bearer")
				return next(ctx, req)
			}
			token := strings.TrimSpace(auth[len(jwtBearerPrefix):])
			claims, err := j.ParseToken(token)
			if err != nil {
				hlp.Warnw("jwt_middleware", "path", path, "action", "skip", "reason", "parse_failed", "err", err.Error())
				return next(ctx, req)
			}
			ctx = ctxkey.WithUserID(ctx, claims.UserID)
			hlp.Infow("jwt_middleware", "path", path, "action", "inject_user_id", "user_id", claims.UserID)
			return next(ctx, req)
		}
	}
}
