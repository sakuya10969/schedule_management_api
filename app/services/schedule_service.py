import logging
from typing import Dict, List, Tuple, Any

from app.utils.formatter import format_candidate_date
from app.schemas import ScheduleRequest, AppointmentRequest
from app.infrastructure.graph_api import GraphAPIClient

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self):
        self.graph_client = GraphAPIClient()

    def get_schedules(self, schedule_req: ScheduleRequest) -> Dict[str, Any]:
        """スケジュールを取得する"""
        target_user_email = schedule_req.users[0].email
        body = self._create_schedule_request_body(schedule_req)
        return self.graph_client.get_schedules(target_user_email, body)

    def _create_schedule_request_body(self, schedule_req: ScheduleRequest) -> Dict[str, Any]:
        """スケジュール取得用のリクエストボディを作成"""
        return {
            "schedules": [user.email for user in schedule_req.users],
            "startTime": {
                "dateTime": f"{schedule_req.start_date}T{schedule_req.start_time}:00",
                "timeZone": schedule_req.time_zone,
            },
            "endTime": {
                "dateTime": f"{schedule_req.end_date}T{schedule_req.end_time}:00",
                "timeZone": schedule_req.time_zone,
            },
            "availabilityViewInterval": 30,
        }

    def parse_availability(self, schedule_data: Dict[str, Any], start_hour: float, end_hour: float) -> List[List[Tuple[float, float]]]:
        """空き時間をパースする"""
        schedules_info = schedule_data.get("value", [])
        return [
            self._get_free_slots(schedule, start_hour, end_hour)
            for schedule in schedules_info
        ]

    def _get_free_slots(self, schedule: Dict[str, Any], start_hour: float, end_hour: float) -> List[Tuple[float, float]]:
        """個別のスケジュールから空き時間を抽出"""
        slot_duration = 0.5
        availability_view = schedule.get("availabilityView", "")
        
        return [
            (start_hour + i * slot_duration, start_hour + (i + 1) * slot_duration)
            for i, status in enumerate(availability_view)
            if status == "0" and start_hour + (i + 1) * slot_duration <= end_hour
        ]

    def create_event_payload(self, appointment_req: AppointmentRequest, start_str: str, end_str: str) -> Dict[str, Any]:
        """イベントペイロードを生成"""
        return {
            "subject": self._create_event_subject(appointment_req),
            "body": {
                "contentType": "HTML",
                "content": self._create_event_body(appointment_req),
            },
            "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
            "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
            "allowNewTimeProposals": True,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }

    def _create_event_subject(self, appointment_req: AppointmentRequest) -> str:
        """イベントの件名を生成"""
        return f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"

    def _create_event_body(self, appointment_req: AppointmentRequest) -> str:
        """イベントの本文を生成"""
        return (
            f"氏名: {appointment_req.lastname} {appointment_req.firstname}<br>"
            f"所属: {appointment_req.company}<br>"
            f"メール: {appointment_req.email}<br>"
            f"日程: {format_candidate_date(appointment_req.candidate)}"
        )

    def register_event(self, user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """イベントを登録"""
        return self.graph_client.retry_operation(self.graph_client.register_event, user_email, event)

    def send_email(self, sender_email: str, to_email: str, subject: str, body: str) -> None:
        """メールを送信"""
        self.graph_client.send_email(sender_email, to_email, subject, body)
