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
        return self.graph_client.get_schedules(target_user_email, body)

    def parse_availability(self, schedule_data: Dict[str, Any], start_hour: float, end_hour: float) -> List[List[Tuple[float, float]]]:
        """空き時間をパースする"""
        schedules_info = schedule_data.get("value", [])
        slot_duration = 0.5
        
        result = []
        for schedule in schedules_info:
            availability_view = schedule.get("availabilityView", "")
            free_slots = [
                (start_hour + i * slot_duration, start_hour + (i + 1) * slot_duration)
                for i, status in enumerate(availability_view)
                if status == "0" and start_hour + (i + 1) * slot_duration <= end_hour
            ]
            result.append(free_slots)
        
        return result

    def handle_appointment(self, appointment_req: AppointmentRequest) -> Dict[str, Any]:
        """予約を処理し、イベントを作成してメールを送信する"""
        if not appointment_req.candidate:
            return {}
            
        start_str, end_str = appointment_req.candidate.split(",")
        
        # イベントペイロードを作成
        subject = f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"
        body = (
            f"氏名: {appointment_req.lastname} {appointment_req.firstname}<br>"
            f"所属: {appointment_req.company}<br>"
            f"メール: {appointment_req.email}<br>"
            f"日程: {format_candidate_date(appointment_req.candidate)}"
        )
        
        event = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body,
            },
            "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
            "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
            "allowNewTimeProposals": True,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }
        
        # イベントを登録
        result = {}
        for user_email in appointment_req.users:
            result[user_email] = self.graph_client.retry_operation(
                self.graph_client.register_event, 
                user_email, 
                event
            )
            
            # メール送信
            self.graph_client.send_email(user_email, appointment_req.email, subject, body)
            
        return result
