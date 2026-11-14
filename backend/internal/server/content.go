package server

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	kratosHttp "github.com/go-kratos/kratos/v2/transport/http"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"homework_ai2easy/backend/internal/biz/usecase"
	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/pkg/aiagent"
	"homework_ai2easy/backend/internal/pkg/pdf"
)

const (
	pdfDownloadKeyPrefix   = "pdf:download:"
	pdfDownloadTTL         = 10 * time.Minute // Redis 读写超时，避免受 HTTP 请求 deadline 影响
	redisOpTimeout         = 10 * time.Second
	multipartMaxMem        = 32 << 20
	uploadsStoryDir        = "uploads/story" // 导出 PDF 时上传图片的保存目录
)

// saveUploadImageToStoryDir 将导出 PDF 时上传的图片复制到 uploads/story/ 目录，文件名为 export-{token}{ext}
func saveUploadImageToStoryDir(imgPath, token string) error {
	if err := os.MkdirAll(uploadsStoryDir, 0755); err != nil {
		return fmt.Errorf("创建目录失败: %w", err)
	}
	ext := filepath.Ext(imgPath)
	if ext == "" {
		ext = ".png"
	}
	dstPath := filepath.Join(uploadsStoryDir, "export-"+token+ext)
	src, err := os.Open(imgPath)
	if err != nil {
		return fmt.Errorf("打开源图片失败: %w", err)
	}
	defer src.Close()
	dst, err := os.Create(dstPath)
	if err != nil {
		return fmt.Errorf("创建目标文件失败: %w", err)
	}
	defer dst.Close()
	if _, err := io.Copy(dst, src); err != nil {
		_ = os.Remove(dstPath)
		return fmt.Errorf("复制文件失败: %w", err)
	}
	return nil
}

// pdfDownloadBaseURL 返回用于拼 PDF 下载链接的根 URL：优先使用配置 server.api_base_url，否则用请求的 Scheme+Host，再否则兜底 your-domain.com
func pdfDownloadBaseURL(serverConf *conf.Server, req *http.Request) string {
	if serverConf != nil {
		if u := strings.TrimSuffix(strings.TrimSpace(serverConf.GetApiBaseUrl()), "/"); u != "" {
			return u
		}
	}
	if req != nil && req.URL != nil && req.URL.Scheme != "" && req.Host != "" {
		return req.URL.Scheme + "://" + req.Host
	}
	return "https://your-domain.com"
}

