from fastapi import Request
import time
import logging
import json

logger = logging.getLogger(__name__)

async def log_requests(request: Request, call_next):
    # リクエスト情報の取得
    request_id = request.headers.get("X-Request-ID", "N/A")
    start_time = time.time()

    # リクエストログ
    logger.info(
        f"Request | ID: {request_id} | {request.method} {request.url.path} | "
        f"Client: {request.client.host if request.client else 'N/A'}"
    )

    try:
        # リクエストボディのログ (POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and "application/json" in request.headers.get("Content-Type", ""):
                    logger.debug(f"Request Body: {json.dumps(json.loads(body), indent=2)}")
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")

        # レスポンス処理
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)

        # レスポンスボディの取得とログ
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        async def new_body_iterator():
            yield response_body

        response.body_iterator = new_body_iterator()

        # レスポンスログ
        log_msg = (
            f"Response | ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time}ms"
        )

        if response.status_code >= 500:
            logger.error(log_msg)
        elif response.status_code >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # レスポンスボディのログ (JSONの場合)
        if response_body and "application/json" in response.headers.get("Content-Type", ""):
            try:
                body_text = json.dumps(json.loads(response_body), indent=2)
                logger.debug(f"Response Body: {body_text}")
            except Exception:
                pass

        return response

    except Exception as e:
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"Error | ID: {request_id} | Duration: {process_time}ms | {str(e)}",
            exc_info=True
        )
        raise
