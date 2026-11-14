# API 文档总结

## 📚 文档结构

```
docs/api/
├── 前端接口文档.md          # 完整的 API 接口文档（Markdown 格式）
├── QUICKSTART.md      # 快速开始指南
├── openapi.yaml       # OpenAPI 3.0 规范文档
└── SUMMARY.md         # 本文档
```

## 🚀 快速开始

### 1. 启动服务

```bash
make dev
# 或
go run ./cmd/server
```

服务默认运行在 `http://localhost:8000`

### 2. 访问 Swagger UI

打开浏览器访问：

```
http://localhost:8000/swagger
```

Swagger UI 提供了：
- ✅ 完整的 API 文档
- ✅ 交互式 API 测试
- ✅ 请求/响应示例
- ✅ 参数验证
- ✅ 认证支持（JWT Token）

### 3. 查看 OpenAPI 文档

访问 OpenAPI 规范文件：

```
http://localhost:8000/api/openapi.yaml
```

## 📖 文档说明

### 前端接口文档.md
完整的 API 接口文档，包含：
- 所有接口的详细说明
- 请求参数说明
- 响应格式说明
- 错误码参考
- 使用示例

### QUICKSTART.md
快速开始指南，包含：
- 如何访问 Swagger UI
- 如何设置认证
- 常用接口示例
- 开发建议

### openapi.yaml
OpenAPI 3.0 规范文档，包含：
- 完整的 API 定义
- 数据模型定义
- 认证方式说明
- 可以被各种工具使用（Postman、Insomnia 等）

## 🔐 认证说明

大部分 API 需要 JWT Token 认证：

1. **获取 Token**
   - 使用 `/api/v1/auth/login` 或 `/api/v1/auth/password-login` 登录
   - 响应中会返回 `token` 字段

2. **使用 Token**
   - 在请求头中添加：`Authorization: Bearer <token>`
   - 在 Swagger UI 中点击 "Authorize" 按钮设置 Token

3. **刷新 Token**
   - 使用 `/api/v1/auth/refresh` 刷新过期的 Token

## 🛠️ 开发工具集成

### Postman
1. 导入 OpenAPI 文档：`File > Import > Link`
2. 输入：`http://localhost:8000/api/openapi.yaml`
3. 设置环境变量：`base_url = http://localhost:8000`
4. 设置认证：在 Collection 的 Authorization 中设置 Bearer Token

### Insomnia
1. 创建新请求
2. 选择 "Import/Export" > "Import Data" > "From URL"
3. 输入：`http://localhost:8000/api/openapi.yaml`

### VS Code REST Client
创建 `.http` 文件：
```http
### 登录
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "phone": "13800138000",
  "code": "123456"
}

### 获取用户信息
GET http://localhost:8000/api/v1/user/profile
Authorization: Bearer {{token}}
```

## 📝 API 服务列表

### 认证服务 (AuthService)
- 发送验证码
- 手机号验证码登录
- 密码登录
- 微信一键登录
- 用户注册
- 刷新 Token
- 重置密码

### 用户服务 (UserService)
- 获取用户信息
- 更新用户信息
- 上传头像
- 修改密码
- 绑定手机号
- 获取订阅信息
- 更新订阅

### 儿童档案服务 (ChildService)
- 获取儿童列表
- 获取儿童详情
- 创建儿童档案
- 更新儿童档案
- 删除儿童档案
- 上传儿童头像

### 作业服务 (AssignmentService)
- 上传作业图片
- 按作业ID触发扫描识别 (`POST /api/v1/assignments/{id}/scan`)
- 获取识别进度 (`GET /api/v1/assignments/{id}/scan-status`)
- 获取作业详情
- 编辑识别结果
- 题目分割确认
- 题目类型标注
- 知识点匹配
- 更新知识点
- 更新作业信息
- 删除题目
- 生成个性化内容 (`POST /api/v1/assignments/{assignment_id}/generate`)
- 查询内容生成状态 (`GET /api/v1/assignments/{assignment_id}/generate-status`)

### 学习内容 (Content)
- 获取故事/学习材料 (`GET /api/v1/contents/{story_id}`) - 需 JWT

### AI-Agent 对接
- 详见 [AI-AGENT-INTEGRATION.md](./AI-AGENT-INTEGRATION.md)：OCR、内容生成、解题引导、语音合成均已对接
- 获取作业列表

## 🔄 更新文档

当修改 API 定义（proto 文件）后：

1. **重新生成代码**
   ```bash
   make api
   ```

2. **更新 OpenAPI 文档**
   - 手动更新 `docs/api/openapi.yaml`（如果 proto 生成的 OpenAPI 不完整）
   - 或使用工具合并多个 OpenAPI 文件

3. **更新 后端接口文档.md**
   - 根据新的 API 定义更新 Markdown 文档

## 📞 支持

如有问题，请：
1. 查看 [后端接口文档.md](后端接口文档.md) 获取详细文档
2. 查看 [QUICKSTART.md](QUICKSTART.md) 获取快速开始指南
3. 使用 Swagger UI 进行交互式测试
4. 查看 OpenAPI 规范了解完整定义

## 🎯 最佳实践

1. **开发阶段**
   - 使用 Swagger UI 进行快速测试
   - 查看请求/响应示例

2. **集成阶段**
   - 使用 OpenAPI 文档导入到 Postman/Insomnia
   - 参考 后端接口文档.md 了解业务逻辑

3. **生产环境**
   - 确保 Token 安全传输（HTTPS）
   - 注意 Token 过期时间
   - 实现 Token 刷新机制