// RegisterContentRoutes 注册内容相关 HTTP 路由（导出 PDF、PDF 下载、语音合成等）；serverConf 可为 nil，用于读取 api_base_url 生成 PDF 下载链接
func RegisterContentRoutes(srv *kratosHttp.Server, logger log.Logger, serverConf *conf.Server, contentUsecase *usecase.ContentUsecase, rdb *redis.Client) {
	hlp := log.NewHelper(logger)
	r := srv.Route("/")

	// 学习材料导出 PDF：GET /api/v1/contents/{story_id}/pdf
	// 覆盖 proto 生成的同名路由（RegisterContentRoutes 在 http.go 的 RegisterXxxServiceHTTPServer 之后调用）
	r.GET("/api/v1/contents/{story_id}/pdf", func(ctx kratosHttp.Context) error {
		req, ok := kratosHttp.RequestFromServerContext(ctx)
		if !ok || req == nil {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "参数错误", "data": nil,
			})
		}
		storyID := ctx.Vars().Get("story_id")
		if storyID == "" {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "story_id 不能为空", "data": nil,
			})
		}

		reqCtx := context.Background()
		if req != nil {
			reqCtx = req.Context()
		}

		// 1. 查询学习材料
		sc, err := contentUsecase.GetStoryContent(reqCtx, storyID)
		if err != nil {
			hlp.Errorw("export_story_pdf get content failed", "story_id", storyID, "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "获取学习内容失败", "data": nil,
			})
		}
		if sc == nil {
			return ctx.Result(http.StatusNotFound, map[string]interface{}{
				"code": 404, "message": "学习内容不存在", "data": nil,
			})
		}

		// 2. 下载插图到临时文件
		var imgPaths []string
		var imgCleanups []func()
		for _, imgUrl := range sc.IllustrationImages {
			if imgUrl == "" {
				continue
			}
			tmpPath, cleanup, err := pdf.DownloadImageToTemp(imgUrl)
			if err != nil {
				hlp.Warnw("export_story_pdf download image failed", "url", imgUrl, "error", err.Error())
				continue // 单张图失败不阻断
			}
			imgPaths = append(imgPaths, tmpPath)
			imgCleanups = append(imgCleanups, cleanup)
		}
		defer func() {
			for _, c := range imgCleanups {
				c()
			}
		}()

		// 3. 生成 PDF
		fontPath := pdf.ResolveFontPath("")
		pdfData := &pdf.StoryPDFData{
			Title:   sc.Title,
			Summary: sc.Summary,
			Story:   sc.Story,
			Images:  imgPaths,
		}
		// 解析练习题
		for _, q := range sc.Questions {
			qMap, ok := q.(map[string]interface{})
			if !ok {
				continue
			}
			item := pdf.QuestionPDFItem{}
			if c, _ := qMap["content"].(string); c != "" {
				item.Content = c
			}
			if opts, _ := qMap["options"].([]interface{}); len(opts) > 0 {
				for _, o := range opts {
					item.Options = append(item.Options, fmt.Sprint(o))
				}
			}
			if item.Content != "" {
				pdfData.Questions = append(pdfData.Questions, item)
			}
		}

		pdfBytes, err := pdf.BuildStoryPDF(pdfData, fontPath)
		if err != nil {
			hlp.Errorw("export_story_pdf build failed", "story_id", storyID, "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}

		// 4. 写入临时文件 + Redis token 机制（复用现有 pdf-download 端点）
		token := uuid.New().String()
		tmpDir := os.TempDir()
		pdfPath := filepath.Join(tmpDir, "story-"+token+".pdf")
		if err := os.WriteFile(pdfPath, pdfBytes, 0600); err != nil {
			hlp.Errorw("export_story_pdf write temp failed", "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}
		ctxRedis, cancel := context.WithTimeout(context.Background(), redisOpTimeout)
		defer cancel()
		if err := rdb.Set(ctxRedis, pdfDownloadKeyPrefix+token, pdfPath, pdfDownloadTTL).Err(); err != nil {
			_ = os.Remove(pdfPath)
			hlp.Errorw("export_story_pdf redis set failed", "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}

		baseURL := pdfDownloadBaseURL(serverConf, req)
		url := baseURL + "/api/v1/contents/pdf/download?token=" + token
		return ctx.Result(http.StatusOK, map[string]interface{}{
			"code": 0, "message": "success", "data": map[string]interface{}{"url": url},
		})
	})

	// 语音合成：提交任务
	r.POST("/api/v1/voice/synthesize", func(ctx kratosHttp.Context) error {
		var body struct {
			Text       string  `json:"text"`
			Voice      string  `json:"voice"`
			Format     string  `json:"format"`
			SpeechRate float64 `json:"speech_rate"`
		}
		if err := ctx.Bind(&body); err != nil {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "参数错误", "data": nil,
			})
		}
		if body.Voice == "" {
			body.Voice = "xiaoyun"
		}
		if body.Format == "" {
			body.Format = "mp3"
		}
		req, _ := kratosHttp.RequestFromServerContext(ctx)
		reqCtx := context.Background()
		if req != nil {
			reqCtx = req.Context()
		}
		taskID, err := contentUsecase.SubmitVoiceTask(reqCtx, body.Text, body.Voice, body.Format)
		if err != nil {
			if errors.Is(err, aiagent.ErrNotConfigured) {
				return ctx.Result(http.StatusServiceUnavailable, map[string]interface{}{
					"code": 503, "message": "语音合成服务未配置", "data": nil,
				})
			}
			hlp.Warnw("voice_synthesize failed", "error", err.Error())
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": err.Error(), "data": nil,
			})
		}
		return ctx.Result(http.StatusOK, map[string]interface{}{
			"code": 0, "message": "success", "data": map[string]interface{}{"task_id": taskID},
		})
	})

	// 语音合成：查询任务状态（轮询）
	r.GET("/api/v1/voice/synthesize/status", func(ctx kratosHttp.Context) error {
		req, ok := kratosHttp.RequestFromServerContext(ctx)
		if !ok || req == nil {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "缺少 task_id", "data": nil,
			})
		}
		taskID := req.URL.Query().Get("task_id")
		if taskID == "" {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "缺少 task_id", "data": nil,
			})
		}
		reqCtx := req.Context()
		state, found, err := contentUsecase.GetVoiceTaskStatus(reqCtx, taskID)
		if err != nil {
			hlp.Errorw("voice_synthesize_status failed", "task_id", taskID, "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "查询失败", "data": nil,
			})
		}
		if !found || state == nil {
			return ctx.Result(http.StatusNotFound, map[string]interface{}{
				"code": 404, "message": "任务不存在或已过期", "data": nil,
			})
		}
		data := map[string]interface{}{"status": state.Status}
		if state.AudioData != "" {
			data["audio_data"] = state.AudioData
		}
		if state.Format != "" {
			data["format"] = state.Format
		}
		if state.Message != "" {
			data["message"] = state.Message
		}
		return ctx.Result(http.StatusOK, map[string]interface{}{
			"code": 0, "message": "success", "data": data,
		})
	})

	r.POST("/api/v1/contents/export-pdf-from-image", func(ctx kratosHttp.Context) error {
		req, ok := kratosHttp.RequestFromServerContext(ctx)
		if !ok || req == nil {
			hlp.Errorw("export_pdf_from_image", "reason", "RequestFromServerContext_failed")
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "解析表单失败", "data": nil,
			})
		}
		imgPath, cleanup, err := getImageFromRequest(req)
		if err != nil {
			// 打印详细原因便于排查（body 已读、boundary 错误等）
			hlp.Errorw("export_pdf_from_image parse failed",
				"path", req.URL.Path,
				"content_type", req.Header.Get("Content-Type"),
				"error", err.Error(),
				"unwrap", fmt.Sprintf("%v", errors.Unwrap(err)),
			)
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "解析表单失败", "data": nil,
			})
		}
		defer cleanup()

		token := uuid.New().String()
		// 保存上传图片到 uploads/story/，便于后续查看或复用
		if err := saveUploadImageToStoryDir(imgPath, token); err != nil {
			hlp.Warnw("export_pdf_from_image save image to uploads/story failed", "error", err.Error())
			// 不阻断流程，仅打日志
		}

		pdfBytes, err := pdf.BuildFromImage(imgPath)
		if err != nil {
			hlp.Errorw("export_pdf_from_image build failed", "path", req.URL.Path, "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}

		tmpDir := os.TempDir()
		pdfPath := filepath.Join(tmpDir, "export-"+token+".pdf")
		if err := os.WriteFile(pdfPath, pdfBytes, 0600); err != nil {
			hlp.Errorw("export_pdf_from_image write temp failed", "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}
		ctxRedis, cancel := context.WithTimeout(context.Background(), redisOpTimeout)
		defer cancel()
		if err := rdb.Set(ctxRedis, pdfDownloadKeyPrefix+token, pdfPath, pdfDownloadTTL).Err(); err != nil {
			_ = os.Remove(pdfPath)
			hlp.Errorw("export_pdf_from_image redis set failed", "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "生成 PDF 失败", "data": nil,
			})
		}

		baseURL := pdfDownloadBaseURL(serverConf, req)
		url := baseURL + "/api/v1/contents/pdf/download?token=" + token
		return ctx.Result(http.StatusOK, map[string]interface{}{
			"code": 0, "message": "success", "data": map[string]interface{}{"url": url},
		})
	})

	r.GET("/api/v1/contents/pdf/download", func(ctx kratosHttp.Context) error {
		req, ok := kratosHttp.RequestFromServerContext(ctx)
		if !ok || req == nil {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "缺少 token", "data": nil,
			})
		}
		token := req.URL.Query().Get("token")
		if token == "" {
			return ctx.Result(http.StatusBadRequest, map[string]interface{}{
				"code": 400, "message": "缺少 token", "data": nil,
			})
		}
		ctxRedis, cancel := context.WithTimeout(context.Background(), redisOpTimeout)
		defer cancel()
		pdfPath, err := rdb.Get(ctxRedis, pdfDownloadKeyPrefix+token).Result()
		if err == redis.Nil {
			return ctx.Result(http.StatusNotFound, map[string]interface{}{
				"code": 404, "message": "链接已过期或不存在", "data": nil,
			})
		}
		if err != nil {
			hlp.Errorw("pdf_download redis get failed", "token", token, "error", err.Error())
			return ctx.Result(http.StatusInternalServerError, map[string]interface{}{
				"code": 500, "message": "下载失败", "data": nil,
			})
		}
		_ = rdb.Del(ctxRedis, pdfDownloadKeyPrefix+token).Err()
		f, err := os.Open(pdfPath)
		if err != nil {
			hlp.Errorw("pdf_download open file failed", "path", pdfPath, "error", err.Error())
			return ctx.Result(http.StatusNotFound, map[string]interface{}{
				"code": 404, "message": "文件不存在", "data": nil,
			})
		}
		defer f.Close()
		ctx.Response().Header().Set("Content-Type", "application/pdf")
		ctx.Response().WriteHeader(http.StatusOK)
		_, _ = io.Copy(ctx.Response(), f)
		_ = os.Remove(pdfPath)
		return nil
	})
}

