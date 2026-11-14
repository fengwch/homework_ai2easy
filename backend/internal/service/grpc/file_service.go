package grpcService

import (
	"context"
	"net/http"
	"strings"

	"github.com/go-kratos/kratos/v2/log"

	v1 "homework_ai2easy/backend/api/file/v1"
	"homework_ai2easy/backend/internal/pkg/ctxkey"
	"homework_ai2easy/backend/internal/pkg/upload"
)

var _ v1.FileServiceServer = (*FileService)(nil)
var _ v1.FileServiceHTTPServer = (*FileService)(nil)

// FileService 通用文件上传服务
type FileService struct {
	v1.UnimplementedFileServiceServer
	store *upload.LocalStore
	log   *log.Helper
}

// NewFileService 创建文件上传服务
func NewFileService(logger log.Logger) *FileService {
	return &FileService{
		store: upload.NewLocalStore(""),
		log:   log.NewHelper(logger),
	}
}

// UploadFile 通用文件上传（需登录）
func (s *FileService) UploadFile(ctx context.Context, req *v1.UploadFileRequest) (*v1.UploadFileReply, error) {
	// 认证检查
	_, ok := ctxkey.UserIDFromContext(ctx)
	if !ok {
		return &v1.UploadFileReply{Code: http.StatusUnauthorized, Message: "未登录或登录已过期"}, nil
	}

	if len(req.GetFile()) == 0 {
		return &v1.UploadFileReply{Code: http.StatusBadRequest, Message: "请上传文件"}, nil
	}

	// 从 magic bytes 推断文件名，用于 SavePublicFile 的类型检测
	filename := inferFilename(req.GetFile())

	directory := strings.TrimSpace(req.GetDirectory())

	urlPath, size, err := s.store.SavePublicFile(ctx, req.GetFile(), directory, filename)
	if err != nil {
		s.log.WithContext(ctx).Errorf("SavePublicFile failed: %v", err)
		if strings.Contains(err.Error(), "不支持的文件类型") ||
			strings.Contains(err.Error(), "非法") {
			return &v1.UploadFileReply{Code: http.StatusBadRequest, Message: err.Error()}, nil
		}
		return &v1.UploadFileReply{Code: http.StatusInternalServerError, Message: "文件保存失败"}, nil
	}

	s.log.WithContext(ctx).Infow("file uploaded",
		"size", size,
		"url", urlPath,
		"directory", directory,
	)

	return &v1.UploadFileReply{
		Code:    0,
		Message: "上传成功",
		Data: &v1.UploadFileData{
			Url:      urlPath,
			Filename: filename,
			Size:     size,
		},
	}, nil
}

// ListFiles 列出指定目录的文件（需登录）
func (s *FileService) ListFiles(ctx context.Context, req *v1.ListFilesRequest) (*v1.ListFilesReply, error) {
	_, ok := ctxkey.UserIDFromContext(ctx)
	if !ok {
		return &v1.ListFilesReply{Code: http.StatusUnauthorized, Message: "未登录或登录已过期"}, nil
	}

	directory := strings.TrimSpace(req.GetDirectory())
	dir, items, err := s.store.ListDirectory(ctx, directory)
	if err != nil {
		s.log.WithContext(ctx).Errorf("ListDirectory failed: %v", err)
		if strings.Contains(err.Error(), "非法") {
			return &v1.ListFilesReply{Code: http.StatusBadRequest, Message: err.Error()}, nil
		}
		return &v1.ListFilesReply{Code: http.StatusInternalServerError, Message: "读取目录失败"}, nil
	}

	pbItems := make([]*v1.FileItem, 0, len(items))
	for _, it := range items {
		pbItems = append(pbItems, &v1.FileItem{
			Name:    it.Name,
			Size:    it.Size,
			ModTime: it.ModTime,
			IsDir:   it.IsDir,
		})
	}

	return &v1.ListFilesReply{
		Code:    0,
		Message: "success",
		Data: &v1.ListFilesData{
			Items:     pbItems,
			Directory: dir,
		},
	}, nil
}

// inferFilename 根据 magic bytes 推断文件扩展名
func inferFilename(data []byte) string {
	if len(data) < 4 {
		return "file.bin"
	}
	switch {
	case data[0] == 0x89 && data[1] == 0x50 && data[2] == 0x4E && data[3] == 0x47:
		return "image.png"
	case data[0] == 0xFF && data[1] == 0xD8:
		return "image.jpg"
	case data[0] == 0x47 && data[1] == 0x49 && data[2] == 0x46:
		return "image.gif"
	case data[0] == 0x52 && data[1] == 0x49 && data[2] == 0x46 && data[3] == 0x46:
		return "image.webp"
	case data[0] == 0x42 && data[1] == 0x4D:
		return "image.bmp"
	case data[0] == 0x25 && data[1] == 0x50 && data[2] == 0x44 && data[3] == 0x46:
		return "document.pdf"
	case data[0] == 0x50 && data[1] == 0x4B && data[2] == 0x03 && data[3] == 0x04:
		return "archive.zip"
	default:
		return "file.bin"
	}
}
