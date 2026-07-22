import os
from dotenv import load_dotenv


load_dotenv()


name = "BrandCC on FastAPI framework on Gunicorn web server"

wsgi_app = "brandcc_server.main:app"

# Log configuration - use - for stdout/stderr in development
log_dir = os.environ.get("LOG_DIR", None)
if log_dir:
    accesslog = f"{log_dir}/gunicorn-access.log"
    errorlog = f"{log_dir}/gunicorn-error.log"
else:
    # Log to stdout/stderr for development
    accesslog = "-"
    errorlog = "-"

host = os.environ.get("HOST", "127.0.0.1")
port = os.environ.get("PORT", "8001")
bind = f"{host}:{port}"

worker_class = "uvicorn.workers.UvicornWorker"
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
# Single worker for now. If brandcc-server grows in-process state that can't be
# shared across OS-level worker processes (e.g. a job scheduler), keep this at 1 —
# uvicorn's asyncio event loop handles HTTP concurrency within the one process.
workers = 1
worker_connections = 1024
backlog = 2048
max_requests = 5120
timeout = 120
keepalive = 2

debug = os.environ.get("debug", "false") == "true"
reload = debug
preload_app = False
daemon = False