// getImageFromRequest 从请求中获取图片：支持 (1) multipart/form-data 的 image 文件 (2) application/json 的 {"image":"<base64>"}
// 返回临时文件路径、清理函数和错误；错误时已用 fmt.Errorf 包装原因，便于日志和排查。
func getImageFromRequest(r *http.Request) (imgPath string, cleanup func(), err error) {
	cleanup = func() {}
	ct := r.Header.Get("Content-Type")

	if strings.HasPrefix(ct, "application/json") {
		var body struct {
			Image string `json:"image"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			return "", cleanup, fmt.Errorf("解析 JSON 失败: %w", err)
		}
		if body.Image == "" {
			return "", cleanup, fmt.Errorf("JSON 中缺少 image 字段")
		}
		raw, err := base64.StdEncoding.DecodeString(body.Image)
		if err != nil {
			return "", cleanup, fmt.Errorf("base64 解码失败: %w", err)
		}
		tmpPath := filepath.Join(os.TempDir(), "export-img-"+uuid.New().String()+".png")
		if err := os.WriteFile(tmpPath, raw, 0600); err != nil {
			return "", cleanup, fmt.Errorf("写入临时图片失败: %w", err)
		}
		cleanup = func() { _ = os.Remove(tmpPath) }
		return tmpPath, cleanup, nil
	}

	if strings.HasPrefix(ct, "multipart/form-data") {
		if err := r.ParseMultipartForm(multipartMaxMem); err != nil {
			return "", cleanup, fmt.Errorf("ParseMultipartForm 失败: %w", err)
		}
		form := r.MultipartForm
		if form == nil {
			return "", cleanup, fmt.Errorf("MultipartForm 为空")
		}
		files := form.File["image"]
		if len(files) == 0 {
			return "", cleanup, fmt.Errorf("表单中未找到 image 文件")
		}
		fh := files[0]
		src, err := fh.Open()
		if err != nil {
			return "", cleanup, fmt.Errorf("打开上传文件失败: %w", err)
		}
		defer src.Close()
		ext := strings.ToLower(filepath.Ext(fh.Filename))
		if ext != ".png" && ext != ".jpg" && ext != ".jpeg" {
			ext = ".png"
		}
		tmpPath := filepath.Join(os.TempDir(), "export-img-"+uuid.New().String()+ext)
		dst, err := os.Create(tmpPath)
		if err != nil {
			return "", cleanup, fmt.Errorf("创建临时文件失败: %w", err)
		}
		_, err = io.Copy(dst, src)
		_ = dst.Close()
		if err != nil {
			_ = os.Remove(tmpPath)
			return "", cleanup, fmt.Errorf("保存上传文件失败: %w", err)
		}
		cleanup = func() { _ = os.Remove(tmpPath) }
		return tmpPath, cleanup, nil
	}

	return "", cleanup, fmt.Errorf("不支持的 Content-Type（需要 application/json 或 multipart/form-data）: %s", ct)
}
