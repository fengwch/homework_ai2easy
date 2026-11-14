# 测试说明

## 概述

- **单元测试**：对业务用例（usecase）、内部包（如 apilist）进行测试，使用内存依赖（miniredis、FakeUserRepository），**不依赖 MySQL 或真实 Redis**。
- **接口测试**：对认证相关 HTTP 接口发起请求，校验状态码与 JSON 响应，使用上述内存依赖搭建测试用 HTTP 服务。

## 运行方式

```bash
make test          # 单元测试 + 接口测试
make test-unit     # 仅单元测试 (biz/usecase, pkg)
make test-api      # 仅接口测试 (test/)
make test-short    # 快速测试，无 -v
```

或直接使用 `go test`：

```bash
go test ./internal/biz/usecase/... ./internal/pkg/... -v -count=1
go test ./test/... -v -count=1
```

## 目录与职责

| 路径 | 说明 |
|------|------|
| `internal/testutil/` | 测试用工具：miniredis、FakeUserRepository、TestJWTConf、TestSMSConf、AuthTestDeps 等 |
| `internal/biz/usecase/*_test.go` | Auth、User 等用例的单元测试 |
| `internal/pkg/apilist/apilist_test.go` | 支持接口列表的单元测试 |
| `test/auth_api_test.go` | 认证 HTTP 接口测试（send-sms、login、register、password-login、reset-password） |

## 依赖

- `github.com/stretchr/testify`：assert、require
- `github.com/alicebob/miniredis/v2`：内存 Redis，用于短信验证码存储与校验

## 扩展

- 新增用例单测：在 `internal/biz/usecase` 下添加 `*_test.go`，使用 `testutil.NewAuthTestDeps` 或 `testutil.NewFakeUserRepository` 等。
- 新增接口测试：在 `test/` 下添加 `*_test.go`，通过 `newAuthHTTPServer` 或类似方式启动测试用 HTTP 服务，再用 `http.Client` 发请求并断言。
