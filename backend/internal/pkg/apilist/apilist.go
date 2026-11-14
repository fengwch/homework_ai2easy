package apilist

import (
	"fmt"
	"os"
	"strings"
)

// Route 表示一条 HTTP 接口
type Route struct {
	Method  string // GET, POST, PUT, DELETE
	Path    string
	Summary string // 简要说明
}

// SupportedRoutes 返回项目支持的 HTTP 接口列表（与 proto 定义保持一致）
func SupportedRoutes() []Route {
	return []Route{
		// 认证
		{"POST", "/api/v1/auth/send-sms", "发送验证码"},
		{"POST", "/api/v1/auth/login", "手机号验证码登录"},
		{"POST", "/api/v1/auth/wechat-login", "微信一键登录"},
		{"POST", "/api/v1/auth/password-login", "密码登录"},
		{"POST", "/api/v1/auth/register", "用户注册"},
		{"POST", "/api/v1/auth/refresh", "刷新Token"},
		{"POST", "/api/v1/auth/reset-password", "重置密码"},
		// 用户
		{"GET", "/api/v1/user/profile", "获取用户信息"},
		{"PUT", "/api/v1/user/profile", "更新用户信息"},
		{"POST", "/api/v1/user/avatar", "上传头像"},
		{"POST", "/api/v1/user/change-password", "修改密码"},
		{"POST", "/api/v1/user/bind-phone", "绑定手机号"},
		{"GET", "/api/v1/user/subscription", "获取订阅信息"},
		{"POST", "/api/v1/user/subscription", "订阅管理"},
		// 儿童档案
		{"GET", "/api/v1/children", "获取儿童列表"},
		{"GET", "/api/v1/children/{id}", "获取儿童详情"},
		{"POST", "/api/v1/children", "创建儿童档案"},
		{"PUT", "/api/v1/children/{id}", "更新儿童档案"},
		{"DELETE", "/api/v1/children/{id}", "删除儿童档案"},
		{"POST", "/api/v1/children/{id}/avatar", "上传儿童头像"},
		// 作业
		{"POST", "/api/v1/assignments/upload", "上传作业图片"},
		{"POST", "/api/v1/assignments/scan", "扫描识别作业"},
		{"GET", "/api/v1/assignments/{id}/scan-status", "获取识别进度"},
		{"GET", "/api/v1/assignments/{id}", "获取作业详情"},
		{"PUT", "/api/v1/assignments/{id}/questions/{question_id}", "编辑识别结果"},
		{"POST", "/api/v1/assignments/{id}/split-questions", "题目分割确认"},
		{"PUT", "/api/v1/assignments/{id}/questions/{question_id}/type", "题目类型标注"},
		{"GET", "/api/v1/assignments/{id}/questions/{question_id}/knowledge-points", "知识点匹配"},
		{"PUT", "/api/v1/assignments/{id}/questions/{question_id}/knowledge-points", "更新知识点"},
		{"PUT", "/api/v1/assignments/{id}", "更新作业信息"},
		{"DELETE", "/api/v1/assignments/{id}/questions/{question_id}", "删除题目"},
		{"POST", "/api/v1/assignments/{assignment_id}/generate", "生成个性化内容"},
		{"GET", "/api/v1/assignments/{assignment_id}/generate-status", "查询内容生成状态"},
		{"POST", "/api/v1/assignments/{assignment_id}/questions/{question_id}/generate", "单题生成个性化内容"},
		{"GET", "/api/v1/assignments/{assignment_id}/questions/{question_id}/generate-status", "单题内容生成状态"},
		{"GET", "/api/v1/assignments", "获取作业列表"},
		{"GET", "/api/v1/assignments/{id}/answers", "获取作业答题记录（批改页）"},
		// 学习内容
		{"GET", "/api/v1/contents/{story_id}", "获取学习材料"},
		{"POST", "/api/v1/questions/{question_id}/answer", "提交题目答案"},
		{"POST", "/api/v1/contents/solution-guide", "解题引导"},
		{"POST", "/api/v1/voice/synthesize", "语音合成（提交任务）"},
		{"GET", "/api/v1/voice/synthesize/status", "语音合成状态（轮询）"},
	}
}

// PrintSupportedAPIs 在启动时向 stdout 打印支持的 HTTP 与 gRPC 接口列表。
// httpAddr、grpcAddr 为配置中的监听地址，如 "0.0.0.0:8000"、"0.0.0.0:9000"。
func PrintSupportedAPIs(httpAddr, grpcAddr string) {
	routes := SupportedRoutes()
	padMethod := 6
	padPath := 52
	for _, r := range routes {
		if l := len(r.Method); l > padMethod {
			padMethod = l
		}
		if l := len(r.Path); l > padPath {
			padPath = l
		}
	}
	lines := []string{
		"",
		"======== 支持的接口 ========",
		fmt.Sprintf("HTTP: http://%s", normAddr(httpAddr)),
		"",
	}
	for _, r := range routes {
		lines = append(lines, fmt.Sprintf("  %-*s %-*s %s",
			padMethod, r.Method, padPath, r.Path, r.Summary))
	}
	lines = append(lines,
		"",
		fmt.Sprintf("gRPC: %s", grpcAddr),
		"  api.auth.v1.AuthService",
		"  api.user.v1.UserService",
		"  api.child.v1.ChildService",
		"  api.assignment.v1.AssignmentService",
		"============================",
		"",
	)
	fmt.Fprint(os.Stdout, strings.Join(lines, "\n"))
}

// normAddr 将 0.0.0.0 转为 localhost，便于本地访问示例
func normAddr(addr string) string {
	if strings.HasPrefix(addr, "0.0.0.0:") {
		return "127.0.0.1" + addr[7:]
	}
	return addr
}
