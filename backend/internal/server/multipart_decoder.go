package server

import (
	"io"
	"net/http"
	"strconv"
	"strings"

	kratosHttp "github.com/go-kratos/kratos/v2/transport/http"

	v1Assignment "homework_ai2easy/backend/api/assignment/v1"
	v1File "homework_ai2easy/backend/api/file/v1"
	v1User "homework_ai2easy/backend/api/user/v1"
)

const (
	multipartMaxMemory = 32 << 20 // 32MB
	maxFileSize       = 10 << 20  // 10MB
)

// MultipartAwareRequestDecoder 对 multipart/form-data 的上传请求特殊处理，其余走默认 JSON 解码。
func MultipartAwareRequestDecoder(r *http.Request, v interface{}) error {
	ct := r.Header.Get("Content-Type")
	if !strings.HasPrefix(ct, "multipart/form-data") {
		return kratosHttp.DefaultRequestDecoder(r, v)
	}
	if strings.HasSuffix(r.URL.Path, "/assignments/upload") {
		return decodeUploadImageRequest(r, v)
	}
	if strings.HasSuffix(r.URL.Path, "/user/avatar") {
		return decodeUploadAvatarRequest(r, v)
	}
	if strings.HasSuffix(r.URL.Path, "/files/upload") {
		return decodeUploadFileRequest(r, v)
	}
	return kratosHttp.DefaultRequestDecoder(r, v)
}

// decodeUploadImageRequest 解析 multipart 表单，填充 *v1.UploadImageRequest。
// 支持 form 字段：childId / child_id，文件字段：file。
func decodeUploadImageRequest(r *http.Request, v interface{}) error {
	req, ok := v.(*v1Assignment.UploadImageRequest)
	if !ok {
		return kratosHttp.DefaultRequestDecoder(r, v)
	}
	if err := r.ParseMultipartForm(multipartMaxMemory); err != nil {
		return err
	}
	form := r.MultipartForm
	if form == nil {
		return nil
	}
	// childId 或 child_id
	for _, key := range []string{"childId", "child_id"} {
		if vs := form.Value[key]; len(vs) > 0 && vs[0] != "" {
			id, err := strconv.ParseInt(vs[0], 10, 64)
			if err != nil {
				continue
			}
			req.ChildId = id
			break
		}
	}
	// file 字段（第一个文件）
	if files := form.File["file"]; len(files) > 0 {
		fh := files[0]
		f, err := fh.Open()
		if err != nil {
			return err
		}
		defer f.Close()
		buf, err := io.ReadAll(io.LimitReader(f, maxFileSize))
		if err != nil {
			return err
		}
		req.File = buf
	}
	return nil
}

// decodeUploadAvatarRequest 解析 multipart 表单，填充 *v1.UploadAvatarRequest。支持 form 字段：file。
// decodeUploadFileRequest 解析通用文件上传 multipart 表单，填充 *v1File.UploadFileRequest。
// 支持字段：file（文件，必填），directory（目标子目录，可选）。
func decodeUploadFileRequest(r *http.Request, v interface{}) error {
	req, ok := v.(*v1File.UploadFileRequest)
	if !ok {
		return kratosHttp.DefaultRequestDecoder(r, v)
	}
	if err := r.ParseMultipartForm(multipartMaxMemory); err != nil {
		return err
	}
	form := r.MultipartForm
	if form == nil {
		return nil
	}
	// directory 字段
	if vs := form.Value["directory"]; len(vs) > 0 && vs[0] != "" {
		req.Directory = vs[0]
	}
	// file 字段（第一个文件）
	if files := form.File["file"]; len(files) > 0 {
		fh := files[0]
		f, err := fh.Open()
		if err != nil {
			return err
		}
		defer f.Close()
		buf, err := io.ReadAll(io.LimitReader(f, maxFileSize))
		if err != nil {
			return err
		}
		req.File = buf
	}
	return nil
}

func decodeUploadAvatarRequest(r *http.Request, v interface{}) error {
	req, ok := v.(*v1User.UploadAvatarRequest)
	if !ok {
		return kratosHttp.DefaultRequestDecoder(r, v)
	}
	if err := r.ParseMultipartForm(multipartMaxMemory); err != nil {
		return err
	}
	form := r.MultipartForm
	if form == nil {
		return nil
	}
	if files := form.File["file"]; len(files) > 0 {
		fh := files[0]
		f, err := fh.Open()
		if err != nil {
			return err
		}
		defer f.Close()
		buf, err := io.ReadAll(io.LimitReader(f, maxFileSize))
		if err != nil {
			return err
		}
		req.File = buf
	}
	return nil
}
