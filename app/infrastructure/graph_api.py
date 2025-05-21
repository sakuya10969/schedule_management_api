import requests
import urllib.parse
from fastapi import HTTPException
from typing import Dict, Any, List, Optional

from app.utils.access_token import get_access_token
from app.schemas.form import ScheduleRequest

class GraphAPIClient:
    BASE_URL = "https://graph.microsoft.com/v1.0/users"

    def __init__(self):
        self.refresh_token()

    def refresh_token(self) -> None:
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
            raise HTTPException(status_code=500, detail=f"トークン更新失敗: {str(e)}")

    def _handle_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """APIリクエストの共通処理"""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            
            if response.status_code == 401:
                self.refresh_token()
                response = requests.request(method, url, headers=self.headers, **kwargs)
            
            response.raise_for_status()
            
            return response.json() if response.content else None

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Graph APIリクエストエラー: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=502, detail=f"Graph APIのレスポンスが不正: {str(e)}")

    def post_request(self, url: str, body: Dict[str, Any], timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Graph APIへのPOSTリクエスト"""
        return self._handle_request("POST", url, json=body, timeout=timeout)

    def get_schedules(self, schedule_req: ScheduleRequest) -> List[Dict[str, Any]]:
        """スケジュールを取得"""
        try:
            schedules_list = []
            for user in schedule_req.users:
                url = f"{self.BASE_URL}/{urllib.parse.quote(user.email)}/calendar/getSchedule"
                body = {
                    "schedules": [user.email],
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
                schedules_list.append(self.post_request(url, body))
            return schedules_list
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"スケジュール取得エラー: {str(e)}")

    def register_event(self, user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """予定を登録"""
        try:
            url = f"{self.BASE_URL}/{urllib.parse.quote(user_email)}/calendar/events"
            return self.post_request(url, event)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"予定登録エラー: {str(e)}")

    def send_email(self, sender_email: str, to_email: str, subject: str, body: str) -> None:
        """メールを送信"""
        try:
            endpoint = f"{self.BASE_URL}/{sender_email}/sendMail"
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
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"メール送信エラー: {str(e)}")

    def delete_event(self, user_email: str, event_id: str) -> None:
        """予定を削除するためのGraph API呼び出し"""
        try:
            url = f"{self.BASE_URL}/{urllib.parse.quote(user_email)}/events/{event_id}"
            self._handle_request("DELETE", url)
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Graph APIイベント削除エラー: {e}")
