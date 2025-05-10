import requests
import urllib.parse
import logging
import time
from fastapi import HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GraphAPIClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def post_request(self, url: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        """Graph APIへのPOSTリクエストを共通化"""
        try:
            response = requests.post(url, headers=self.headers, json=body, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Graph APIリクエストエラー: {e}")
            raise HTTPException(status_code=500, detail=f"Graph APIリクエストエラー: {e}")

    def get_schedules(self, target_user_email: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """スケジュールを取得するためのGraph API呼び出し"""
        url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(target_user_email)}/calendar/getSchedule"
        return self.post_request(url, body)

    def register_event(self, user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """予定を登録するためのGraph API呼び出し"""
        encoded_email = urllib.parse.quote(user_email)
        graph_url = f"https://graph.microsoft.com/beta/users/{encoded_email}/calendar/events"
        return self.post_request(graph_url, event)

    def send_email(self, sender_email: str, to_email: str, subject: str, body: str) -> None:
        """メールを送信するためのGraph API呼び出し"""
        endpoint = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body,
                },
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            }
        }
        self.post_request(endpoint, email_data)

    def retry_operation(self, func, *args, max_retries: int = 3):
        """リトライ処理"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                return func(*args)
            except Exception as e:
                retry_count += 1
                logger.warning(f"リトライ中 ({retry_count}/{max_retries}): {e}")
                time.sleep(2**retry_count)
        logger.error("リトライ回数を超過しました")
        raise HTTPException(status_code=500, detail="リトライ失敗")
