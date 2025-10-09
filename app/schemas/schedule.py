from pydantic import BaseModel, Field


class AppointmentRequest(BaseModel):
    """面接予約リクエストを表すスキーマ"""

    schedule_interview_datetime: str | None = Field(
        None,
        description="選択された候補日時(None または '開始日時,終了日時' の形式）",
    )
    employee_email: str = Field(..., description="面接担当者のメールアドレス")
    candidate_lastname: str = Field(..., description="候補者の姓")
    candidate_firstname: str = Field(..., description="候補者の名")
    company: str = Field(..., description="候補者の所属会社")
    candidate_email: str = Field(..., description="候補者のメールアドレス")
    cosmos_db_id: str | None = Field(None, description="CosmosDBのID")
    candidate_id: int | None = Field(None, description="候補者のID")
    interview_stage: str | None = Field(None, description="面接のステージ")
    university: str | None = Field(..., description="大学名")

    class Config:
        json_schema_extra = {
            "example": {
                "schedule_interview_datetime": "2025-01-10T10:00:00,2025-01-10T11:00:00",
                "employee_email": "crawler01@intelligentforce.co.jp",
                "candidate_lastname": "青木",
                "candidate_firstname": "駿介",
                "company": "株式会社サンプル",
                "candidate_email": "shunsuke.aoki0913@gmail.com",
                "cosmos_db_id": "sample-az-cosmos-id-123",
                "candidate_id": "1234567890",
                "interview_stage": "1",
                "university": "インテリ大学",
            }
        }


class AppointmentResponse(BaseModel):
    """面接予約レスポンスを表すスキーマ"""

    message: str = Field(..., description="処理結果のメッセージ")
    subjects: list[str] = Field(..., description="作成された予定の件名リスト")
    meeting_urls: list[str | None] = Field(..., description="オンライン会議のURLリスト")
    employee_email: str = Field(..., description="面接担当者のメールアドレス")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "予定を登録しました。確認メールは別途送信されます。",
                "subjects": ["面接: 青木 駿介 (株式会社サンプル)"],
                "meeting_urls": ["https://teams.microsoft.com/l/meetup-join/..."],
                "employee_email": "crawler01@intelligentforce.co.jp",
            }
        }


class AvailabilityResponse(BaseModel):
    """空き時間候補のレスポンスを表すスキーマ"""

    common_availability: list[list[str]] = Field(
        ...,
        description="共通の空き時間候補のリスト（開始日時と終了日時のリストのリスト）",
    )
    slot_members_map: dict[str, list[str]] = Field(
        ...,
        description="各スロットの参加者リストの辞書",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "common_availability": [
                    ["2025-01-10T10:00:00", "2025-01-10T11:00:00"],
                    ["2025-01-10T14:00:00", "2025-01-10T15:00:00"],
                ],
                "slot_members_map": {
                    "2025-01-10T10:00:00/2025-01-10T11:00:00": ["crawler01@intelligentforce.co.jp", "y.ohama@intelligentforce.co.jp"],
                    "2025-01-10T14:00:00/2025-01-10T15:00:00": ["crawler01@intelligentforce.co.jp", "y.ohama@intelligentforce.co.jp"],
                },
            }
        }
