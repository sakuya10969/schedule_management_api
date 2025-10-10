import requests
import urllib.parse
from fastapi import HTTPException
from typing import Any
from datetime import datetime, timedelta

from app.utils.access_token import get_access_token
from app.schemas.form import ScheduleRequest
from app.interfaces.graph_api_interface import GraphAPIClientInterface

class GraphAPIClient(GraphAPIClientInterface):
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

    def _handle_request(
        self, method: str, url: str, **kwargs
    ) -> dict[str, Any] | None:
        """APIリクエストの共通処理"""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)

            if response.status_code == 401:
                self.refresh_token()
                response = requests.request(method, url, headers=self.headers, **kwargs)

            response.raise_for_status()

            return response.json() if response.content else None

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Graph APIリクエストエラー: {str(e)}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=502, detail=f"Graph APIのレスポンスが不正: {str(e)}"
            )

    def post_request(
        self, url: str, body: dict[str, Any], timeout: int = 60
    ) -> dict[str, Any] | None:
        """Graph APIへのPOSTリクエスト"""
        return self._handle_request("POST", url, json=body, timeout=timeout)

    def get_schedules(self, schedule_req: ScheduleRequest) -> list[dict[str, Any]]:
        """スケジュールを取得"""
        try:
            schedules_list = []
            start_date = datetime.strptime(schedule_req.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(schedule_req.end_date, "%Y-%m-%d")

            delta = timedelta(days=1)
            while start_date <= end_date:
                for employee_email in schedule_req.employee_emails:
                    url = f"{self.BASE_URL}/{urllib.parse.quote(employee_email.email)}/calendar/getSchedule"
                    body = {
                        "schedules": [employee_email.email],
                        "startTime": {
                            "dateTime": f"{start_date.date()}T{schedule_req.start_time}:00",
                            "timeZone": schedule_req.time_zone,
                        },
                        "endTime": {
                            "dateTime": f"{start_date.date()}T{schedule_req.end_time}:00",
                            "timeZone": schedule_req.time_zone,
                        },
                        "availabilityViewInterval": schedule_req.duration_minutes,
                    }
                    schedules_list.append(self.post_request(url, body))
                start_date += delta

            return schedules_list
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"スケジュール取得エラー: {str(e)}"
            )

    def register_event(
        self, employee_email: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """予定を登録"""
        try:
            url = (
                f"{self.BASE_URL}/{urllib.parse.quote(employee_email)}/calendar/events"
            )
            return self.post_request(url, event)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"予定登録エラー: {str(e)}")

    def send_email(
        self, sender_email: str, target_employee_email: str, subject: str, body: str
    ) -> None:
        """メールを送信"""
        try:
            endpoint = f"{self.BASE_URL}/{sender_email}/sendMail"
            modified_body = (
                "<div style=\"font-family: 'Segoe UI', Calibri, Arial, sans-serif; "
                'font-size: 14px; line-height: 1.6; color: #333; margin: 0; padding: 0;">'
                f"{body}"
                "</div>"
            )
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": modified_body,
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": target_employee_email}}
                    ],
                }
            }
            self.post_request(endpoint, email_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"メール送信エラー: {str(e)}")

    def update_event_time(
        self, employee_email: str, event_id: str, start_datetime: str, end_datetime: str
    ) -> None:
        """予定の開始時刻と終了時刻を更新"""
        try:
            url = f"{self.BASE_URL}/{urllib.parse.quote(employee_email)}/events/{event_id}"
            update_data = {
                "start": {
                    "dateTime": start_datetime,
                    "timeZone": "Tokyo Standard Time"
                },
                "end": {
                    "dateTime": end_datetime,
                    "timeZone": "Tokyo Standard Time"
                }
            }
            self._handle_request("PATCH", url, json=update_data)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Graph APIイベント時刻更新エラー: {e}"
            )

    def delete_event(self, employee_email: str, event_id: str) -> None:
        """予定を削除するためのGraph API呼び出し"""
        try:
            url = f"{self.BASE_URL}/{urllib.parse.quote(employee_email)}/events/{event_id}"
            self._handle_request("DELETE", url)
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500, detail=f"Graph APIイベント削除エラー: {e}"
            )
