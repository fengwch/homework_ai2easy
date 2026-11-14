package apilist

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

func TestSupportedRoutes(t *testing.T) {
	routes := SupportedRoutes()
	if len(routes) == 0 {
		t.Fatal("SupportedRoutes() returned empty")
	}
	seen := make(map[string]bool)
	for _, r := range routes {
		if r.Method == "" || r.Path == "" {
			t.Errorf("route has empty method or path: %+v", r)
		}
		key := r.Method + " " + r.Path
		if seen[key] {
			t.Errorf("duplicate route: %s", key)
		}
		seen[key] = true
	}
	// 确保包含已知接口
	expected := []string{"POST /api/v1/auth/login", "GET /api/v1/user/profile", "GET /api/v1/children", "GET /api/v1/assignments"}
	for _, e := range expected {
		if !seen[e] {
			t.Errorf("expected route missing: %s", e)
		}
	}
}

func TestPrintSupportedAPIs(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	defer func() { os.Stdout = old }()

	PrintSupportedAPIs("0.0.0.0:8000", "0.0.0.0:9000")
	_ = w.Close()

	var buf bytes.Buffer
	_, _ = buf.ReadFrom(r)
	out := buf.String()

	if !strings.Contains(out, "支持的接口") {
		t.Errorf("output missing 支持的接口: %s", out)
	}
	if !strings.Contains(out, "http://127.0.0.1:8000") {
		t.Errorf("output missing http base: %s", out)
	}
	if !strings.Contains(out, "0.0.0.0:9000") {
		t.Errorf("output missing gRPC addr: %s", out)
	}
	if !strings.Contains(out, "/api/v1/auth/login") {
		t.Errorf("output missing sample route: %s", out)
	}
}
