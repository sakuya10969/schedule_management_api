import logging
from typing import Dict, List, Tuple, Any

from app.config import SYSTEM_SENDER_EMAIL
from app.utils.formatter import format_candidate_date
from app.schemas.form import ScheduleRequest, AppointmentRequest
from app.infrastructure.graph_api import GraphAPIClient

logger = logging.getLogger(__name__)

def get_schedules(schedule_req: ScheduleRequest) -> Dict[str, Any]:
    """スケジュールを取得するビジネスロジック"""
    graph_api_client = GraphAPIClient()

    target_user_email = schedule_req.users[0].email
    body = {
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

    return graph_api_client.get_schedules(target_user_email, body)

def parse_availability(schedule_data: Dict[str, Any], start_hour: float, end_hour: float) -> List[List[Tuple[float, float]]]:
    """空き時間をパースするビジネスロジック"""
    schedules_info = schedule_data.get("value", [])
    slot_duration = 0.5
    free_slots_list = []

    for schedule in schedules_info:
        availability_view = schedule.get("availabilityView", "")
        free_slots = [
            (start_hour + i * slot_duration, start_hour + (i + 1) * slot_duration)
            for i, c in enumerate(availability_view) if c == "0" and start_hour + (i + 1) * slot_duration <= end_hour
        ]
        free_slots_list.append(free_slots)
    return free_slots_list

def create_event_payload(appointment_req: AppointmentRequest, start_str: str, end_str: str) -> Dict[str, Any]:
    """イベントペイロードを生成する"""
    return {
        "subject": f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定",
        "body": {
            "contentType": "HTML",
            "content": (
                f"氏名: {appointment_req.lastname} {appointment_req.firstname}<br>"
                f"所属: {appointment_req.company}<br>"
                f"メール: {appointment_req.email}<br>"
                f"日程: {format_candidate_date(appointment_req.candidate)}"
            ),
        },
        "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
        "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
        "allowNewTimeProposals": True,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
    }

def register_event(user_email: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """イベントを登録するビジネスロジック"""
    graph_api_client = GraphAPIClient()
    return graph_api_client.retry_operation(graph_api_client.register_event, user_email, event)

def send_email(sender_email: str, to_email: str, subject: str, body: str) -> None:
    """メールを送信するビジネスロジック"""
    graph_api_client = GraphAPIClient()
    graph_api_client.send_email(sender_email, to_email, subject, body)
