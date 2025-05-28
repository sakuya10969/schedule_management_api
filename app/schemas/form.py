from pydantic import BaseModel, Field
from typing import List

class EmployeeEmail(BaseModel):
    """ユーザー情報を表すスキーマ"""
    email: str = Field(..., description="ユーザーのメールアドレス")

    class Config:
        frozen = True
        json_schema_extra = {"example": {"email": "crawler01@intelligentforce.co.jp"}}

class ScheduleRequest(BaseModel):
    """スケジュールリクエストを表すスキーマ"""

    start_date: str = Field(..., description="開始日 (YYYY-MM-DD形式)")
    end_date: str = Field(..., description="終了日 (YYYY-MM-DD形式)")
    start_time: str = Field(..., description="開始時間 (HH:MM形式)")
    end_time: str = Field(..., description="終了時間 (HH:MM形式)")
    selected_days: List[str] = Field(..., description="選択された曜日のリスト")
    duration_minutes: int = Field(..., description="打合せ時間（分）")
    employee_emails: List[EmployeeEmail] = Field(..., description="面接担当者のリスト")
    required_participants: int = Field(..., description="共通する候補日を検索する人数")
    time_zone: str = Field(default="Tokyo Standard Time", description="タイムゾーン")

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2025-01-10",
                "end_date": "2025-01-15",
                "start_time": "09:00",
                "end_time": "18:00",
                "selected_days": ["月", "火", "水", "木", "金"],
                "duration_minutes": 60,
                "employee_emails": [
                    {"email": "crawler01@intelligentforce.co.jp"},
                    {"email": "y.ohama@intelligentforce.co.jp"},
                ],
                "time_zone": "Tokyo Standard Time",
            }
        }

class FormData(BaseModel):
    """フォームデータを表すスキーマ"""

    start_date: str
    end_date: str
    start_time: str
    end_time: str
    selected_days: List[str]
    duration_minutes: int
    employee_emails: List[EmployeeEmail]
    required_participants: int
    time_zone: str = "Tokyo Standard Time"
    is_confirmed: bool = False
    schedule_interview_datetimes: List[List[str]] | None = None
    event_ids: dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2025-01-10",
                "end_date": "2025-01-15",
                "start_time": "09:00",
                "end_time": "18:00",
                "selected_days": ["月", "火", "水", "木", "金"],
                "duration_minutes": 60,
                "employee_emails": [
                    {"email": "crawler01@intelligentforce.co.jp"},
                    {"email": "y.ohama@intelligentforce.co.jp"},
                ],
                "time_zone": "Tokyo Standard Time",
                "is_confirmed": False,
                "schedule_interview_datetimes": [
                    ["2025-01-10T10:00:00", "2025-01-10T11:00:00"],
                    ["2025-01-10T14:00:00", "2025-01-10T15:00:00"],
                ],
                "event_ids": None,
            }
        }
