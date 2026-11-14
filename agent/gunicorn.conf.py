"""
Gunicorn 配置：用于生产环境以 Gunicorn 启动 FastAPI（ASGI）。
可通过环境变量覆盖：GUNICORN_BIND、GUNICORN_WORKERS、GUNICORN_WORKER_CLASS 等。

启动示例：
  gunicorn -c gunicorn.conf.py api.main:app
  或指定绑定：GUNICORN_BIND=0.0.0.0:8001 gunicorn -c gunicorn.conf.py api.main:app
"""
import os

# macOS fork safety: prevent EXC_CRASH (SIGABRT) when Gunicorn forks workers
# after the parent has loaded libraries with Objective-C bindings (uvloop, numpy, etc.)
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

# 应用入口由命令行指定：gunicorn -c gunicorn.conf.py api.main:app

# 必须使用 Uvicorn 的 worker 才能跑 FastAPI（ASGI）
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")

# 绑定地址与端口
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8011")

# 进程数（建议 CPU 核数 * 2 + 1，或按需调小）
workers = int(os.getenv("GUNICORN_WORKERS", "2"))

# 单 worker 内线程（ASGI 通常用 1 即可）
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# 超时（秒），调大以适配 OCR/LLM 等长耗时请求
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# 日志：输出到控制台，便于被 systemd/supervisor 或 Docker 收集
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# 进程名
proc_name = os.getenv("GUNICORN_PROC_NAME", "ai-agent")

# 预加载应用：在主进程加载所有代码后再 fork worker，避免 macOS fork 安全问题
# 同时减少内存占用（Copy-on-Write 共享只读代码段）
preload_app = True
