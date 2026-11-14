package upload

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const uploadDir = "uploads"

// 允许上传的文件扩展名
var allowedExts = map[string]bool{
	".jpg": true, ".jpeg": true, ".png": true, ".gif": true,
	".webp": true, ".bmp": true, ".svg": true,
	".pdf": true, ".doc": true, ".docx": true,
	".xls": true, ".xlsx": true, ".ppt": true, ".pptx": true,
	".txt": true, ".csv": true, ".json": true, ".xml": true,
	".zip": true, ".tar": true, ".gz": true,
	".mp3": true, ".mp4": true, ".wav": true, ".ogg": true,
}

// LocalStore 本地文件存储
type LocalStore struct {
	BaseDir string
}

// NewLocalStore 创建本地存储，baseDir 为空时使用 "./uploads"
func NewLocalStore(baseDir string) *LocalStore {
	if baseDir == "" {
		baseDir = uploadDir
	}
	return &LocalStore{BaseDir: baseDir}
}

// SaveAssignmentImage 保存作业图片，返回可访问路径（如 /uploads/assignments/1/0.jpg）
func (s *LocalStore) SaveAssignmentImage(_ context.Context, assignmentID uint64, data []byte, filename string) (string, error) {
	ext := filepath.Ext(filename)
	if ext == "" {
		ext = ".jpg"
	}
	relPath := filepath.Join("assignments", fmt.Sprintf("%d", assignmentID), "0"+ext)
	fullPath := filepath.Join(s.BaseDir, relPath)
	dir := filepath.Dir(fullPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	if err := os.WriteFile(fullPath, data, 0644); err != nil {
		return "", err
	}
	// 返回 URL 路径，供前端拼接 baseURL
	return "/" + filepath.ToSlash(filepath.Join(uploadDir, relPath)), nil
}

// SaveUserAvatar 保存用户头像，返回可访问路径（如 /uploads/users/1/avatar.jpg）
func (s *LocalStore) SaveUserAvatar(_ context.Context, userID uint64, data []byte, filename string) (string, error) {
	ext := filepath.Ext(filename)
	if ext == "" {
		ext = ".jpg"
	}
	relPath := filepath.Join("users", fmt.Sprintf("%d", userID), "avatar"+ext)
	fullPath := filepath.Join(s.BaseDir, relPath)
	dir := filepath.Dir(fullPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	if err := os.WriteFile(fullPath, data, 0644); err != nil {
		return "", err
	}
	return "/" + filepath.ToSlash(filepath.Join(uploadDir, relPath)), nil
}

// SavePublicFile 保存通用文件到指定子目录，返回可访问路径及文件大小。
//
// 安全措施：
//   - 路径穿越防护（Clean + .. 阻断 + 绝对路径前缀校验）
//   - 文件类型白名单（magic bytes 检测 + 扩展名校验）
//   - 唯一文件名（时间戳 + 随机串）
//
// directory 为空时存入 files/ 根目录。
func (s *LocalStore) SavePublicFile(_ context.Context, data []byte, directory string, filename string) (string, int64, error) {
	// 1. 从 magic bytes 推断扩展名
	ext := detectExtensionByMagic(data)
	if ext == "" {
		// 回退到从原始文件名提取
		ext = filepath.Ext(filename)
	}
	if ext == "" {
		ext = ".bin"
	}
	ext = strings.ToLower(ext)
	if !isAllowedExtension(ext) {
		return "", 0, fmt.Errorf("不支持的文件类型: %s", ext)
	}

	// 2. 路径穿越防护
	dir := filepath.Clean(directory)
	if dir == "." {
		dir = ""
	}
	if strings.Contains(dir, "..") {
		return "", 0, fmt.Errorf("非法目录: %s", directory)
	}

	// 3. 生成唯一文件名
	uniqueName := fmt.Sprintf("%d_%s%s", time.Now().UnixNano(), randHex(8), ext)

	// 4. 构建目标路径
	relPath := filepath.Join("files", dir, uniqueName)
	fullPath := filepath.Join(s.BaseDir, relPath)

	// 5. 最终安全检查：fullPath 必须在 BaseDir 内
	absBase, err := filepath.Abs(s.BaseDir)
	if err != nil {
		return "", 0, fmt.Errorf("无法解析存储根目录: %w", err)
	}
	absFull, err := filepath.Abs(fullPath)
	if err != nil {
		return "", 0, fmt.Errorf("无法解析目标路径: %w", err)
	}
	if !strings.HasPrefix(absFull, absBase+string(filepath.Separator)) {
		return "", 0, fmt.Errorf("非法路径")
	}

	// 6. 写入文件
	if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
		return "", 0, fmt.Errorf("创建目录失败: %w", err)
	}
	if err := os.WriteFile(fullPath, data, 0644); err != nil {
		return "", 0, fmt.Errorf("写入文件失败: %w", err)
	}

	// 7. 返回可访问路径
	urlPath := "/" + filepath.ToSlash(filepath.Join(uploadDir, relPath))
	return urlPath, int64(len(data)), nil
}

// detectExtensionByMagic 通过文件头 magic bytes 推断扩展名；无法识别时返回空串。
func detectExtensionByMagic(data []byte) string {
	if len(data) < 4 {
		return ""
	}
	// PNG
	if data[0] == 0x89 && data[1] == 0x50 && data[2] == 0x4E && data[3] == 0x47 {
		return ".png"
	}
	// JPEG
	if data[0] == 0xFF && data[1] == 0xD8 && data[2] == 0xFF {
		return ".jpg"
	}
	// GIF
	if data[0] == 0x47 && data[1] == 0x49 && data[2] == 0x46 && data[3] == 0x38 {
		return ".gif"
	}
	// WEBP
	if data[0] == 0x52 && data[1] == 0x49 && data[2] == 0x46 && data[3] == 0x46 {
		return ".webp"
	}
	// BMP
	if data[0] == 0x42 && data[1] == 0x4D {
		return ".bmp"
	}
	// PDF
	if data[0] == 0x25 && data[1] == 0x50 && data[2] == 0x44 && data[3] == 0x46 {
		return ".pdf"
	}
	// ZIP / DOCX / XLSX / PPTX (PK..)
	if data[0] == 0x50 && data[1] == 0x4B && data[2] == 0x03 && data[3] == 0x04 {
		return ".zip"
	}
	// MP3 (ID3 header or frame sync)
	if (data[0] == 0x49 && data[1] == 0x44 && data[2] == 0x33) ||
		(data[0] == 0xFF && (data[1]&0xE0) == 0xE0) {
		return ".mp3"
	}
	// MP4
	if len(data) >= 12 &&
		data[4] == 0x66 && data[5] == 0x74 && data[6] == 0x79 && data[7] == 0x70 {
		return ".mp4"
	}
	return ""
}

// isAllowedExtension 检查扩展名是否在白名单内。
func isAllowedExtension(ext string) bool {
	return allowedExts[strings.ToLower(ext)]
}

// randHex 生成 n 字节的随机十六进制字符串（2n 字符）。
func randHex(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		// crypto/rand.Read 在 Linux/macOS 上不会失败；极端情况下返回时间戳兜底
		return fmt.Sprintf("%x", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}

// FileItem 目录中的单个条目
type FileItem struct {
	Name    string
	Size    int64
	ModTime string // RFC3339
	IsDir   bool
}

// ListDirectory 列出指定子目录下的文件，directory 为空时列出 files/ 根目录。
// 复用 SavePublicFile 的路径穿越防护逻辑。
func (s *LocalStore) ListDirectory(_ context.Context, directory string) (string, []FileItem, error) {
	// 路径穿越防护（与 SavePublicFile 一致）
	dir := filepath.Clean(directory)
	if dir == "." {
		dir = ""
	}
	if strings.Contains(dir, "..") {
		return "", nil, fmt.Errorf("非法目录: %s", directory)
	}

	relPath := filepath.Join("files", dir)
	fullPath := filepath.Join(s.BaseDir, relPath)

	// 最终安全检查
	absBase, err := filepath.Abs(s.BaseDir)
	if err != nil {
		return "", nil, fmt.Errorf("无法解析存储根目录: %w", err)
	}
	absFull, err := filepath.Abs(fullPath)
	if err != nil {
		return "", nil, fmt.Errorf("无法解析目标路径: %w", err)
	}
	if !strings.HasPrefix(absFull, absBase+string(filepath.Separator)) {
		return "", nil, fmt.Errorf("非法路径")
	}

	entries, err := os.ReadDir(fullPath)
	if err != nil {
		if os.IsNotExist(err) {
			return directory, []FileItem{}, nil
		}
		return "", nil, err
	}

	items := make([]FileItem, 0, len(entries))
	for _, e := range entries {
		info, err := e.Info()
		if err != nil {
			continue
		}
		items = append(items, FileItem{
			Name:    e.Name(),
			Size:    info.Size(),
			ModTime: info.ModTime().Format(time.RFC3339),
			IsDir:   e.IsDir(),
		})
	}
	return directory, items, nil
}

// ExtFromContentType 从 Content-Type 获取扩展名
func ExtFromContentType(ct string) string {
	ct = strings.ToLower(ct)
	switch {
	case strings.Contains(ct, "jpeg"), strings.Contains(ct, "jpg"):
		return ".jpg"
	case strings.Contains(ct, "png"):
		return ".png"
	case strings.Contains(ct, "gif"):
		return ".gif"
	case strings.Contains(ct, "webp"):
		return ".webp"
	default:
		return ".jpg"
	}
}
