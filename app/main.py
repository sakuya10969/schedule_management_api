from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from app.routers import form_router, schedule_router
from app.config.config import get_config

# ログ設定を直接ここでやる
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

config = get_config()

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログミドルウェアの追加
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # リクエスト情報のログ
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")

    start_time = time.time()
    try:
        # レスポンスをキャプチャするためのカスタムResponseクラス
        response = await call_next(request)
        # レスポンスボディをキャプチャ
        response_body = [chunk async for chunk in response.body_iterator]
        # レスポンスボディを非同期ジェネレータとして再構築
        async def response_body_generator():
            for chunk in response_body:
                yield chunk
        # レスポンスボディをデコードしてログに表示
        response_text = b"".join(response_body).decode("utf-8")
        process_time = time.time() - start_time
        # ログ出力
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response_text}")
        # レスポンスのボディを非同期ジェネレータに差し替え
        response.body_iterator = response_body_generator()
        return response

    except Exception as e:
        # エラーログ
        logger.error(f"Error: {str(e)}")
        raise

# ルーターの登録
app.include_router(form_router.router)
app.include_router(schedule_router.router)
