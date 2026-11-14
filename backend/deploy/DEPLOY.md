# 线上部署流程

## 一、环境要求

- **操作系统**：Linux（推荐 CentOS 7+、Ubuntu 18.04+）
- **MySQL**：5.7+ 或 8.0+，需已创建数据库并执行 DDL
- **Redis**：5.0+
- **AI Agent 服务**：需单独部署，用于 OCR、内容生成等（如 `http://ip:8001`）

## 二、部署步骤

### 1. 解压部署包

```bash
unzip homework-ai2easy-backend-xxx.zip
cd homework-ai2easy-backend
```

### 2. 配置

```bash
# 复制配置模板
cp configs/config.example.yaml configs/config.yaml

# 编辑配置文件，修改以下关键项：
vim configs/config.yaml
```

**必改配置项：**

| 配置项 | 说明 |
|--------|------|
| `data.database.source` | MySQL 连接串，格式：`user:password@tcp(host:port)/dbname?charset=utf8mb4&parseTime=True&loc=Local` |
| `data.redis.addr` | Redis 地址，如 `127.0.0.1:6379` |
| `data.redis.password` | Redis 密码（无密码留空） |
| `jwt.secret` | JWT 密钥，**生产环境务必改为随机长串** |
| `wechat.app_id` / `wechat.app_secret` | 微信小程序 AppID 与 AppSecret（如需微信登录） |
| `ai_agent.url` | AI Agent 服务地址，如 `http://127.0.0.1:8001` |
| `sms.provider` | 生产环境填 `aliyun` / `tencent` / `huawei`，并配置对应 access_key 等 |

### 3. 初始化数据库

确保 MySQL 中已创建数据库，并执行项目提供的 DDL：

```bash
mysql -u root -p smartstudy < scripts/smartstudy_2026-02-16.sql
# 或根据实际 DDL 文件名执行
```

### 4. 创建目录并赋权

```bash
mkdir -p logs uploads
chmod 755 bin/server
chmod +x start.sh
```

### 5. 启动服务

**前台运行（调试用）：**
```bash
./start.sh
```

**后台运行（推荐）：**
```bash
nohup ./start.sh > logs/console.log 2>&1 &
echo $! > server.pid
```

**使用 systemd（推荐生产环境）：**

创建 `/etc/systemd/system/homework-ai2easy.service`：

```ini
[Unit]
Description=Homework AI2Easy Backend
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/opt/homework-ai2easy
ExecStart=/opt/homework-ai2easy/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable homework-ai2easy
sudo systemctl start homework-ai2easy
sudo systemctl status homework-ai2easy
```

### 6. 验证

- HTTP 接口：`http://服务器IP:8000`
- 健康检查：`curl http://127.0.0.1:8000/healthz`（如有）
- Swagger UI：`http://服务器IP:8000/swagger/`（若已配置）
- 上传目录：`uploads/` 用于作业图片、用户头像，需确保可写

## 三、目录结构

```
homework-ai2easy-backend/
├── bin/
│   └── server          # 可执行文件
├── configs/
│   ├── config.example.yaml
│   └── config.yaml     # 需自行创建
├── docs/
│   └── api/
│       └── openapi.yaml
├── logs/               # 日志目录，需可写
├── uploads/            # 上传文件目录，需可写
├── start.sh
├── DEPLOY.md
└── server.pid          # 后台运行时记录 PID
```

## 四、常用命令

| 操作 | 命令 |
|------|------|
| 查看日志 | `tail -f logs/app.log` |
| 停止服务 | `kill $(cat server.pid)` 或 `systemctl stop homework-ai2easy` |
| 重启服务 | `systemctl restart homework-ai2easy` |
| 查看端口 | `netstat -tlnp \| grep 8000` |

## 五、注意事项

1. **防火墙**：开放 8000（HTTP）、9002（gRPC，如对外）端口
2. **反向代理**：生产环境建议用 Nginx 做反向代理，配置 HTTPS
3. **JWT 密钥**：务必使用强随机串，不要使用示例值
4. **上传目录**：`uploads/` 需保证应用用户有写权限
5. **AI Agent**：OCR 与内容生成依赖 AI Agent，需先部署并保证网络可达
