package server

import (
	"net/http"
	"strings"

	"homework_ai2easy/backend/internal/conf"
)

const (
	headerOrigin            = "Origin"
	headerAllowOrigin       = "Access-Control-Allow-Origin"
	headerAllowMethods      = "Access-Control-Allow-Methods"
	headerAllowHeaders      = "Access-Control-Allow-Headers"
	headerAllowCredentials  = "Access-Control-Allow-Credentials"
	headerMaxAge            = "Access-Control-Max-Age"
)

// CORSFilter 根据配置返回 CORS 用的 FilterFunc。未启用或 c 为 nil 时返回透传，不处理跨域。
func CORSFilter(c *conf.CORS) func(http.Handler) http.Handler {
	if c == nil || !c.GetEnabled() {
		return func(next http.Handler) http.Handler { return next }
	}
	origins := c.GetAllowOrigins()
	methods := c.GetAllowMethods()
	headers := c.GetAllowHeaders()
	if len(origins) == 0 {
		origins = []string{"*"}
	}
	if len(methods) == 0 {
		methods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
	}
	if len(headers) == 0 {
		headers = []string{"Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"}
	}
	allowMethods := strings.Join(methods, ", ")
	allowHeaders := strings.Join(headers, ", ")
	allowCreds := c.GetAllowCredentials()
	allowWildcard := false
	for _, o := range origins {
		if o == "*" {
			allowWildcard = true
			break
		}
	}
	// 带 credentials 时不允许 *，须用具体源
	if allowCreds && allowWildcard {
		allowWildcard = false
	}

	normalize := func(s string) string {
		s = strings.TrimSpace(s)
		for len(s) > 1 && s[len(s)-1] == '/' {
			s = s[:len(s)-1]
		}
		return s
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := normalize(r.Header.Get(headerOrigin))
			acao := ""
			if allowWildcard {
				acao = "*"
			} else if origin != "" {
				for _, o := range origins {
					if normalize(o) == origin {
						acao = r.Header.Get(headerOrigin) // 回显原始 Origin，不篡改
						break
					}
				}
			}
			if acao != "" {
				w.Header().Set(headerAllowOrigin, acao)
				w.Header().Set(headerAllowMethods, allowMethods)
				w.Header().Set(headerAllowHeaders, allowHeaders)
				w.Header().Set(headerMaxAge, "86400")
				if allowCreds {
					w.Header().Set(headerAllowCredentials, "true")
				}
			}
			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

