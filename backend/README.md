# AI赋能儿童作业辅导App - 后端服务

基于 Kratos v2.x 的 Go 微服务后端实现。

## 项目结构

```
backend/
├── api/                    # API 定义 (Protobuf 文件)
│   ├── auth/v1/           # 认证服务
│   ├── user/v1/            # 用户服务
│   ├── child/v1/           # 儿童档案服务
│   └── assignment/v1/     # 作业服务
├── cmd/server/             # 应用程序入口
├── configs/                # 配置文件
├── internal/               # 私有代码
│   ├── biz/               # 业务逻辑层
│   ├── data/              # 数据访问层
│   ├── service/           # 服务层
│   ├── server/            # 服务器配置
│   ├── conf/              # 配置结构
│   └── pkg/               # 内部共享包
├── third_party/            # 第三方依赖
├── scripts/                # 脚本（如 init-db.sql）
└── docs/                   # 文档
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 Go 工具
make init

# 下载 Go 依赖
go mod download
```

### 2. 数据库与 Redis 初始化

**MySQL**：创建数据库 `homework_ai2easy`，并创建用户、授权。按运行环境选择：

- **本机直连**：对 `'user'@'localhost'` 授权。
- **Docker 跑 MySQL、应用在宿主机**：常见报错 `Access denied for user '...'@'192.168.65.1'`，需对 `'%'` 或 `'192.168.65.%'` 授权。

可使用项目提供的脚本（**使用前请修改脚本内密码**）：

```bash
mysql -u root -p < scripts/init-db.sql
```

或按 [docs/database-setup.md](docs/database-setup.md) 手动执行建库、创建用户、授权。

**Redis**：确保已启动，默认 `127.0.0.1:6379`，无密码。

**配置文件**：修改 `configs/config.yaml` 中的数据库连接串，与上述用户、密码一致：

```yaml
data:
  database:
    source: homework_app:your_password@tcp(127.0.0.1:3306)/homework_ai2easy?charset=utf8mb4&parseTime=True&loc=Local
  redis:
    addr: 127.0.0.1:6379
    password: ""
    db: 0
```

测试与部署场景的库名、用户、权限等详见 **[数据库初始化与授权](docs/database-setup.md)**。

### 3. 生成代码

```bash
# 生成 proto 代码
make api

# 生成依赖注入代码
make wire
```

### 4. 运行服务

```bash
# 编译并运行（默认使用 configs/config.yaml）
make run

# 或指定配置路径
./bin/server -conf configs/config.yaml
```

## API 接口

服务启动后，HTTP 服务运行在 `http://localhost:8000`，gRPC 服务运行在 `localhost:9000`。

### 认证接口

- `POST /api/v1/auth/send-sms` - 发送验证码
- `POST /api/v1/auth/login` - 手机号验证码登录
- `POST /api/v1/auth/password-login` - 密码登录
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/reset-password` - 重置密码

### 用户接口

- `GET /api/v1/user/profile` - 获取用户信息
- `PUT /api/v1/user/profile` - 更新用户信息
- `POST /api/v1/user/avatar` - 上传头像
- `POST /api/v1/user/change-password` - 修改密码
- `GET /api/v1/user/subscription` - 获取订阅信息

### 儿童档案接口

- `GET /api/v1/children` - 获取儿童列表
- `GET /api/v1/children/{id}` - 获取儿童详情
- `POST /api/v1/children` - 创建儿童档案
- `PUT /api/v1/children/{id}` - 更新儿童档案
- `DELETE /api/v1/children/{id}` - 删除儿童档案

### 作业接口

- `POST /api/v1/assignments/upload` - 上传作业图片
- `POST /api/v1/assignments/scan` - 扫描识别作业
- `GET /api/v1/assignments/{id}` - 获取作业详情
- `GET /api/v1/assignments` - 获取作业列表

详细接口文档请参考 `docs/api/前端接口文档.md`。

## 开发说明

### 代码生成

项目使用 Wire 进行依赖注入，修改依赖关系后需要重新生成：

```bash
make wire
```

### 添加新接口

1. 在 `api/{service}/v1/` 目录下定义 proto 文件
2. 运行 `make api` 生成代码
3. 在 `internal/service/grpc/` 实现服务
4. 在 `internal/server/http.go` 和 `internal/server/grpc.go` 注册服务

### 数据库迁移

项目使用 GORM 自动迁移，启动时会自动创建 `users`、`children`、`assignments` 等表。需事先完成 MySQL 建库、用户创建与授权，参见 [数据库初始化与授权](docs/database-setup.md)。

### 单元测试与接口测试

- **单元测试**：`internal/biz/usecase`（Auth、User 等业务用例）、`internal/pkg/apilist`。使用 `internal/testutil` 的 miniredis、FakeUserRepository、测试配置等，**无需真实 MySQL/Redis**。
- **接口测试**：`test/` 下对认证相关 HTTP 接口（send-sms、login、register、password-login、reset-password）进行请求级测试。

```bash
make test          # 单元测试 + 接口测试
make test-unit     # 仅单元测试
make test-api      # 仅接口测试
make test-short    # 快速测试（无 -v）
```

详见 [测试说明](docs/testing.md)。

## 技术栈

- **框架**: Kratos v2.x
- **数据库**: MySQL + GORM
- **缓存**: Redis
- **认证**: JWT
- **API**: gRPC + HTTP (通过 proto 注解自动生成)

## 配置说明

### 日志配置

日志模块（`internal/pkg/logger`）基于 **Zap + lumberjack**，遵循项目日志规范：结构化 key-value、JSON/text、输出 stdout/file/both、按大小/备份/天数轮转。

```yaml
logger:
  level: info
  format: json
  output: both
  file_path: logs/app.log
  max_size: 100
  max_backups: 5
  max_age: 30
  compress: true
  enable_caller: true
  enable_stacktrace: false
