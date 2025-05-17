import requests
import urllib.parse
from fastapi import HTTPException
from typing import Dict, Any

from app.utils.access_token import get_access_token
from app.schemas.form import ScheduleRequest

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
        """Graph APIへのPOSTリクエスト"""
        try:
            response = requests.post(url, headers=self.headers, json=body, timeout=timeout)
            if response.status_code == 401:
                # トークンが無効な場合はリフレッシュして再試行
                self.refresh_token()
                response = requests.post(url, headers=self.headers, json=body, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Graph APIリクエストエラー: {e}")

    def get_schedules(self, schedule_req: ScheduleRequest) -> Dict[str, Any]:
        """スケジュールを取得するためのGraph API呼び出し"""
        target_user_email = urllib.parse.quote(schedule_req.users[0].email)
        url = f"https://graph.microsoft.com/v1.0/users/{target_user_email}/calendar/getSchedule"
        
        # リクエストボディの構築
        request_body = {
            "schedules": [user.email for user in schedule_req.users],
            "startTime": {
                "dateTime": f"{schedule_req.start_date}T{schedule_req.start_time}:00",
                "timeZone": schedule_req.time_zone
            },
            "endTime": {
                "dateTime": f"{schedule_req.end_date}T{schedule_req.end_time}:00",
                "timeZone": schedule_req.time_zone
            },
            "availabilityViewInterval": schedule_req.duration_minutes
        }

        response = self.post_request(url, request_body)
        
        if not response or 'value' not in response:
            error_msg = f"無効なレスポンス形式: {response}"
            raise ValueError(error_msg)

        return response

    def register_event(self, user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """予定を登録するためのGraph API呼び出し"""
        encoded_email = urllib.parse.quote(user_email)
        graph_url = f"https://graph.microsoft.com/v1.0/users/{encoded_email}/calendar/events"
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
                "toRecipients": [{"emailAddress": {"address": to_email}}]
            }
        }
        self.post_request(endpoint, email_data)
