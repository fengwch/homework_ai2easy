# 数据库初始化与授权

本文档说明本地开发、测试与部署场景下 MySQL、Redis 的初始化、用户授权及配置方式。  
服务启动时通过 GORM 自动迁移创建表（`users`、`children`、`assignments`），**只需事先创建数据库和用户并完成授权**。

---

## 1. 前置要求

- **MySQL** 5.7+ 或 8.0
- **Redis** 5.0+
- 本服务使用 `configs/config.yaml`（或 `-conf` 指定路径）连接数据库与 Redis

---

## 2. MySQL 初始化与授权

### 2.1 创建数据库

使用具备建库权限的账号（如 `root`）登录 MySQL，执行：

```sql
CREATE DATABASE IF NOT EXISTS homework_ai2easy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2.2 创建用户并授权（按场景）

根据运行环境选择一种方式即可。  
**注意**：以下 `'password'`、`'your_password'` 等请替换为强密码，且不要提交到仓库。

#### 场景 A：本机直连（开发机装 MySQL）

应用与 MySQL 均在本机，使用 `127.0.0.1` 或 `localhost` 连接：

```sql
-- 使用 root（仅本地开发可考虑，生产勿用）
-- 若 root 已存在，只需确保允许本地连接即可，无需执行 CREATE USER

-- 或创建专用用户（推荐）
CREATE USER IF NOT EXISTS 'homework_app'@'localhost'
  IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON homework_ai2easy.* TO 'homework_app'@'localhost';
FLUSH PRIVILEGES;
```

`configs/config.yaml` 示例：

```yaml
data:
  database:
    driver: mysql
    source: homework_app:your_password@tcp(127.0.0.1:3306)/homework_ai2easy?charset=utf8mb4&parseTime=True&loc=Local
```

#### 场景 B：Docker 运行 MySQL，应用在宿主机运行（常见开发方式）

MySQL 在容器内，应用跑在宿主机。应用连 `127.0.0.1:3306`（端口映射），MySQL 看到的客户端 IP 为 Docker 网桥地址（如 `172.17.0.1`、`192.168.65.1` 等），因此需对该网段或 `%` 授权。

**方式 1：允许来自任意主机的连接（仅开发/测试）**

```sql
CREATE USER IF NOT EXISTS 'homework_app'@'%'
  IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON homework_ai2easy.* TO 'homework_app'@'%';
FLUSH PRIVILEGES;
```

**方式 2：仅允许 Docker 网桥网段（更安全）**

宿主机通过 Docker 访问时，常见网段示例：

- Docker Desktop (Mac/Windows): `192.168.65.0/24` 等
- Linux bridge: `172.17.0.0/16`

按实际网段创建用户，例如：

```sql
-- 示例：允许 192.168.65.x
CREATE USER IF NOT EXISTS 'homework_app'@'192.168.65.%'
  IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON homework_ai2easy.* TO 'homework_app'@'192.168.65.%';
FLUSH PRIVILEGES;
```

若遇到 `Access denied for user '...'@'192.168.65.1'`，即 Docker 宿主机以该 IP 连接，对 `'%'` 或 `'192.168.65.%'` 授权即可。

#### 场景 C：测试 / CI 环境

使用独立数据库与专用用户，避免与开发/生产共用：

```sql
CREATE DATABASE IF NOT EXISTS homework_ai2easy_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'homework_test'@'%'
  IDENTIFIED BY 'test_password';

GRANT ALL PRIVILEGES ON homework_ai2easy_test.* TO 'homework_test'@'%';
FLUSH PRIVILEGES;
```

测试时通过 `-conf configs/config.test.yaml` 或环境变量指向 `homework_ai2easy_test` 及对应用户。

#### 场景 D：生产 / 部署环境

- 使用**专用业务用户**，不要用 `root`。
- 强密码、最小权限（仅 `homework_ai2easy.*` 的 `SELECT/INSERT/UPDATE/DELETE` 等）。
- 按实际网络限制 `HOST`（如应用所在内网网段），避免 `'%'`。

```sql
CREATE USER IF NOT EXISTS 'homework_app'@'10.0.%.%'
  IDENTIFIED BY 'strong_production_password';

