import requests
import urllib.parse
import time
from fastapi import HTTPException
from typing import Dict, Any, Callable

from app.utils.access_token import get_access_token

class GraphAPIClient:
    def __init__(self):
        self.refresh_token()

    def refresh_token(self):
        """アクセストークンを取得またはリフレッシュ"""
        try:
            self.access_token = get_access_token()
            if not self.access_token:
                raise HTTPException(status_code=401, detail="アクセストークンが空です")
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"トークン更新失敗: {e}")

    def post_request(self, url: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        """Graph APIへのPOSTリクエストを共通化"""
        try:
            response = requests.post(url, headers=self.headers, json=body, timeout=timeout)
            if response.status_code == 401:
                self.refresh_token()
                response = requests.post(url, headers=self.headers, json=body, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Graph APIリクエストエラー: {e}")

    def retry_operation(self, func: Callable, *args, max_retries: int = 3) -> Any:
        """指定した操作をリトライする共通メソッド"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                return func(*args)
            except HTTPException:
                retry_count += 1
                time.sleep(2**retry_count)
        raise HTTPException(status_code=500, detail="リトライ失敗")

    def get_schedules(self, target_user_email: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """スケジュールを取得するためのGraph API呼び出し"""
        encoded_email = urllib.parse.quote(target_user_email)
        url = f"https://graph.microsoft.com/v1.0/users/{encoded_email}/calendar/getSchedule"
        return self.retry_operation(self.post_request, url, body)

    def register_event(self, user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """予定を登録するためのGraph API呼び出し"""
        encoded_email = urllib.parse.quote(user_email)
        graph_url = f"https://graph.microsoft.com/v1.0/users/{encoded_email}/calendar/events"
        return self.retry_operation(self.post_request, graph_url, event)

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
                "toRecipients": [{"emailAddress": {"address": to_email}}]
            }
        }
        self.retry_operation(self.post_request, endpoint, email_data)
