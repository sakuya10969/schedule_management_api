from fastapi import Request
import time
import logging
import json

logger = logging.getLogger(__name__)

async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "N/A")
    start_time = time.time()

    # リクエストログ
    logger.info(
        f"Request | ID: {request_id} | {request.method} {request.url.path} | "
        f"Client: {request.client.host if request.client else 'N/A'}"
    )

    try:
        # POST/PUT/PATCHのJSONボディをログ
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body and "application/json" in request.headers.get("Content-Type", ""):
                logger.debug(f"Request Body: {json.dumps(json.loads(body), indent=2)}")

        # レスポンス処理
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)

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

        return response

    except Exception as e:
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"Error | ID: {request_id} | Duration: {process_time}ms | {str(e)}",
            exc_info=True
        )
        raise