```

- `level`: debug / info / warn / error / fatal  
- `format`: json 或 text  
- `output`: stdout / file / both  
- `file_path`: 文件路径，`output` 为 file 或 both 时生效  
- 不配置 `logger` 时使用默认值（level=info, format=json, output=stdout, 等）。`logs/` 已加入 `.gitignore`。

### CORS（测试环境）

测试环境下需配置 **Access-Control-Allow-Origin / Allow-Methods / Allow-Headers**（及可选 **Allow-Credentials**），以便前端直连后端接口。前端若使用 `credentials: 'include'` 或 Cookie/Authorization，须用**具体源**并设 `allow_credentials: true`，不能使用 `*`。

使用测试配置（已适配 Vite 开发服 `http://localhost:5173`）：

```bash
./bin/server -conf configs/config.test.yaml
```

`config.test.yaml` 示例：

```yaml
server:
  cors:
    enabled: true
    allow_origins:
      - "http://localhost:5173"
      - "http://127.0.0.1:5173"
    allow_credentials: true
    allow_methods: [GET, POST, PUT, PATCH, DELETE, OPTIONS]
    allow_headers: [Content-Type, Authorization, X-Requested-With, Accept, Origin]
```

遇 `strict-origin-when-cross-origin` 等跨域问题时，确认后端以测试配置启动且前端请求带 `Origin: http://localhost:5173`。生产环境建议关闭 CORS 或仅允许指定源。

### SMS 短信服务配置

**开发模式（默认）**：
- 当前配置为 `mock` 模式，验证码会打印在日志中，不会实际发送短信
- 适合开发和测试环境

**测试环境万能验证码**：使用 `configs/config.test.yaml` 时，已配置 `sms.test_code: "123456"`。登录、注册、重置密码时填写该验证码即可跳过校验，无需发送短信。

**生产环境配置**：
- 需要配置正式的短信服务商（阿里云/腾讯云/华为云）
- 详细配置步骤请参考：[SMS 服务配置指引](docs/sms-configuration.md)
- 快速配置指南：[SMS 快速配置](docs/sms-quickstart.md)

**配置文件位置**：`configs/config.yaml`

```yaml
sms:
  expires_in: 300s  # 验证码过期时间
  provider: mock  # mock/aliyun/tencent/huawei
  # 生产环境需要配置以下字段：
  # access_key_id: "your-access-key-id"
  # access_key_secret: "your-access-key-secret"
  # sign_name: "作业助手"
  # template_code: "your-template-code"
  # region: "cn-hangzhou"
```

## 更新日志

### 2025-01-26

**数据库与单题生成相关**

- **questionId 生成规则**：来源为 AI-Agent OCR 返回的 `id`（如 `q1`、`q2`），在作业内唯一；详见 [docs/database-schema.md](docs/database-schema.md)
- **表结构变更**：
  - `story_contents` 新增 `question_id` 字段，单题生成时非空
  - 新增 `question_generation_statuses` 表，记录单题内容生成状态
- **文档**：
  - 新增 [docs/database-schema.md](docs/database-schema.md)：表结构、questionId 说明、接口与表映射
  - 新增 [scripts/ddl.sql](scripts/ddl.sql)：完整 MySQL DDL（供参考或手动部署）
  - 更新 [docs/database-setup.md](docs/database-setup.md)：补充 story_contents、question_generation_statuses 表说明

**单题个性化内容生成接口（2.4.3）**

- `POST /api/v1/assignments/{assignmentId}/questions/{questionId}/generate` - 单题生成
- `GET /api/v1/assignments/{assignmentId}/questions/{questionId}/generate-status` - 查询生成状态

---

## 注意事项

1. **生产环境配置**：
   - 修改 `configs/config.yaml` 中的 JWT secret
   - 数据库使用专用用户并限制 HOST，参见 [数据库初始化与授权](docs/database-setup.md)
   - 配置正式的短信服务，参见 [SMS 服务配置指引](docs/sms-configuration.md)

2. **安全建议**：
   - 不要将 AccessKey、Secret 等敏感信息提交到 Git
   - 使用环境变量或密钥管理服务存储敏感配置
   - 生产环境配置文件应添加到 `.gitignore`

3. **待实现功能**：
   - 文件上传功能需要配置对象存储服务（OSS）
   - OCR 识别功能需要集成 AI 服务

## License

MIT
