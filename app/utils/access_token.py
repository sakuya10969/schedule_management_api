import logging
import time
from msal import ConfidentialClientApplication

from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

# Microsoft Graph API用のアクセストークン取得
def get_access_token() -> str:
    """
    Microsoft Graph API にアクセスするための認証トークンを取得
    """
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            scope = [
                "https://graph.microsoft.com/.default"
            ]  # Graph API 全般の既定スコープ

            app = ConfidentialClientApplication(
                client_id=config['CLIENT_ID'],
                client_credential=config['CLIENT_SECRET'],
                authority=f"https://login.microsoftonline.com/{config['TENANT_ID']}",
            )

            result = app.acquire_token_silent(scope, account=None)
            if not result:
                result = app.acquire_token_for_client(scopes=scope)

            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(
                    f"トークン取得に失敗しました: {result.get('error_description')}"
                )
                raise Exception(f"トークン取得失敗: {result.get('error_description')}")
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"最大リトライ回数に達しました: {e}")
                raise
            time.sleep(2**retry_count) 