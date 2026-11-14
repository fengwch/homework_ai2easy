package server

import (
	"os"
	"path/filepath"

	kratosHttp "github.com/go-kratos/kratos/v2/transport/http"
)

// RegisterSwaggerUI 注册 Swagger UI 路由
func RegisterSwaggerUI(srv *kratosHttp.Server, openAPIPath string) {
	r := srv.Route("/")

	// 提供 OpenAPI 文档
	r.GET("/api/openapi.yaml", func(ctx kratosHttp.Context) error {
		// 尝试多个可能的路径
		paths := []string{
			openAPIPath,
			filepath.Join(".", openAPIPath),
			filepath.Join("docs", "api", "openapi.yaml"),
			"docs/api/openapi.yaml",
		}

		var content []byte
		var err error
		for _, path := range paths {
			content, err = os.ReadFile(path)
			if err == nil {
				break
			}
		}

		if err != nil {
			// 如果文件不存在，返回错误信息
			return ctx.Result(404, map[string]interface{}{
				"code":    404,
				"message": "OpenAPI document not found. Please ensure docs/api/openapi.yaml exists.",
			})
		}

		// 设置响应头
		ctx.Response().Header().Set("Content-Type", "application/yaml")
		ctx.Response().Header().Set("Access-Control-Allow-Origin", "*")
		
		// 直接写入响应体
		ctx.Response().WriteHeader(200)
		_, err = ctx.Response().Write(content)
		return err
	})

	// 提供 Swagger UI（使用 CDN 版本，更简单可靠）
	r.GET("/swagger", func(ctx kratosHttp.Context) error {
		html := getSwaggerUIHTML("/api/openapi.yaml")
		ctx.Response().Header().Set("Content-Type", "text/html; charset=utf-8")
		ctx.Response().WriteHeader(200)
		_, err := ctx.Response().Write([]byte(html))
		return err
	})
}

// getSwaggerUIHTML 返回使用 CDN 的 Swagger UI HTML
func getSwaggerUIHTML(openAPIPath string) string {
	return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>API 文档 - Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
  <style>
    html {
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }
    *, *:before, *:after {
      box-sizing: inherit;
    }
    body {
      margin:0;
      background: #fafafa;
    }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: "` + openAPIPath + `",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout",
        validatorUrl: null,
        supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
        onComplete: function() {
          console.log("Swagger UI loaded");
        }
      });
      window.ui = ui;
    }
  </script>
</body>
</html>`
}
