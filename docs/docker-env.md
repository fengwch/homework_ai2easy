# Docker 环境说明（可选）

本仓库的 AI-Agent 服务可以在宿主机运行，通过 **Docker** 提供的 MySQL / Redis / Milvus 等依赖服务连接（若你后续启用缓存/任务/向量检索模块）。  
Docker 依赖服务由 `docker-compose.yml` 启动。

## 1. 准备 .env

```bash
cp .env.example .env
```

建议调试时加入：

```env
LOG_LEVEL=DEBUG
```

## 2. 启动 Docker 依赖

在项目根目录执行：

```bash
docker compose up -d
docker compose ps
```

## 3. 启动 AI-Agent（对外端口 8001）

```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

健康检查：

```bash
curl http://localhost:8001/health
```