GRANT SELECT, INSERT, UPDATE, DELETE ON homework_ai2easy.* TO 'homework_app'@'10.0.%.%';
FLUSH PRIVILEGES;
```

生产环境数据库连接建议通过环境变量或配置中心注入，不要将密码写入仓库。

---

### 2.3 使用提供的 SQL 脚本（可选）

项目提供 `scripts/init-db.sql`，用于创建数据库和示例用户。**使用前请修改其中的密码**。

```bash
mysql -u root -p < scripts/init-db.sql
```

脚本默认创建 `homework_ai2easy` 库及 `'homework_app'@'%'`，仅适用于开发/测试。生产请按 2.2 节自行编写更严格的授权。

---

## 3. Redis

本服务默认连接无密码的 Redis（`127.0.0.1:6379`，db 0）。  
若 Redis 设置密码或不同地址，修改 `configs/config.yaml`：

```yaml
data:
  redis:
    addr: 127.0.0.1:6379
    password: "your_redis_password"  # 无密码则留空
    db: 0
```

测试/部署时可使用独立 Redis 实例，并在对应环境的配置中修改 `addr` / `password` / `db`。

---

## 4. 配置说明（config.yaml）

### 4.1 配置优先级

- 服务通过 `-conf` 指定配置路径（默认 `configs/config.yaml`）。
- 敏感信息（数据库密码、Redis 密码、JWT secret）建议通过环境变量或部署平台 Secret 注入，覆盖配置文件中的值（若已实现相应逻辑）。

### 4.2 本地 / 测试 / 部署差异

| 项         | 本地开发       | 测试 / CI     | 生产部署       |
|------------|----------------|---------------|----------------|
| 数据库     | `homework_ai2easy` | `homework_ai2easy_test` | `homework_ai2easy` |
| 用户       | `homework_app` 或 `root` | `homework_test` | 专用业务用户   |
| MySQL host | `127.0.0.1`    | 测试机/容器   | 内网 DB 地址   |
| Redis      | 本地 Redis     | 测试 Redis    | 生产 Redis     |
| JWT secret | 可固定开发用   | 独立测试密钥  | 强随机、保密   |

可为不同环境维护不同配置文件（如 `config.test.yaml`、`config.prod.yaml`），通过 `-conf` 或环境切换。

### 4.3 Duration 格式

`jwt.expires_in`、`sms.expires_in` 等为 `google.protobuf.Duration`，仅支持**秒**格式，例如：

- `2592000s`：30 天  
- `300s`：5 分钟  

不要使用 `720h`、`5m` 等 Go duration 格式。

---

## 5. 表结构（自动迁移）

服务启动时 GORM 自动迁移下列表，无需手动建表：

- `users`：用户
- `children`：儿童档案
- `assignments`：作业（含 questions JSON）
- `story_contents`：故事内容（含 question_id 字段，单题生成时使用）
- `question_generation_statuses`：单题内容生成状态

若修改了 `internal/data/model` 中的模型，重启服务即可应用迁移变更。

**详细表结构、questionId 生成规则与 SQL DDL** 参见：

- [docs/database-schema.md](database-schema.md)
- [scripts/ddl.sql](../scripts/ddl.sql)

---

## 6. 常见问题

### 6.1 `Access denied for user 'root'@'192.168.65.1' (using password: YES)`

- **原因**：MySQL 在 Docker 中，应用从宿主机连接；MySQL 看到的客户端 IP 为 Docker 网桥（如 `192.168.65.1`），该 `user@host` 无权限。
- **处理**：对 `'%'` 或 `'192.168.65.%'` 授权，见 2.2 节「场景 B」。

### 6.2 `stat configs/config.yaml: no such file or directory`

- **原因**：工作目录或 `-conf` 路径不对，找不到配置文件。
- **处理**：在项目根目录执行 `make run`，或 `./bin/server -conf configs/config.yaml`；若使用自定义路径，请写绝对路径或相对当前工作目录的正确路径。

### 6.3 `invalid google.protobuf.Duration value "720h"`

- **原因**：Duration 仅支持秒，如 `3600s`。
- **处理**：将 `720h` 改为 `2592000s`，`5m` 改为 `300s`，参见 4.3 节。

### 6.4 Redis 连接失败

- 确认 Redis 已启动，`addr`、`password`、`db` 与当前环境一致。
- 若 Redis 在 Docker，确认端口已映射且应用能访问对应地址。

---

## 7. 参考

- 项目配置：`configs/config.yaml`
- 初始化脚本：`scripts/init-db.sql`
- 数据模型与迁移：`internal/data/model`、`internal/data/dao/data.go`
