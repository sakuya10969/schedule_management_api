from fastapi import FastAPI, Request
import logging

from app.routers import form_router, schedule_router
from app.config.config import get_config
from app.middlewares.logging_middleware import log_requests
from app.middlewares.cors_middleware import add_cors

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

config = get_config()

app = FastAPI()
# CORS設定
add_cors(app)


# ログミドルウェアの追加
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    return await log_requests(request, call_next)


# ルーターの登録
app.include_router(form_router.router)
app.include_router(schedule_router.router)
