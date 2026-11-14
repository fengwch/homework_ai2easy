package server

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/go-kratos/kratos/v2/log"
	"homework_ai2easy/backend/internal/pkg/ctxkey"
	"homework_ai2easy/backend/internal/pkg/jwt"
)

const (
	authHeader     = "Authorization"
	bearerPrefix   = "Bearer "
	pathPrefixAPI  = "/api/v1/"
	pathPrefixAuth = "/api/v1/auth"
)

// JWTAuthFilter 返回 JWT 鉴权 Filter：对 /api/v1/* 且非 /api/v1/auth 的请求解析 Bearer Token，
// 将 user_id 写入 context；缺 Token 或无效时返回 401 JSON。
func JWTAuthFilter(j *jwt.JWT, logger log.Logger) func(http.Handler) http.Handler {
	hlp := log.NewHelper(logger)
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			path := r.URL.Path
			if !strings.HasPrefix(path, pathPrefixAPI) || strings.HasPrefix(path, pathPrefixAuth) {
				hlp.Infow("jwt_filter", "path", path, "action", "skip_path")
				next.ServeHTTP(w, r)
				return
			}
			if r.Method == http.MethodOptions {
				hlp.Infow("jwt_filter", "path", path, "action", "skip_options")
				next.ServeHTTP(w, r)
				return
			}
			auth := r.Header.Get(authHeader)
			if auth == "" || !strings.HasPrefix(auth, bearerPrefix) {
				hlp.Warnw("jwt_filter", "path", path, "action", "reject", "reason", "no_bearer_token")
				writeJSON(w, http.StatusUnauthorized, map[string]interface{}{
					"code":    401,
					"message": "未登录或登录已过期",
				})
				return
			}
			token := strings.TrimSpace(auth[len(bearerPrefix):])
			claims, err := j.ParseToken(token)
			if err != nil {
				hlp.Warnw("jwt_filter", "path", path, "action", "reject", "reason", "parse_failed", "err", err.Error())
				writeJSON(w, http.StatusUnauthorized, map[string]interface{}{
					"code":    401,
					"message": "未登录或登录已过期",
				})
				return
			}
			hlp.Infow("jwt_filter", "path", path, "action", "pass", "user_id", claims.UserID)
			ctx := ctxkey.WithUserID(r.Context(), claims.UserID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
